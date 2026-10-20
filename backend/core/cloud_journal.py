"""Shared append-only sequence arbitration on official GCS; no mutable checkpoint.

Each sequence is won by create-if-absent. The deployment principal MUST NOT have
overwrite/delete permissions. Independent protected buckets survive SQL/media
restores. All real access remains gated until IAM/durability is qualified.
"""

import copy
import hashlib
import hmac
import json
import re
import threading
from collections import OrderedDict
from urllib.parse import quote

from django.conf import settings

from backend.core.cloud import CloudFailure, authorized_session, resource
from backend.core.preview_ledger import (
    MAX_EVENTS,
    MAX_RECORD,
    ZERO,
    LedgerFailure,
    canonical,
    transition,
    unique_pairs,
    validate_intent,
)


class Collision(Exception):
    pass


# Immutable generation-pinned bytes only. Fresh inventory is always read; a cache
# cannot hide a new sequence, changed generation, missing object or bad signature.
_cache = OrderedDict()
_cache_lock = threading.Lock()
_cache_bytes = 0
_cache_limit = 8388608


def decode(raw):
    try:
        value = json.loads(raw, object_pairs_hook=unique_pairs)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, TypeError, RecursionError):
        raise LedgerFailure("CLOUD_JOURNAL_INVALID") from None


def namespace_id():
    value = settings.DEPLOYMENT_NAMESPACE
    if not isinstance(value, str) or not 1 <= len(value) <= 192 or any(ord(c) < 32 for c in value):
        raise LedgerFailure("CLOUD_JOURNAL_NAMESPACE")
    return hashlib.sha256(value.encode()).hexdigest()[:48]


class GoogleObjects:
    def __init__(self, bucket, session=None):
        if not settings.PREVIEW_LEDGER_RUNTIME_QUALIFIED:
            raise LedgerFailure("CLOUD_JOURNAL_UNQUALIFIED")
        self.bucket = resource(bucket, r"[a-z0-9][a-z0-9.-]{2,61}[a-z0-9]")
        self.session = session if session is not None else authorized_session()
        self.url = f"https://storage.googleapis.com/storage/v1/b/{self.bucket}/o"

    def request(self, method, url, *, maximum=MAX_RECORD, accepted=(200,), **kwargs):
        try:
            response = self.session.request(
                method, url, timeout=(5, 20), allow_redirects=False, stream=True, **kwargs
            )
        except Exception:
            raise CloudFailure("JOURNAL_TRANSPORT_FAILURE", ambiguous=method == "POST") from None
        try:
            if response.status_code not in accepted:
                raise CloudFailure(
                    "JOURNAL_REQUEST_REJECTED",
                    retryable=response.status_code in {429, 500, 502, 503, 504},
                )
            data = bytearray()
            for block in response.iter_content(chunk_size=16384):
                data.extend(block)
                if len(data) > maximum:
                    raise LedgerFailure("CLOUD_JOURNAL_RESPONSE_LIMIT")
            return response.status_code, bytes(data), dict(response.headers)
        finally:
            response.close()

    def get(self, name, generation=None):
        global _cache_bytes
        cache_key = (self.bucket, name, generation)
        if generation:
            with _cache_lock:
                if cache_key in _cache:
                    _cache.move_to_end(cache_key)
                    return _cache[cache_key]
        params = {"alt": "media"}
        if generation:
            params.update(generation=generation, ifGenerationMatch=generation)
        status, raw, _ = self.request(
            "GET", self.url + "/" + quote(name, safe=""), params=params, accepted=(200, 404)
        )
        if status == 404:
            return None
        if generation:
            with _cache_lock:
                _cache_bytes -= len(_cache.pop(cache_key, b""))
                _cache[cache_key] = raw
                _cache_bytes += len(raw)
                while _cache_bytes > _cache_limit:
                    _, discarded = _cache.popitem(last=False)
                    _cache_bytes -= len(discarded)
        return raw

    def create(self, name, raw):
        try:
            status, body, _ = self.request(
                "POST",
                f"https://storage.googleapis.com/upload/storage/v1/b/{self.bucket}/o",
                params={"uploadType": "media", "name": name, "ifGenerationMatch": "0"},
                headers={"Content-Type": "application/json", "Content-Length": str(len(raw))},
                data=raw,
                accepted=(200, 201, 412),
                maximum=65536,
            )
        except CloudFailure:
            # A read receipt of identical immutable bytes resolves response loss.
            if self.get(name) == raw:
                return
            raise
        if status == 412:
            if self.get(name) == raw:
                return
            raise Collision
        info = decode(body)
        generation = resource(str(info.get("generation", "")), r"[1-9][0-9]{0,29}")
        if (
            info.get("name") != name
            or info.get("bucket") != self.bucket
            or str(info.get("size")) != str(len(raw))
            or self.get(name, generation) != raw
        ):
            raise LedgerFailure("CLOUD_JOURNAL_WRITE_UNCONFIRMED")

    def inventory(self, prefix):
        found, token, seen = {}, None, set()
        for _ in range(34):
            params = {"prefix": prefix, "maxResults": 128}
            if token:
                params["pageToken"] = token
            _, raw, _ = self.request("GET", self.url, params=params, maximum=262144)
            body = decode(raw)
            for item in body.get("items", []):
                name, generation = item.get("name", ""), str(item.get("generation", ""))
                if (
                    not name.startswith(prefix)
                    or name in found
                    or not re.fullmatch(r"[1-9][0-9]{0,29}", generation)
                ):
                    raise LedgerFailure("CLOUD_JOURNAL_INVENTORY_INVALID")
                found[name] = generation
                if len(found) > MAX_EVENTS + 1:
                    raise LedgerFailure("CLOUD_JOURNAL_LIMIT")
            token = body.get("nextPageToken")
            if not token:
                return found
            if not isinstance(token, str) or len(token) > 4096 or token in seen:
                raise LedgerFailure("CLOUD_JOURNAL_INVENTORY_INVALID")
            seen.add(token)
        raise LedgerFailure("CLOUD_JOURNAL_LIMIT")


class CloudLog:
    def __init__(self, kind, store=None):
        if kind not in {"preview", "control", "execution"}:
            raise LedgerFailure("CLOUD_JOURNAL_KIND")
        namespace = namespace_id()
        self.kind, self.prefix = kind, f"{kind}/{namespace}/"
        self.key = (
            settings.CONTROL_JOURNAL_KEY if kind == "control" else settings.PREVIEW_LEDGER_KEY
        ).encode()
        if not self.key:
            raise LedgerFailure("CLOUD_JOURNAL_KEY_REQUIRED")
        bucket = {
            "preview": settings.GOOGLE_PREVIEW_LEDGER_BUCKET,
            "control": settings.GOOGLE_CONTROL_JOURNAL_BUCKET,
            "execution": settings.GOOGLE_EXECUTION_JOURNAL_BUCKET,
        }[kind]
        self.store = store if store is not None else GoogleObjects(bucket)

    def seal(self, body):
        body = {**body, "version": 1, "namespace": settings.DEPLOYMENT_NAMESPACE, "kind": self.kind}
        return canonical(
            {**body, "signature": hmac.new(self.key, canonical(body), hashlib.sha256).hexdigest()}
        )

    def open(self, raw):
        if raw is None or len(raw) > MAX_RECORD:
            raise LedgerFailure("CLOUD_JOURNAL_MISSING_OR_LIMIT")
        body = decode(raw)
        signature = body.pop("signature", "")
        if (
            body.get("version") != 1
            or body.get("namespace") != settings.DEPLOYMENT_NAMESPACE
            or body.get("kind") != self.kind
            or not isinstance(signature, str)
            or not hmac.compare_digest(
                signature, hmac.new(self.key, canonical(body), hashlib.sha256).hexdigest()
            )
        ):
            raise LedgerFailure("CLOUD_JOURNAL_SIGNATURE")
        return body

    def initialize(self):
        # Explicit operator bootstrap only, never called by admission/recovery.
        if self.store.inventory(self.prefix):
            self.records()
            return
        self.store.create(
            self.prefix + "00000000.json",
            self.seal({"sequence": 0, "previous": ZERO, "payload": None}),
        )

    def records(self):
        inventory = self.store.inventory(self.prefix)
        if not inventory or len(inventory) > MAX_EVENTS + 1:
            raise LedgerFailure("CLOUD_JOURNAL_UNINITIALIZED_OR_LIMIT")
        expected = {self.prefix + f"{i:08d}.json" for i in range(len(inventory))}
        if set(inventory) != expected:
            raise LedgerFailure("CLOUD_JOURNAL_SEQUENCE_GAP")
        records, previous = [], ZERO
        for sequence in range(len(inventory)):
            name = self.prefix + f"{sequence:08d}.json"
            raw = self.store.get(name, inventory[name])
            body = self.open(raw)
            if (
                set(body) != {"version", "namespace", "kind", "sequence", "previous", "payload"}
                or body["sequence"] != sequence
                or body["previous"] != previous
                or (sequence == 0 and body["payload"] is not None)
            ):
                raise LedgerFailure("CLOUD_JOURNAL_CHAIN")
            previous = hashlib.sha256(raw).hexdigest()
            if sequence:
                records.append(body["payload"])
        return records, previous

    def update(self, mutate):
        for _ in range(6):
            records, previous = self.records()
            payload = mutate(records)
            if payload is None:
                return
            if len(records) == MAX_EVENTS:
                raise LedgerFailure("CLOUD_JOURNAL_LIMIT")
            sequence = len(records) + 1
            raw = self.seal({"sequence": sequence, "previous": previous, "payload": payload})
            if len(raw) > MAX_RECORD:
                raise LedgerFailure("CLOUD_JOURNAL_LIMIT")
            try:
                self.store.create(self.prefix + f"{sequence:08d}.json", raw)
                return
            except Collision:
                continue  # Read the winning immutable sequence and reapply the state transition.
        raise LedgerFailure("CLOUD_JOURNAL_CONTENTION")


class GooglePreviewLedger:
    def __init__(self, log=None):
        self.log = log if log is not None else CloudLog("preview")

    @staticmethod
    def reduce(records):
        rows = {}
        for sequence, row in enumerate(records, 1):
            validate_intent(row)
            transition(rows.get(row["id"], (None, 0))[0], row)
            rows[row["id"]] = (row, sequence)
        return rows

    def records(self):
        return self.reduce(self.log.records()[0])

    def update(self, identity, mutate):
        result = []

        def apply(records):
            old = self.reduce(records).get(identity, (None, 0))[0]
            row = mutate(copy.deepcopy(old))
            validate_intent(row)
            if row["id"] != identity:
                raise LedgerFailure("CLOUD_JOURNAL_IDENTITY")
            transition(old, row)
            result[:] = [row]
            return None if old == row else row

        self.log.update(apply)
        return result[0]
