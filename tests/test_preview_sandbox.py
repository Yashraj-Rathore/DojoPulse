"""Actual default Docker preview profile and bounded retrieval; no hosted deployment claim."""

import json
import os
import subprocess
from uuid import uuid4

import pytest

from analysis.media import file_hash
from analysis.preview_bundle import validate_bundle
from analysis.process import execution_check, run_bounded
from backend.core.preview_sandbox import COPY_FILE, command, normalize_isolated, remove_container

IMAGE = os.getenv("PARSER_TEST_IMAGE", "")
pytestmark = [
    pytest.mark.sandbox,
    pytest.mark.skipif(not IMAGE, reason="Preview Docker image not configured"),
]


@pytest.fixture
def source(tmp_path, settings):
    settings.PARSER_IMAGE = IMAGE
    settings.PARSER_BACKEND = "docker"
    path = tmp_path / "source.mp4"
    path.write_bytes(b"invalid")
    path.chmod(0o644)
    return path


def test_actual_preview_profile_rejects_network_secrets_and_host_writes(source, tmp_path):
    metadata = tmp_path / "metadata.json"
    metadata.write_text("{}")
    metadata.chmod(0o644)
    name = "dojopulse-preview-" + uuid4().hex + "-1"
    argv = command(IMAGE, name, source, metadata)
    argv[-2:] = ["-c", "import time; time.sleep(60)"]
    try:
        run_bounded(argv)
        code = """
import os,pathlib,socket,json
assert os.getuid()==10001
assert {n for _,n in socket.if_nameindex()}=={'lo'}
status=pathlib.Path('/proc/self/status').read_text()
assert 'CapEff:\\t0000000000000000' in status and 'NoNewPrivs:\\t1' in status
root=pathlib.Path('/sys/fs/cgroup')
assert (root/'memory.max').read_text().strip()=='3221225472'
assert (root/'memory.swap.max').read_text().strip()=='0'
quota,period=map(int,(root/'cpu.max').read_text().split()); assert quota==2*period
assert (root/'pids.max').read_text().strip()=='64'
for path in ['/app/denied','/input/source.mp4']:
    try: open(path,'wb')
    except OSError: pass
    else: raise AssertionError('protected write')
assert not pathlib.Path('/var/run/docker.sock').exists()
assert not any(k in os.environ for k in ['DATABASE_URL','DJANGO_SECRET_KEY','GOOGLE_APPLICATION_CREDENTIALS'])
print(json.dumps({'isolated':True}))
"""
        result = run_bounded(["docker", "exec", name, "python", "-c", code], max_output=8192)
        assert json.loads(result.stdout) == {"isolated": True}
        for attack in [
            "os.symlink('/input/source.mp4',p)",
            "os.mkfifo(p)",
            "open('/work/other','wb').write(b'x');os.link('/work/other',p)",
            "os.rmdir('/work/bundle');os.mkdir('/work/else');open('/work/else/preview.mp4','wb').write(b'x');os.symlink('/work/else','/work/bundle')",
        ]:
            setup = (
                "import os;os.makedirs('/work/bundle',exist_ok=True);p='/work/bundle/preview.mp4';"
                + attack
            )
            run_bounded(["docker", "exec", name, "python", "-c", setup])
            with pytest.raises(ValueError, match="DECODER_REJECTED_INPUT"):
                run_bounded(
                    [
                        "docker",
                        "exec",
                        name,
                        "python",
                        "-c",
                        COPY_FILE,
                        "/work/bundle/preview.mp4",
                        "100",
                    ],
                    max_output=8192,
                    timeout=5,
                )
            run_bounded(
                [
                    "docker",
                    "exec",
                    name,
                    "python",
                    "-c",
                    "import os;p='/work/bundle/preview.mp4';os.unlink(p) if os.path.lexists(p) else None",
                ]
            )
    finally:
        remove_container(name)


def test_actual_hevc_vfr_binary_retrieval_and_cleanup(source, tmp_path):
    from tests.test_recording_normalization import generate

    source.unlink()
    generate(source, codec="hevc", gaps=True, full_range=True)
    source.chmod(0o644)
    before = file_hash(source)
    name = "dojopulse-preview-" + uuid4().hex + "-1"
    result = normalize_isolated(source, tmp_path / "bundle", name)
    quality = validate_bundle(tmp_path / "bundle", before)
    assert result["image_sha256"] == IMAGE and quality["gaps_over_limit"] == 1
    assert quality["frame_count"] == 29 and quality["precise_gameplay_analysis_approved"] is False
    assert file_hash(source) == before
    assert subprocess.run(["docker", "inspect", name], capture_output=True).returncode != 0


def test_actual_malformed_media_has_no_ready_artifacts(source, tmp_path):
    name = "dojopulse-preview-" + uuid4().hex + "-1"
    with pytest.raises(ValueError, match="MEDIA_REJECTED"):
        normalize_isolated(source, tmp_path / "bundle", name)
    assert not (tmp_path / "bundle").exists()
    assert subprocess.run(["docker", "inspect", name], capture_output=True).returncode != 0


def test_actual_revocation_removes_unique_container(source, tmp_path):
    name = "dojopulse-preview-" + uuid4().hex + "-1"
    calls = 0

    def cancelled():
        nonlocal calls
        calls += 1
        if calls > 2:
            raise ValueError("RUN_REVOKED")

    guard = execution_check.set(cancelled)
    try:
        with pytest.raises(ValueError, match="RUN_REVOKED"):
            normalize_isolated(source, tmp_path / "bundle", name)
    finally:
        execution_check.reset(guard)
    assert subprocess.run(["docker", "inspect", name], capture_output=True).returncode != 0
