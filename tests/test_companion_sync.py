import copy
import os
import shutil
import subprocess
import time
import urllib.error
from unittest.mock import Mock

import pytest

from companion.credentials import StateStore, crypt
from companion.sync import (
    NoRedirect,
    SyncEngine,
    TransferError,
    Transport,
    locked_recording,
    retry_delay,
    selected_file,
    server_origin,
)


class MemoryStore:
    def __init__(self):
        self.state = {}

    def load(self):
        return copy.deepcopy(self.state)

    def save(self, state):
        self.state = copy.deepcopy(state)


def container():
    return b"".join(
        (8 + len(body)).to_bytes(4, "big") + name + body
        for name, body in [(b"ftyp", b"isom"), (b"moov", b"fixture"), (b"mdat", b"x" * 80)]
    )


class FakeTransfer:
    def __init__(self):
        self.received, self.content, self.lost, self.complete = 0, b"", False, False
        self.offsets = []

    def request(self, method, path, body=None, offset=None):
        if method == "PUT":
            assert offset == self.received
            self.offsets.append(offset)
            self.content += body
            self.received += len(body)
            if not self.lost:
                self.lost = True
                raise TransferError("NETWORK_RETRY")  # Server accepted bytes; response lost.
            return {"received_bytes": self.received}
        if path.endswith("complete"):
            self.complete = True
        if method == "DELETE":
            return {"state": "CANCELLED"}
        return {
            "id": "00000000-0000-4000-8000-000000000001",
            "state": "VERIFYING" if self.complete else "UPLOADING",
            "storage_provider": "LOCAL",
            "chunk_bytes": 25,
            "received_bytes": self.received,
        }


def ready(tmp_path, transfer=None):
    path = tmp_path / "fixture.mp4"
    path.write_bytes(container())
    store, transport = MemoryStore(), transfer or FakeTransfer()
    engine = SyncEngine(store, transport, check_media=lambda path: {})
    engine.select_folder(tmp_path, include_existing=True)
    engine.enabled = True
    return engine, store, transport, path


def test_lost_response_restart_resumes_confirmed_offset_and_deduplicates(tmp_path):
    engine, store, transfer, path = ready(tmp_path)
    engine.tick(100)
    assert engine.tick(111) == "NETWORK_RETRY"
    assert transfer.offsets == [0] and transfer.received == 25
    restarted = SyncEngine(store, transfer, check_media=lambda path: {})
    assert not restarted.enabled and restarted.tick(120) == "Paused"
    restarted.enabled = True
    restarted.tick(120)
    assert transfer.content == path.read_bytes() and transfer.offsets == [0, 25, 50, 75, 100]
    assert next(iter(store.state["receipts"].values()))["state"] == "VERIFYING"


def test_growing_unfinished_changed_and_outside_files_stay_local(tmp_path):
    engine, store, transfer, path = ready(tmp_path)
    engine.tick(100)
    path.write_bytes(path.read_bytes() + b"growing")
    engine.tick(111)
    engine.tick(122)
    assert not store.state["receipts"] and not transfer.offsets
    path.write_bytes(container())
    engine.tick(123)
    engine.tick(134)
    path.write_bytes(b"changed")
    engine.tick(140)
    assert next(iter(store.state["receipts"].values()))["state"] == "REJECTED"
    outside = tmp_path.parent / "outside.mp4"
    outside.write_bytes(container())
    with pytest.raises(ValueError):
        selected_file(tmp_path, outside)
    sub = tmp_path / "subfolder"
    sub.mkdir()
    nested = sub / "nested.mp4"
    nested.write_bytes(container())
    with pytest.raises(ValueError):
        selected_file(tmp_path, nested)


def test_existing_files_opt_in_and_receipts_bounded(tmp_path):
    engine, store, _, _ = ready(tmp_path)
    engine.enabled = False
    engine.select_folder(tmp_path)
    engine.enabled = True
    engine.tick(100)
    engine.tick(111)
    assert not store.state["receipts"]
    new = tmp_path / "new.mp4"
    new.write_bytes(container())
    engine.tick(112)
    engine.tick(123)
    assert len(store.state["receipts"]) == 1


def test_pause_during_local_media_validation_never_reserves_remote_bytes(tmp_path):
    engine, store, transfer, _ = ready(tmp_path)

    def pause(path):
        engine.enabled = False

    engine.check_media = pause
    engine.tick(100)
    assert engine.tick(111) == "Paused"
    assert not store.state["receipts"] and not transfer.offsets


@pytest.mark.parametrize("response", ["REMOVED", "DUPLICATE"])
def test_remote_tombstone_stops_receipt_driven_resurrection(tmp_path, response):
    class Remote:
        calls = 0

        def request(self, *args):
            self.calls += 1
            return {"state": response}

    engine, store, transport, _ = ready(tmp_path, Remote())
    engine.tick(100)
    engine.tick(111)
    engine.tick(130)
    assert (
        transport.calls == 1 and next(iter(store.state["receipts"].values()))["state"] == response
    )


def test_retry_after_and_access_revocation(tmp_path):
    class RateLimited:
        def request(self, *args):
            raise TransferError("SERVICE_RETRY", retry_after=600)

    engine, store, _, _ = ready(tmp_path, RateLimited())
    engine.tick(100)
    engine.tick(111)
    assert next(iter(store.state["receipts"].values()))["retry_at"] == 711

    class Revoked:
        def request(self, *args):
            raise TransferError("DEVICE_ACCESS_STOPPED", fatal=True)

    engine.transport = Revoked()
    engine.tick(712)
    assert not engine.enabled
    assert retry_delay("600") == 600 and retry_delay("invalid") == 60


def test_cancel_preserves_original_and_terminal_receipt(tmp_path):
    engine, store, _, path = ready(tmp_path)
    engine.tick(100)
    engine.tick(111)
    engine.cancel_requested = True
    engine.tick(115)
    assert not engine.enabled and path.exists()
    assert next(iter(store.state["receipts"].values()))["state"] == "CANCELLED"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://user:secret@example.com",
        "https://example.com/path",
        "https://example.com?upload_url=secret",
        "http://localhost:8000",
        "http://127.0.0.1:9000",
    ],
)
def test_origin_never_accepts_arbitrary_destinations(url):
    with pytest.raises(ValueError):
        server_origin(url, local_development=True)
    transport = Transport("https://example.com")
    with pytest.raises(ValueError):
        transport.request("GET", "https://other.example/steal")


def test_redirect_never_forwards_device_credentials():
    transport = Transport("https://fixture.example", "private-fixture-token")
    transport.opener = Mock()
    transport.opener.open.side_effect = urllib.error.HTTPError(
        "https://fixture.example/api/companion/uploads",
        302,
        "redirect",
        {"Location": "https://foreign.example/steal"},
        None,
    )
    with pytest.raises(TransferError) as error:
        transport.request("POST", "/api/companion/uploads", {})
    assert error.value.fatal and transport.opener.open.call_count == 1
    request = transport.opener.open.call_args.args[0]
    assert request.full_url.startswith("https://fixture.example/")
    assert (
        NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://foreign.example")
        is None
    )


def test_windows_dpapi_and_exclusive_read_against_writers(tmp_path):
    if os.name != "nt":
        pytest.skip("Actual Windows DPAPI/share modes require Windows")
    store = StateStore(tmp_path / "state.dpapi")
    state = {"credential": "fixture-private-device-token", "receipts": {"fixture": {"offset": 25}}}
    store.save(state)
    assert store.load() == state and b"fixture-private-device-token" not in store.path.read_bytes()
    with pytest.raises(ValueError):
        crypt(b"not-dpapi", decrypt=True)
    path = tmp_path / "fixture.mp4"
    path.write_bytes(container())
    with locked_recording(path):
        with pytest.raises(PermissionError):
            path.write_bytes(b"write during transfer")


def test_linked_recording_and_linked_root_are_rejected(tmp_path):
    folder = tmp_path / "selected"
    folder.mkdir()
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(container())
    link = folder / "linked.mp4"
    root_link = tmp_path / "linked-root"
    try:
        link.symlink_to(outside)
        root_link.symlink_to(folder, target_is_directory=True)
    except OSError:
        pytest.skip(
            "OS symlink privilege unavailable; reparse acceptance remains a Windows delivery gate"
        )
    with pytest.raises(ValueError):
        selected_file(folder, link)
    engine = SyncEngine(MemoryStore(), FakeTransfer())
    with pytest.raises(ValueError):
        engine.select_folder(root_link)


@pytest.mark.django_db
def test_real_supported_mp4_sync_worker_and_private_playback(tmp_path, settings, django_user_model):
    from django.core.management import call_command
    from rest_framework.test import APIClient

    from backend.core.models import GameplayEvent, Match
    from backend.core.resumable import verify
    from tests.test_companion import paired

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg/FFprobe required for actual controlled media test")
    settings.LOCAL_OPERATOR_UPLOADS = settings.LOCAL_RECORDING_COMPANION = True
    settings.DEBUG = True
    settings.PARSER_BACKEND = (
        "local"  # Explicit local operator check, production isolation unchanged.
    )
    settings.PRIVATE_DATA_ROOT = tmp_path / "private"
    folder = tmp_path / "captures"
    folder.mkdir()
    path = folder / "controlled.mp4"
    subprocess.run(
        [
            shutil.which("ffmpeg"),
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=1920x1080:r=60",
            "-t",
            "0.2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-threads",
            "1",
            str(path),
        ],
        check=True,
        timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    owner = django_user_model.objects.create_user("actual-media-companion", is_staff=True)
    web = APIClient()
    web.force_authenticate(owner)
    client, _ = paired(web)

    class APITransfer:
        def request(self, method, url, body=None, offset=None):
            if method == "PUT":
                response = client.put(
                    url,
                    body,
                    content_type="application/octet-stream",
                    HTTP_UPLOAD_OFFSET=str(offset),
                )
            else:
                response = (
                    getattr(client, method.lower())(url, body, format="json")
                    if method != "GET"
                    else client.get(url)
                )
            assert response.status_code < 300, response.data
            return response.data

    store = MemoryStore()
    engine = SyncEngine(store, APITransfer())
    engine.select_folder(folder, include_existing=True)
    engine.enabled = True
    now = time.time()
    engine.tick(now)
    engine.tick(now + 11)
    receipt = next(iter(store.state["receipts"].values()))
    assert receipt["state"] == "VERIFYING"
    assert verify(receipt["id"])
    call_command("process_runs", once=True)
    result = web.get("/api/synced-recordings").data["recordings"][0]
    assert result["availability"] == "AVAILABLE", result
    response = web.get(result["media_url"], HTTP_RANGE="bytes=0-31")
    assert (
        response.status_code == 206
        and b"".join(response.streaming_content) == path.read_bytes()[:32]
    )
    assert not Match.objects.exists() and not GameplayEvent.objects.exists()
