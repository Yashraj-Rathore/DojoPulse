"""Authenticated, generation-pinned range playback without public URLs."""

import re
import time

from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
from django.utils import timezone

from backend.core.cloud import CloudFailure
from backend.core.models import ReplayAsset, UploadSession
from backend.core.storage import private_path, storage_for


def byte_range(header, size):
    if not header:
        return 0, size - 1, False
    match = re.fullmatch(r"bytes=([0-9]{0,12})-([0-9]{0,12})", header)
    if not match or not any(match.groups()) or size <= 0:
        raise ValueError("INVALID_MEDIA_RANGE")
    first, last = match.groups()
    if not first:
        if int(last) <= 0:
            raise ValueError("INVALID_MEDIA_RANGE")
        start, end = max(0, size - int(last)), size - 1
    else:
        start, end = int(first), min(int(last), size - 1) if last else size - 1
    if not 0 <= start <= end < size:
        raise ValueError("INVALID_MEDIA_RANGE")
    return start, end, True


class PrefetchedBody:
    def __init__(self, first, chunks):
        self.first, self.chunks = first, chunks

    def __iter__(self):
        return self

    def __next__(self):
        if self.first is not None:
            block, self.first = self.first, None
            return block
        return next(self.chunks)

    def close(self):
        self.chunks.close()


def asset_response(asset, range_header, *, authorize=None):
    if asset.retain_until and asset.retain_until <= timezone.now():
        return HttpResponse(status=404)
    if UploadSession.objects.filter(asset=asset).exclude(state="COMPLETE").exists():
        return HttpResponse(status=404)
    if (
        asset.metadata.get("unattributed_recording")
        or asset.metadata.get("capture_tool") == "dojopulse-companion/1"
    ):
        from backend.core.models import AnalysisRun

        run = (
            AnalysisRun.objects.filter(asset=asset, owner_id=asset.owner_id)
            .order_by("-created_at")
            .first()
        )
        if (
            not run
            or run.status not in {"REVIEW_REQUIRED", "PARTIAL", "COMPLETED"}
            or run.result.get("source", {}).get("source_sha256") != asset.source_sha256
        ):
            return HttpResponse(status=404)
    size = asset.bytes
    if asset.storage_provider == "LOCAL":
        path = private_path(asset.storage_key)
        if not path.is_file():
            return HttpResponse(status=404)
        size = path.stat().st_size
    elif not settings.GCS_STORAGE_QUALIFIED:
        raise CloudFailure("GCS_STORAGE_UNQUALIFIED", retryable=False)
    try:
        start, end, partial = byte_range(range_header, size)
    except ValueError:
        response = HttpResponse(status=416)
        response["Content-Range"] = f"bytes */{size}"
        response["Accept-Ranges"] = "bytes"
        response["Cache-Control"] = "private, no-store"
        return response
    last_check, deadline = 0.0, time.monotonic() + 180

    def check():
        nonlocal last_check
        if settings.RESTORE_QUARANTINE or time.monotonic() >= deadline:
            raise ValueError("MEDIA_READ_REVOKED")
        if time.monotonic() - last_check < 0.5:
            return
        last_check = time.monotonic()
        if authorize is not None and not authorize():
            raise ValueError("MEDIA_GRANT_REVOKED")
        if not ReplayAsset.objects.filter(
            pk=asset.pk, owner_id=asset.owner_id, owner__is_active=True, deleted_at=None
        ).exists():
            raise ValueError("MEDIA_READ_REVOKED")
        if asset.retain_until and asset.retain_until <= timezone.now():
            raise ValueError("MEDIA_READ_EXPIRED")

    def local_chunks():
        with path.open("rb") as source:
            source.seek(start)
            remaining = end - start + 1
            while remaining:
                check()
                block = source.read(min(65536, remaining))
                if not block:
                    raise ValueError("MEDIA_SIZE_CHANGED")
                remaining -= len(block)
                yield block

    chunks = (
        local_chunks()
        if asset.storage_provider == "LOCAL"
        else storage_for(asset).range_stream(
            asset.storage_key, asset.storage_generation, start, end, size, check
        )
    )
    try:
        first = next(chunks, b"")  # Validate upstream status/headers before sending HTTP headers.
    except Exception:
        chunks.close()
        raise
    response = StreamingHttpResponse(
        PrefetchedBody(first, chunks), status=206 if partial else 200, content_type="video/mp4"
    )
    response["Content-Length"] = str(end - start + 1)
    if partial:
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
    response["Accept-Ranges"] = "bytes"
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
