"""Independent, bounded signed preview intents. Session capabilities never enter SQL.

This file backend is a controlled prototype, not a qualified replicated cloud store.
An unavailable, torn, missing or untrusted journal fails closed. Its entire historical
rollback requires an external freshness anchor; production activation is gated.
"""

import base64
import copy
import hashlib
import hmac
import json
import os
import re
import stat
import time
from contextlib import contextmanager
from itertools import islice
from pathlib import Path
from uuid import UUID, uuid5

from django.conf import settings

from analysis.preview_bundle import FILES

MAX_EVENTS = 4096
MAX_RECORD = 16384
ZERO = "0" * 64


class LedgerFailure(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LedgerFailure("PREVIEW_LEDGER_INVALID")
        result[key] = value
    return result


def validate_intent(row):
    try:
        if set(row) != {
            "id",
            "owner",
            "asset",
            "preview",
            "run",
            "fence",
            "bucket",
            "source_sha256",
            "state",
            "files",
        }:
            raise ValueError
        for key in ("id", "asset", "preview", "run"):
            if str(UUID(row[key])) != row[key]:
                raise ValueError
        if type(row["owner"]) is not int or not 0 < row["owner"] < 2**63:
            raise ValueError
        if type(row["fence"]) is not int or not 0 < row["fence"] < 2**31:
            raise ValueError
        if row["id"] != str(uuid5(UUID(row["preview"]), f"{row['run']}:{row['fence']}")):
            raise ValueError
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,220}[a-z0-9]", row["bucket"]):
            raise ValueError
        if not re.fullmatch(r"[a-f0-9]{64}", row["source_sha256"]):
            raise ValueError
        if row["state"] not in {"OPEN", "PUBLISHED", "CLEANUP", "ERASED"}:
            raise ValueError
        if set(row["files"]) != set(FILES):
            raise ValueError
        for name, item in row["files"].items():
            if set(item) != {"bytes", "sha256", "md5", "state", "session", "generation"}:
                raise ValueError
            if type(item["bytes"]) is not int or not 0 < item["bytes"] <= FILES[name]:
                raise ValueError
            if not re.fullmatch(r"[a-f0-9]{64}", item["sha256"]):
                raise ValueError
            if len(base64.b64decode(item["md5"], validate=True)) != 16:
                raise ValueError
            if item["state"] not in {"PLANNED", "INITIALIZING", "SESSION", "FINALIZED", "STOPPED"}:
                raise ValueError
            if item["session"]:
                from backend.core.cloud import GooglePrivateStorage

                GooglePrivateStorage(
                    None, row["bucket"], row["owner"], row["asset"]
                ).preview_session_url(item["session"], prefix(row) + name)
            if item["generation"] and not re.fullmatch(r"[1-9][0-9]{0,29}", item["generation"]):
                raise ValueError
            if item["state"] in {"SESSION", "FINALIZED"} and not item["session"]:
                raise ValueError
            if item["state"] in {"PLANNED", "INITIALIZING"} and (
                item["session"] or item["generation"]
            ):
                raise ValueError
            if item["state"] == "SESSION" and item["generation"]:
                raise ValueError
            if item["state"] == "FINALIZED" and not item["generation"]:
                raise ValueError
        if row["state"] == "PUBLISHED" and any(
            item["state"] != "FINALIZED" for item in row["files"].values()
        ):
            raise ValueError
        if row["state"] == "ERASED" and any(
            item["state"] != "STOPPED" for item in row["files"].values()
        ):
            raise ValueError
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise LedgerFailure("PREVIEW_LEDGER_INVALID") from error


def prefix(row):
    return f"{row['owner']}/{row['asset']}/previews/{row['preview']}/{row['run']}/{row['fence']}/"


def held_bytes(row):
    return 0 if row["state"] == "ERASED" else sum(item["bytes"] for item in row["files"].values())


def transition(old, new):
    if old is None:
        if new["state"] != "OPEN" or any(x["state"] != "PLANNED" for x in new["files"].values()):
            raise LedgerFailure("PREVIEW_LEDGER_TRANSITION")
        return
    for key in set(old) - {"state", "files"}:
        if old[key] != new[key]:
            raise LedgerFailure("PREVIEW_LEDGER_TRANSITION")
    states = {
        "OPEN": {"OPEN", "PUBLISHED", "CLEANUP"},
        "PUBLISHED": {"PUBLISHED", "CLEANUP"},
        "CLEANUP": {"CLEANUP", "ERASED"},
        "ERASED": {"ERASED"},
    }
    file_states = {
        "PLANNED": {"PLANNED", "INITIALIZING", "STOPPED"},
        "INITIALIZING": {"INITIALIZING", "SESSION"},
        "SESSION": {"SESSION", "FINALIZED", "STOPPED"},
        "FINALIZED": {"FINALIZED", "STOPPED"},
        "STOPPED": {"STOPPED"},
    }
    if new["state"] not in states[old["state"]]:
        raise LedgerFailure("PREVIEW_LEDGER_TRANSITION")
    for name, before in old["files"].items():
        after = new["files"][name]
        if any(before[k] != after[k] for k in ("bytes", "sha256", "md5")):
            raise LedgerFailure("PREVIEW_LEDGER_TRANSITION")
        if after["state"] not in file_states[before["state"]]:
            raise LedgerFailure("PREVIEW_LEDGER_TRANSITION")
        if (
            old["state"] in {"CLEANUP", "ERASED"}
            and after["state"] == "INITIALIZING"
            and before["state"] != "INITIALIZING"
        ):
            raise LedgerFailure("PREVIEW_LEDGER_TRANSITION")
        if before["session"] and before["session"] != after["session"]:
            raise LedgerFailure("PREVIEW_LEDGER_TRANSITION")
        if before["generation"] and before["generation"] != after["generation"]:
            raise LedgerFailure("PREVIEW_LEDGER_TRANSITION")
        if after["state"] == "STOPPED" and new["state"] not in {"CLEANUP", "ERASED"}:
            raise LedgerFailure("PREVIEW_LEDGER_TRANSITION")


class FileLedger:
    def __init__(self):
        self.root = Path(settings.PREVIEW_LEDGER_ROOT).absolute()
        self.key = settings.PREVIEW_LEDGER_KEY.encode()
        if not self.key:
            raise LedgerFailure("PREVIEW_LEDGER_KEY_REQUIRED")

    def initialize(self):
        if not settings.DEBUG:
            raise LedgerFailure("PREVIEW_LEDGER_UNQUALIFIED")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.lock():
            if (self.root / "checkpoint.json").exists():
                self._read()
                return
            if set(x.name for x in self.root.iterdir()) != {"lock"}:
                raise LedgerFailure("PREVIEW_LEDGER_NOT_EMPTY")
            self._write("checkpoint.json", self.sign({"count": 0, "hash": ZERO}))

    @contextmanager
    def lock(self):
        # Reject symlink/reparse components, including an ancestor redirect.
        if self.root.resolve() != self.root or not self.root.is_dir():
            raise LedgerFailure("PREVIEW_LEDGER_UNAVAILABLE")
        if any(
            p.is_symlink() or bool(p.stat().st_file_attributes & 1024)
            if hasattr(p.stat(), "st_file_attributes")
            else p.is_symlink()
            for p in (self.root, *self.root.parents)
        ):
            raise LedgerFailure("PREVIEW_LEDGER_UNAVAILABLE")
        target = self.root / "lock"
        if target.exists() and (target.is_symlink() or not target.is_file()):
            raise LedgerFailure("PREVIEW_LEDGER_UNAVAILABLE")
        fd = os.open(target, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        stream = os.fdopen(fd, "r+b", buffering=0)
        locked = False
        try:
            if not os.fstat(fd).st_size:
                stream.write(b"0")
            deadline = time.monotonic() + 5
            while not locked:
                try:
                    stream.seek(0)
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                except OSError:
                    if time.monotonic() >= deadline:
                        raise LedgerFailure("PREVIEW_LEDGER_BUSY") from None
                    time.sleep(0.02)
            yield
        finally:
            if locked:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fd, fcntl.LOCK_UN)
            stream.close()

    def sign(self, body):
        body = {**body, "version": 1, "namespace": settings.DEPLOYMENT_NAMESPACE}
        return {
            **body,
            "signature": hmac.new(self.key, canonical(body), hashlib.sha256).hexdigest(),
        }

    def _load(self, name):
        path = self.root / name
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_RECORD:
                raise LedgerFailure("PREVIEW_LEDGER_INVALID")
            with path.open("rb") as stream:
                raw = stream.read(MAX_RECORD + 1)
            if len(raw) > MAX_RECORD:
                raise LedgerFailure("PREVIEW_LEDGER_INVALID")
            data = json.loads(raw, object_pairs_hook=unique_pairs)
            signature = data.pop("signature")
            if (
                data["version"] != 1
                or data["namespace"] != settings.DEPLOYMENT_NAMESPACE
                or not hmac.compare_digest(signature, self.sign(data)["signature"])
            ):
                raise LedgerFailure("PREVIEW_LEDGER_INVALID")
            return data, hashlib.sha256(raw).hexdigest()
        except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
            raise LedgerFailure("PREVIEW_LEDGER_INVALID") from error

    def _write(self, name, data):
        raw = canonical(data)
        if len(raw) > MAX_RECORD:
            raise LedgerFailure("PREVIEW_LEDGER_LIMIT")
        tmp = self.root / (name + ".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, self.root / name)
        if os.name != "nt":
            fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        return hashlib.sha256(raw).hexdigest()

    def _read(self):
        checkpoint, _ = self._load("checkpoint.json")
        count = checkpoint.get("count")
        if (
            set(checkpoint) != {"count", "hash", "version", "namespace"}
            or type(count) is not int
            or not 0 <= count <= MAX_EVENTS
        ):
            raise LedgerFailure("PREVIEW_LEDGER_INVALID")
        names = {"lock", "checkpoint.json"} | {f"{i:08d}.json" for i in range(1, count + 1)}
        if set(p.name for p in islice(self.root.iterdir(), MAX_EVENTS + 4)) != names:
            raise LedgerFailure("PREVIEW_LEDGER_INCOMPLETE")
        rows, previous = {}, ZERO
        for sequence in range(1, count + 1):
            event, digest = self._load(f"{sequence:08d}.json")
            if (
                set(event) != {"sequence", "previous", "intent", "version", "namespace"}
                or event["sequence"] != sequence
                or event["previous"] != previous
            ):
                raise LedgerFailure("PREVIEW_LEDGER_INVALID")
            row = event["intent"]
            validate_intent(row)
            transition(rows.get(row["id"], (None, 0))[0], row)
            rows[row["id"]] = (row, sequence)
            previous = digest
        if previous != checkpoint["hash"]:
            raise LedgerFailure("PREVIEW_LEDGER_INCOMPLETE")
        return rows, count, previous

    def records(self):
        with self.lock():
            return self._read()[0]

    def update(self, intent_id, mutate):
        if not settings.DEBUG and not settings.PREVIEW_LEDGER_RUNTIME_QUALIFIED:
            raise LedgerFailure("PREVIEW_LEDGER_UNQUALIFIED")
        with self.lock():
            rows, count, previous = self._read()
            old = rows.get(intent_id, (None, 0))[0]
            new = mutate(copy.deepcopy(old))
            validate_intent(new)
            if new["id"] != intent_id:
                raise LedgerFailure("PREVIEW_LEDGER_TRANSITION")
            transition(old, new)
            if old == new:
                return new
            if count == MAX_EVENTS:
                raise LedgerFailure("PREVIEW_LEDGER_LIMIT")
            digest = self._write(
                f"{count + 1:08d}.json",
                self.sign(
                    {
                        "sequence": count + 1,
                        "previous": previous,
                        "intent": new,
                    }
                ),
            )
            self._write("checkpoint.json", self.sign({"count": count + 1, "hash": digest}))
            return new
