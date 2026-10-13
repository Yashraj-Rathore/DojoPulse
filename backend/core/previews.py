"""Private derivative lifecycle on the existing job/consent/storage fences."""

import re
import shutil
import subprocess
from itertools import islice
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from analysis.media import file_hash
from analysis.preview_bundle import FILES, MAX_BYTES, PIPELINE, read_json, validate_bundle
from analysis.process import execution_check
from backend.core.cloud import CloudFailure
from backend.core.consents import require_processing
from backend.core.jobs import enqueue_run, finish_run, heartbeat, locked_run
from backend.core.models import (
    AnalysisRun,
    ExecutionSlot,
    RecordingPreview,
    ReplayAsset,
    UploadSession,
)
from backend.core.ownership import lock_owner
from backend.core.recordings import require_local_operator
from backend.core.security import admit_run, check_capacity
from backend.core.storage import private_path, storage_for


def available(asset, *, pending_upload=False):
    return (
        asset.owner.is_active
        and not asset.deleted_at
        and not settings.RESTORE_QUARANTINE
        and (not asset.retain_until or asset.retain_until > timezone.now())
        and (
            pending_upload
            or not UploadSession.objects.filter(asset=asset).exclude(state="COMPLETE").exists()
        )
    )


@transaction.atomic
def enqueue_preview(owner, asset_id, request_id):
    owner = lock_owner(owner.pk)
    require_local_operator(owner)
    require_processing(owner)
    asset = ReplayAsset.objects.select_related("owner").get(pk=asset_id, owner=owner)
    if not available(asset) or not asset.source_sha256:
        raise ValidationError("Verified recording bytes are required")
    if asset.storage_provider == "GCS" and not settings.GCS_PREVIEW_WRITES_QUALIFIED:
        raise CloudFailure("GCS_PREVIEW_UNQUALIFIED", retryable=False)
    key = f"preview:{request_id}"
    prior = AnalysisRun.objects.filter(owner=owner, request_key=key).first()
    preview = RecordingPreview.objects.filter(asset=asset).first()
    if prior and (prior.asset_id != asset.pk or not preview or preview.run_id != prior.pk):
        raise ValidationError("Preview request belongs to different or superseded evidence")
    if prior:
        return preview  # A completed receipt never resurrects its old job/state.
    if preview and preview.state in {"QUEUED", "READY"}:
        return preview
    if preview and preview.state == "PURGING":
        raise ValidationError("Preview cleanup must finish before retry")
    if not preview or preview.state == "PURGED":
        check_capacity(owner, MAX_BYTES)
    admit_run(owner)
    run = enqueue_run(owner=owner, asset=asset, request_key=key, pipeline_version=PIPELINE)
    if not preview:
        preview = RecordingPreview(asset=asset)
    preview.run, preview.state = run, "QUEUED"
    preview.source_sha256, preview.reserved_bytes = asset.source_sha256, MAX_BYTES
    preview.manifest, preview.quality, preview.error_code = {}, {}, ""
    preview.attempt_fence, preview.write_pending, preview.completed_at = 0, False, None
    preview.save()
    return preview


def attempt_prefix(preview, fence):
    return (
        str(Path(preview.asset.storage_key).parent).replace("\\", "/")
        + f"/previews/{preview.pk}/{preview.run_id}/{fence}/"
    )


@transaction.atomic
def start_preview(run_id, fence):
    run = locked_run(run_id)
    if run.pipeline_version != PIPELINE or not heartbeat(run_id, fence):
        raise ValueError("RUN_REVOKED")
    preview = RecordingPreview.objects.select_related("asset__owner").filter(run=run).first()
    if (
        not preview
        or preview.state != "QUEUED"
        or preview.asset_id != run.asset_id
        or preview.source_sha256 != run.asset.source_sha256
    ):
        raise ValueError("RUN_REVOKED")
    preview.attempt_fence = fence
    preview.save(update_fields=["attempt_fence"])
    name = f"dojopulse-preview-{run.pk.hex}-{fence}"
    ExecutionSlot.objects.filter(run=run, fence=fence).update(execution_name=name)
    return preview, name


def publish_files(preview, fence, directory):
    if not heartbeat(preview.run_id, fence, phase="PUBLISHING", progress=85):
        raise ValueError("RUN_REVOKED")
    manifest = {}
    prefix = attempt_prefix(preview, fence)
    for filename in FILES:
        check = execution_check.get()
        if check:
            check()
        key = prefix + filename
        source = directory / filename
        sha = file_hash(source)
        if preview.asset.storage_provider == "LOCAL":
            target = private_path(key)
            # Serialize each bounded local write with deletion/withdrawal, so an old
            # coordinator cannot recreate bytes after the deletion fence commits.
            with transaction.atomic():
                if not heartbeat(preview.run_id, fence):
                    raise ValueError("RUN_REVOKED")
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open("rb") as stream, target.open("xb") as output:
                    while block := stream.read(65536):
                        if check:
                            check()
                        output.write(block)
            generation = ""
        else:
            if not settings.GCS_PREVIEW_WRITES_QUALIFIED:
                raise CloudFailure("GCS_PREVIEW_UNQUALIFIED", retryable=False)
            # Persist ambiguity BEFORE the RPC; a crash/outage cannot refund uncertain bytes.
            with transaction.atomic():
                if not heartbeat(preview.run_id, fence):
                    raise ValueError("RUN_REVOKED")
                RecordingPreview.objects.filter(
                    pk=preview.pk, run_id=preview.run_id, attempt_fence=fence
                ).update(write_pending=True)
            generation = storage_for(preview.asset).create_preview_object(key, source)
            RecordingPreview.objects.filter(
                pk=preview.pk, run_id=preview.run_id, attempt_fence=fence
            ).update(write_pending=False)
        manifest[filename] = {
            "key": key,
            "sha256": sha,
            "bytes": source.stat().st_size,
            "generation": generation,
        }
    return manifest


@transaction.atomic
def complete_preview(run_id, fence, directory, identity):
    run = locked_run(run_id)
    preview = RecordingPreview.objects.select_related("asset__owner").filter(run=run).first()
    if (
        not preview
        or not heartbeat(run_id, fence)
        or preview.state != "QUEUED"
        or preview.attempt_fence != fence
    ):
        return False
    quality = validate_bundle(directory, run.asset.source_sha256)
    # Files were published outside this transaction; re-pin their actual bytes and lineage.
    manifest = preview.manifest
    if set(manifest) != set(FILES) or any(
        manifest[name]["sha256"] != file_hash(directory / name) for name in FILES
    ):
        raise ValueError("INVALID_PREVIEW_BUNDLE")
    report = {
        "status": "PREVIEW_READY",
        "schema_version": "private-preview/1",
        "source": {
            "source_sha256": run.asset.source_sha256,
            "duration_seconds": quality["duration_seconds"],
        },
        "opportunities": [],
        "automatic_gameplay_validated": False,
        "precise_gameplay_analysis_approved": False,
        "decoder_identity": identity,
        "quality": quality,
        "cost": {"derived_bytes": sum(item["bytes"] for item in manifest.values())},
    }
    if not finish_run(run_id, fence, report):
        return False
    preview.state, preview.quality = "READY", quality
    preview.reserved_bytes = sum(item["bytes"] for item in manifest.values())
    preview.completed_at = timezone.now()
    preview.save()
    return True


def process_preview(run, fence, source, scratch):
    from backend.core.preview_sandbox import normalize_isolated

    preview, name = start_preview(run.pk, fence)
    directory = scratch / "bundle"
    identity = normalize_isolated(source, directory, name)
    validate_bundle(directory, run.asset.source_sha256)
    if not heartbeat(run.pk, fence, phase="PUBLISHING", progress=85):
        raise ValueError("RUN_REVOKED")
    manifest = publish_files(preview, fence, directory)
    RecordingPreview.objects.filter(
        pk=preview.pk, run_id=run.pk, state="QUEUED", attempt_fence=fence
    ).update(manifest=manifest)
    if not complete_preview(run.pk, fence, directory, identity):
        raise ValueError("RUN_REVOKED")
    return AnalysisRun.objects.get(pk=run.pk).result


def revoke(previews):
    previews.exclude(state="PURGED").update(state="PURGING", quality={})


@transaction.atomic
def purge_preview(preview_id):
    preview = RecordingPreview.objects.select_related("asset__owner").get(pk=preview_id)
    lock_owner(preview.asset.owner_id)
    preview = (
        RecordingPreview.objects.select_for_update().select_related("asset").get(pk=preview_id)
    )
    if preview.state != "PURGING" or preview.write_pending:
        return False
    if (
        preview.run_id
        and ExecutionSlot.objects.filter(run_id=preview.run_id, released_at=None).exists()
    ):
        return False
    prefix = (
        str(Path(preview.asset.storage_key).parent).replace("\\", "/") + f"/previews/{preview.pk}/"
    )
    if preview.asset.storage_provider == "LOCAL":
        path = private_path(prefix)
        if path.exists():
            shutil.rmtree(path)
    else:
        storage_for(preview.asset).delete_preview(prefix)
        path = private_path(prefix)
        if path.exists():
            shutil.rmtree(path)  # Remove this asset's bounded local staging, too.
    with transaction.atomic():
        lock_owner(preview.asset.owner_id)
        current = RecordingPreview.objects.select_for_update().get(pk=preview.pk)
        if current.state != "PURGING" or current.write_pending:
            return False
        current.state, current.reserved_bytes, current.manifest, current.quality = (
            "PURGED",
            0,
            {},
            {},
        )
        current.source_sha256 = ""
        current.save()
    return True


def reconcile_previews():
    from backend.core.jobs import acknowledge_stopped
    from backend.core.preview_sandbox import remove_container

    for slot in ExecutionSlot.objects.filter(
        runtime="LOCAL", released_at=None, run__pipeline_version=PIPELINE
    ).select_related("run")[:100]:
        if not slot.stop_requested_at:
            continue
        expected = f"dojopulse-preview-{slot.run_id.hex}-{slot.fence}"
        if settings.PARSER_BACKEND != "docker":
            continue  # A host decoder cannot be stopped by another process's assertion.
        if slot.execution_name and slot.execution_name != expected:
            continue
        try:
            remove_container(expected)
            with transaction.atomic():
                run = locked_run(slot.run_id)
                current_slot = ExecutionSlot.objects.select_for_update().get(pk=slot.pk)
                if current_slot.released_at or not current_slot.stop_requested_at:
                    continue
                preview = (
                    RecordingPreview.objects.filter(run_id=slot.run_id)
                    .select_related("asset")
                    .first()
                )
                # Fence the coordinator before touching its files. Holding the owner
                # lock also excludes an in-progress local publisher or new admission.
                if run.fence == slot.fence and run.status == "PROCESSING":
                    run.lease_until = None
                    run.save(update_fields=["lease_until"])
                if preview and preview.write_pending:
                    run.status, run.error_code = "FAILED", "PREVIEW_WRITE_UNCONFIRMED"
                    run.fence += 1
                    run.save(update_fields=["status", "error_code", "fence"])
                    revoke(RecordingPreview.objects.filter(pk=preview.pk))
                elif preview:
                    prefix = attempt_prefix(preview, slot.fence)
                    if preview.asset.storage_provider == "LOCAL":
                        path = private_path(prefix)
                        if path.exists():
                            shutil.rmtree(path)
                    else:
                        storage_for(preview.asset).delete_preview(prefix)
                    RecordingPreview.objects.filter(
                        pk=preview.pk, run_id=slot.run_id, attempt_fence=slot.fence
                    ).update(manifest={})
                acknowledge_stopped(slot.run_id, slot.fence)
        except (OSError, ValueError, CloudFailure):
            continue
    for preview in RecordingPreview.objects.exclude(state="PURGED").select_related(
        "asset__owner", "run"
    )[:100]:
        pending = (
            preview.state == "WAITING_UPLOAD"
            and UploadSession.objects.filter(
                asset=preview.asset,
                state__in=["INITIALIZING", "UPLOADING", "VERIFYING"],
                expires_at__gt=timezone.now(),
            ).exists()
        )
        invalid = not available(preview.asset, pending_upload=pending)
        try:
            require_processing(preview.asset.owner)
        except Exception:
            invalid = True
        if invalid or (preview.run and preview.run.status in {"FAILED", "CANCELLED"}):
            revoke(RecordingPreview.objects.filter(pk=preview.pk))
        if RecordingPreview.objects.filter(pk=preview.pk, state="PURGING").exists():
            try:
                purge_preview(preview.pk)
            except (OSError, ValueError, CloudFailure):
                pass


def preview_view(asset):
    preview = RecordingPreview.objects.select_related("run").filter(asset=asset).first()
    if not preview:
        return {"state": "NOT_PREPARED", "media_url": None}
    permitted = available(asset)
    try:
        require_processing(asset.owner)
    except Exception:
        permitted = False
    ready = (
        permitted
        and preview.state == "READY"
        and preview.run
        and preview.run.status == "PREVIEW_READY"
        and preview.run.pipeline_version == PIPELINE
        and preview.run.owner_id == asset.owner_id
        and preview.run.asset_id == asset.pk
        and preview.source_sha256 == asset.source_sha256
    )
    if ready:
        prefix = attempt_prefix(preview, preview.attempt_fence)
        manifest = preview.manifest
        ready = set(manifest) == set(FILES) and all(
            isinstance(manifest[name], dict)
            and manifest[name].get("key") == prefix + name
            and type(manifest[name].get("bytes")) is int
            and 0 < manifest[name]["bytes"] <= maximum
            for name, maximum in FILES.items()
        )
    return {
        "state": preview.state if permitted else "UNAVAILABLE",
        "run_id": str(preview.run_id) if preview.run_id else None,
        "phase": preview.run.phase if permitted and preview.run else None,
        "progress": preview.run.progress if permitted and preview.run else 0,
        "media_url": f"/api/assets/{asset.pk}/preview/media" if ready else None,
        "quality": preview.quality if ready else {},
        "error_code": preview.error_code if permitted else "",
    }


def quality_windows(asset, offset=0):
    preview = RecordingPreview.objects.get(asset=asset, state="READY")
    item = preview.manifest["report.json"]
    if asset.storage_provider == "LOCAL":
        path = private_path(item["key"])
        if file_hash(path) != item["sha256"]:
            raise ValueError("PREVIEW_HASH_CHANGED")
        report = read_json(path, FILES["report.json"])
    else:
        if not settings.GCS_PREVIEW_WRITES_QUALIFIED:
            raise CloudFailure("GCS_PREVIEW_UNQUALIFIED", retryable=False)
        import tempfile

        with tempfile.TemporaryDirectory(prefix="preview-quality-") as directory:
            path = Path(directory) / "report.json"
            storage_for(asset).download(item["key"], item["generation"], path, item["bytes"])
            if file_hash(path) != item["sha256"]:
                raise ValueError("PREVIEW_HASH_CHANGED")
            report = read_json(path, FILES["report.json"])
    intervals = report["quality"]["unknown_intervals"]
    return {
        "intervals": intervals[offset : offset + 100],
        "offset": offset,
        "next_offset": offset + 100 if offset + 100 < len(intervals) else None,
        "total": len(intervals),
    }


def purge_restored_previews():
    """Sweep post-backup preview artifacts; require stop certainty before freeing bytes."""
    previews = RecordingPreview.objects.all()
    active = ExecutionSlot.objects.filter(run__pipeline_version=PIPELINE, released_at=None)
    if active.exists():
        if settings.PARSER_BACKEND != "docker":
            raise ValueError("RESTORE_PREVIEW_EXECUTION_UNCONFIRMED")
        from backend.core.jobs import acknowledge_stopped
        from backend.core.preview_sandbox import remove_container

        for slot in active:
            remove_container(f"dojopulse-preview-{slot.run_id.hex}-{slot.fence}")
            acknowledge_stopped(slot.run_id, slot.fence)
    if previews.filter(write_pending=True).exists():
        raise ValueError("RESTORE_PREVIEW_WRITE_UNCONFIRMED")
    if settings.PARSER_BACKEND == "docker" and settings.PARSER_IMAGE:
        listing = subprocess.run(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                "label=dojopulse.role=preview",
                "--format",
                "{{.Names}}",
            ],
            timeout=15,
            capture_output=True,
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        from backend.core.preview_sandbox import remove_container

        names = listing.stdout.decode().splitlines()
        if len(names) > 100 or any(
            not re.fullmatch(r"dojopulse-preview-[a-f0-9]{32}-[0-9]{1,10}", name) for name in names
        ):
            raise ValueError("RESTORE_PREVIEW_INVENTORY_INVALID")
        for name in names:
            remove_container(name)
    # Inventory only the server-owned LOCAL owner/asset namespace. A preview created
    # after the backup may have no restored asset row. Never erase its original.
    root = settings.PRIVATE_DATA_ROOT
    owner_dirs = list(islice(root.iterdir(), 1001)) if root.exists() else []
    if len(owner_dirs) > 1000:
        raise ValueError("RESTORE_PREVIEW_INVENTORY_LIMIT")
    discovered = []
    inspected_assets = 0
    for owner_dir in owner_dirs:
        if not re.fullmatch(r"[1-9][0-9]{0,19}", owner_dir.name):
            continue
        if owner_dir.is_symlink() or not owner_dir.is_dir():
            raise ValueError("RESTORE_PREVIEW_INVENTORY_INVALID")
        asset_dirs = list(islice(owner_dir.iterdir(), 1001))
        if len(asset_dirs) > 1000:
            raise ValueError("RESTORE_PREVIEW_INVENTORY_LIMIT")
        inspected_assets += len(asset_dirs)
        if inspected_assets > 10000:
            raise ValueError("RESTORE_PREVIEW_INVENTORY_LIMIT")
        for asset_dir in asset_dirs:
            if not re.fullmatch(r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}", asset_dir.name):
                continue
            prefix = f"{owner_dir.name}/{asset_dir.name}/previews/"
            path = private_path(prefix)  # Reject ancestor links; resolved private-root scope.
            if path.exists():
                discovered.append(path)
    for path in discovered:
        shutil.rmtree(path)
    for asset in ReplayAsset.objects.all():
        prefix = str(Path(asset.storage_key).parent).replace("\\", "/") + "/previews/"
        path = private_path(prefix)
        if path.exists():
            shutil.rmtree(path)
        if asset.storage_provider == "GCS" and (
            previews.filter(asset=asset).exists() or settings.GCS_PREVIEW_WRITES_QUALIFIED
        ):
            storage_for(asset).delete_preview(prefix)
    previews.update(state="PURGED", reserved_bytes=0, manifest={}, quality={}, source_sha256="")
