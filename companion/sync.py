"""Selected-folder admission and bounded durable transfer, independent of the GUI."""

import base64
import hashlib
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from analysis.media import probe

MAX_BYTES = 536870912
TERMINAL = {"COMPLETE", "REMOVED", "DUPLICATE", "CANCELLED", "REJECTED"}


class TransferError(Exception):
    def __init__(self, code: str, *, retry_after: float = 0, fatal: bool = False):
        super().__init__(code)
        self.retry_after, self.fatal = retry_after, fatal


def server_origin(value: str, local_development: bool = False) -> str:
    url = urlsplit(value)
    if url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
        raise ValueError("CONFIGURED_SERVICE_ORIGIN_REQUIRED")
    local = (
        local_development
        and url.scheme == "http"
        and url.hostname == "127.0.0.1"
        and url.port == 8000
    )
    if not local and (url.scheme != "https" or not url.hostname):
        raise ValueError("HTTPS_SERVICE_REQUIRED")
    if not url.netloc or any(c.isspace() for c in value):
        raise ValueError("CONFIGURED_SERVICE_ORIGIN_REQUIRED")
    return value.rstrip("/")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: Any, msg: Any, headers: Any, newurl: Any
    ) -> None:
        return None


def retry_delay(value: str) -> float:
    try:
        return max(0, float(int(value)))
    except ValueError:
        try:
            return max(0, (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return 60


class Transport:
    def __init__(self, origin: str, credential: str = "", *, local_development: bool = False):
        self.origin = server_origin(origin, local_development)
        self.credential = credential
        # No environmental proxy, cookies, redirect or arbitrary upload destination.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(
        self, method: str, path: str, body: Any = None, offset: int | None = None
    ) -> dict[str, Any]:
        if not re.fullmatch(
            r"/api/companion/(pair|uploads(?:/[a-f0-9-]{36}(?:/(chunk|complete))?)?)", path
        ):
            raise ValueError("INVALID_COMPANION_OPERATION")
        headers = {"Accept": "application/json"}
        data: bytes | None
        if self.credential:
            headers["Authorization"] = "RecordingDevice " + self.credential
        if isinstance(body, bytes):
            data = body
            headers["Content-Type"] = "application/octet-stream"
            headers["Upload-Offset"] = str(offset)
        else:
            data = json.dumps(body).encode() if body is not None else None
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.origin + path, data=data, headers=headers, method=method
        )
        try:
            with self.opener.open(request, timeout=20) as response:
                raw = response.read(1_000_001)
                if len(raw) > 1_000_000:
                    raise TransferError("RESPONSE_LIMIT", fatal=True)
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise TransferError("INVALID_RESPONSE", fatal=True)
                return result
        except urllib.error.HTTPError as error:
            if error.code in {429, 500, 502, 503, 504}:
                raise TransferError(
                    "SERVICE_RETRY", retry_after=retry_delay(error.headers.get("Retry-After", "0"))
                ) from None
            raise TransferError(
                "DEVICE_ACCESS_STOPPED" if error.code in {401, 403} else "UPLOAD_REJECTED",
                fatal=error.code in {401, 403, 301, 302, 307, 308},
            ) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            raise TransferError("NETWORK_RETRY") from None
        except (ValueError, UnicodeError):
            raise TransferError("INVALID_RESPONSE", fatal=True) from None


def linked(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def selected_file(root: Path, path: Path) -> Path:
    root, path = root.absolute(), path.absolute()
    for ancestor in [root, *root.parents]:
        if linked(ancestor):
            raise ValueError("LINKED_FOLDER_REJECTED")
    if path.parent != root or linked(path) or path.resolve().parent != root.resolve():
        raise ValueError("SELECTED_FOLDER_REQUIRED")
    if (
        path.suffix.lower() != ".mp4"
        or not path.is_file()
        or not 0 < path.stat().st_size <= MAX_BYTES
    ):
        raise ValueError("SUPPORTED_MP4_REQUIRED")
    return path


def signature(info: os.stat_result) -> tuple[int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


@contextmanager
def locked_recording(path: Path) -> Any:
    if sys.platform == "win32":
        import ctypes
        import msvcrt
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        kernel.CreateFileW.restype = wintypes.HANDLE
        # Share READ only: recording writers/rename/deletion must finish before admission.
        handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x00200000, None)
        if handle == wintypes.HANDLE(-1).value:
            raise ValueError("RECORDING_BUSY")
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    else:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        if linked(path) or not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("LINKED_RECORDING_REJECTED")
        yield stream


def finalized(stream: Any, size: int) -> None:
    offset, seen, boxes = 0, set(), 0
    while offset < size:
        stream.seek(offset)
        header = stream.read(8)
        if len(header) != 8:
            raise ValueError("UNFINISHED_CONTAINER")
        length, kind = int.from_bytes(header[:4], "big"), header[4:]
        minimum = 8
        if length == 1:
            extra = stream.read(8)
            if len(extra) != 8:
                raise ValueError("UNFINISHED_CONTAINER")
            length, minimum = int.from_bytes(extra, "big"), 16
        # Reject indefinite, fragmented and externally referenced containers.
        if length < minimum or offset + length > size or kind in {b"moof", b"sidx"}:
            raise ValueError("UNFINISHED_CONTAINER")
        seen.add(kind)
        offset += length
        boxes += 1
        if boxes > 10000:
            raise ValueError("CONTAINER_LIMIT")
    if not {b"ftyp", b"moov", b"mdat"}.issubset(seen):
        raise ValueError("UNFINISHED_CONTAINER")


class SyncEngine:
    def __init__(self, store: Any, transport: Any, *, check_media: Any = probe):
        self.store, self.transport, self.check_media = store, transport, check_media
        self.state = store.load()
        self.state.setdefault("receipts", {})
        self.enabled = False  # Explicit start after launch/restart; transfer receipts survive.
        self.observed: dict[str, tuple[tuple[int, int, int, int], float]] = {}
        self.cancel_requested = False

    def select_folder(self, root: Path, *, include_existing: bool = False) -> None:
        if self.enabled:
            raise ValueError("PAUSE_BEFORE_FOLDER_CHANGE")
        root = root.absolute()
        if not root.is_dir() or any(linked(a) for a in [root, *root.parents]):
            raise ValueError("SELECTED_FOLDER_REQUIRED")
        if (
            self.state.get("folder")
            and self.state["folder"] != str(root)
            and any(row["state"] not in TERMINAL for row in self.state["receipts"].values())
        ):
            raise ValueError("FINISH_OR_CANCEL_PENDING_RECORDINGS")
        names = [p.name for p in root.iterdir() if p.suffix.lower() == ".mp4"][:501]
        if len(names) > 500:
            raise ValueError("FOLDER_FILE_LIMIT")
        self.state["folder"] = str(root)
        self.state["excluded"] = [] if include_existing else names
        self.observed.clear()
        self.store.save(self.state)

    def tick(self, now: float | None = None) -> str:
        if not self.enabled:
            return "Paused"
        now = time.time() if now is None else now
        stale = [
            key
            for key, row in self.state["receipts"].items()
            if row["state"] in TERMINAL and now - row["created_at"] > 90 * 86400
        ]
        if stale:
            for key in stale:
                del self.state["receipts"][key]
            self.store.save(self.state)
        root = Path(self.state["folder"])
        # Resume accepted receipts first; never manufacture another retry key after rejection.
        for sha, receipt in self.state["receipts"].items():
            if receipt["state"] not in TERMINAL and (
                self.cancel_requested or receipt.get("retry_at", 0) <= now
            ):
                return self.transfer(root, sha, receipt, now)
        if self.cancel_requested:
            self.cancel_requested = self.enabled = False
            return "No pending transfer; paused"
        names = 0
        for path in root.iterdir():
            names += 1
            if names > 500:
                return "Folder file limit reached; move unrelated files elsewhere"
            if path.name in self.state.get("excluded", []) or path.suffix.lower() != ".mp4":
                continue
            try:
                selected_file(root, path)
                current = signature(path.stat())
                prior = self.observed.get(path.name)
                self.observed[path.name] = (
                    current,
                    prior[1] if prior and prior[0] == current else now,
                )
                if not prior or prior[0] != current or now - prior[1] < 10:
                    continue
                with locked_recording(path) as stream:
                    selected_file(root, path)
                    initial = signature(os.fstat(stream.fileno()))
                    if initial != current:
                        raise ValueError("RECORDING_CHANGED")
                    finalized(stream, current[2])
                    sha, md5 = hashlib.sha256(), hashlib.md5(usedforsecurity=False)
                    stream.seek(0)
                    while block := stream.read(1024 * 1024):
                        if not self.enabled:
                            return "Paused"
                        sha.update(block)
                        md5.update(block)
                    key = sha.hexdigest()
                    if key in self.state["receipts"]:
                        continue
                    self.check_media(path)  # Bounded local finalized-container/profile check.
                    if not self.enabled:
                        return "Paused"
                    if (
                        signature(path.stat()) != initial
                        or signature(os.fstat(stream.fileno())) != initial
                    ):
                        raise ValueError("RECORDING_CHANGED")
                    if len(self.state["receipts"]) >= 256:
                        return "Local receipt limit reached; no new recordings admitted"
                    receipt = {
                        "name": path.name,
                        "bytes": current[2],
                        "signature": list(initial),
                        "md5": base64.b64encode(md5.digest()).decode(),
                        "state": "PENDING",
                        "offset": 0,
                        "attempts": 0,
                        "created_at": now,
                    }
                    self.state["receipts"][key] = receipt
                    self.store.save(self.state)
                return self.transfer(root, key, receipt, now)
            except (ValueError, OSError):
                continue  # Growing/unsupported/unreadable files remain local.
        return "Watching selected folder; completed supported MP4s only"

    def transfer(self, root: Path, sha: str, receipt: dict[str, Any], now: float) -> str:
        try:
            if not self.enabled and not self.cancel_requested:
                return "Paused"
            if self.cancel_requested and not receipt.get("id"):
                receipt["state"] = "CANCELLED"
                self.cancel_requested = self.enabled = False
                self.store.save(self.state)
                return "Transfer cancelled; local original retained"
            path = selected_file(root, root / receipt["name"])
            with locked_recording(path) as stream:
                selected_file(root, path)
                expected = tuple(receipt["signature"])
                if signature(os.fstat(stream.fileno())) != expected:
                    raise ValueError("RECORDING_CHANGED")
                if not receipt.get("id"):
                    info = self.transport.request(
                        "POST",
                        "/api/companion/uploads",
                        {"bytes": receipt["bytes"], "sha256": sha, "md5": receipt["md5"]},
                    )
                    if info.get("state") in {"REMOVED", "DUPLICATE"}:
                        receipt["state"] = info["state"]
                        self.store.save(self.state)
                        return "Recording already present or removed; skipped"
                    receipt["id"] = str(UUID(info["id"]))
                    self.store.save(self.state)
                if not self.enabled and not self.cancel_requested:
                    return "Paused"
                url = "/api/companion/uploads/" + receipt["id"]
                info = self.transport.request("GET", url)
                if self.cancel_requested:
                    if info["state"] not in {"COMPLETE", "CANCELLED", "PURGING"}:
                        self.transport.request("DELETE", url)
                    receipt["state"] = "CANCELLED" if info["state"] != "COMPLETE" else "COMPLETE"
                    self.cancel_requested = False
                    self.enabled = False
                    self.store.save(self.state)
                    return "Transfer cancelled; local original retained"
                if info["state"] in {"COMPLETE", "CANCELLED", "PURGING"}:
                    receipt["state"] = "REMOVED" if info["state"] == "PURGING" else info["state"]
                    self.store.save(self.state)
                    return "Transferred; check private recordings in DojoPulse"
                if info["state"] != "UPLOADING":
                    receipt["state"] = info["state"]
                    receipt["retry_at"] = now + 10
                    self.store.save(self.state)
                    return "Waiting for server verification"
                if info.get("storage_provider") != "LOCAL" or info.get("upload_url"):
                    raise TransferError("UNQUALIFIED_STORAGE", fatal=True)
                chunk = info["chunk_bytes"]
                offset = info["received_bytes"]
                if (
                    type(chunk) is not int
                    or not 1 <= chunk <= 8 * 1024**2
                    or type(offset) is not int
                    or not 0 <= offset <= receipt["bytes"]
                ):
                    raise TransferError("INVALID_TRANSFER", fatal=True)
                receipt["offset"] = offset
                while self.enabled and offset < receipt["bytes"] and not self.cancel_requested:
                    selected_file(root, path)
                    if (
                        signature(path.stat()) != expected
                        or signature(os.fstat(stream.fileno())) != expected
                    ):
                        raise ValueError("RECORDING_CHANGED")
                    stream.seek(offset)
                    block = stream.read(min(chunk, receipt["bytes"] - offset))
                    if not block:
                        raise ValueError("RECORDING_CHANGED")
                    response = self.transport.request("PUT", url + "/chunk", block, offset)
                    if response.get("received_bytes") != offset + len(block):
                        raise TransferError("INVALID_TRANSFER", fatal=True)
                    offset += len(block)
                    receipt["offset"] = offset
                    self.store.save(self.state)
                if offset == receipt["bytes"] and self.enabled and not self.cancel_requested:
                    if signature(path.stat()) != expected:
                        raise ValueError("RECORDING_CHANGED")
                    self.transport.request("POST", url + "/complete", {})
                    receipt["state"] = "VERIFYING"
                    receipt["retry_at"] = time.time() + 10
                receipt["attempts"] = 0
                self.store.save(self.state)
                return (
                    "Paused"
                    if not self.enabled
                    else "Syncing; gameplay attribution remains separate"
                )
        except TransferError as error:
            if error.fatal:
                self.enabled = False
            receipt["attempts"] += 1
            receipt["retry_at"] = now + max(
                error.retry_after, min(300, 2 ** min(receipt["attempts"], 9))
            )
            if receipt["attempts"] >= 8 or str(error) == "UPLOAD_REJECTED":
                receipt["state"] = "REJECTED"
            self.store.save(self.state)
            return str(error)  # Fixed codes only; no path, credential, player or response body.
        except (ValueError, OSError, KeyError, TypeError):
            # A changed/missing local file cannot resume an older byte reservation.
            receipt["state"] = "REJECTED"
            self.store.save(self.state)
            return "Recording changed or unavailable; pending server bytes expire automatically"
