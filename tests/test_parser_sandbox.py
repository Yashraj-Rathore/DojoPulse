"""Opt-in real Docker checks. No hostile executable or external provider is contacted."""

import json
import os
import shutil
import struct
import subprocess
import time
import uuid

import pytest

from analysis.process import execution_check, run_bounded
from backend.core.parser import analyze_isolated, sandbox_command

IMAGE = os.getenv("PARSER_TEST_IMAGE", "")
pytestmark = [
    pytest.mark.sandbox,
    pytest.mark.skipif(
        not IMAGE, reason="Set PARSER_TEST_IMAGE to an immutable locally built image ID"
    ),
]


@pytest.fixture
def inputs(tmp_path, settings):
    settings.PARSER_IMAGE = IMAGE
    settings.PARSER_BACKEND = "docker"
    source = tmp_path / "source.mp4"
    source.write_bytes(b"malformed media fixture")
    metadata = tmp_path / "metadata.json"
    metadata.write_text("{}")
    # Docker on Linux runs as a distinct UID; pytest parent directories default to 0700.
    source.chmod(0o644)
    metadata.chmod(0o644)
    return source, metadata


def diagnostic(inputs, code, timeout=30):
    source, metadata = inputs
    name = "dojopulse-test-" + uuid.uuid4().hex
    command = sandbox_command(IMAGE, name, source, metadata)
    command[-1:] = ["--entrypoint", "python", IMAGE, "-c", code]
    try:
        return run_bounded(command, timeout=timeout, max_output=8192).stdout
    finally:
        subprocess.run(["docker", "rm", "-f", name], timeout=15, capture_output=True, check=False)


def test_actual_isolation_network_mounts_identity_cgroups(inputs):
    code = r"""
import json, os, pathlib, socket
def read(p): return pathlib.Path(p).read_text().strip()
assert os.getuid() == 10001
status = read('/proc/self/status')
assert 'CapEff:\t0000000000000000' in status
assert 'NoNewPrivs:\t1' in status
for p in ['/app/write-denied', '/input/source.mp4']:
    try: open(p, 'wb')
    except OSError: pass
    else: raise AssertionError('writable protected path')
assert {name for _, name in socket.if_nameindex()} == {'lo'}
for secret in ['DATABASE_URL', 'DJANGO_SECRET_KEY', 'AWS_SECRET_ACCESS_KEY']:
    assert secret not in os.environ
assert not pathlib.Path('/var/run/docker.sock').exists()
root = pathlib.Path('/sys/fs/cgroup')
if (root/'memory.max').exists():
    memory = read(root/'memory.max')
    assert read(root/'memory.swap.max') == '0'
    assert read(root/'pids.max') == '64'
    quota, period = map(int, read(root/'cpu.max').split())
else:
    memory = read(root/'memory/memory.limit_in_bytes')
    assert read(root/'memory/memory.memsw.limit_in_bytes') == memory
    assert read(root/'pids/pids.max') == '64'
    quota = int(read(root/'cpu/cpu.cfs_quota_us'))
    period = int(read(root/'cpu/cpu.cfs_period_us'))
assert memory == '1073741824'
assert quota == period
assert os.statvfs('/work').f_blocks * os.statvfs('/work').f_frsize <= 512*1024*1024
assert os.statvfs('/tmp').f_blocks * os.statvfs('/tmp').f_frsize <= 64*1024*1024
print(json.dumps({'uid':os.getuid(), 'memory':memory, 'cpu':[quota,period], 'network':'loopback-only'}))
"""
    assert json.loads(diagnostic(inputs, code))["uid"] == 10001


def test_malformed_media_abstains_without_host_artifacts(inputs, tmp_path):
    source, metadata = inputs
    result = analyze_isolated(source, tmp_path / "report.json", metadata)
    assert result["status"] == "FAILED" and result["opportunities"] == []
    assert not (tmp_path / "report.json").exists()


def test_actual_tmpfs_limit_and_oom(inputs):
    code = r"""
import errno
try:
    with open('/work/fill', 'wb', buffering=0) as stream:
        for _ in range(520): stream.write(b'x'*1024*1024)
except OSError as error:
    assert error.errno == errno.ENOSPC
    print('SCRATCH_LIMIT_ENFORCED')
else: raise AssertionError('scratch was not bounded')
"""
    assert b"SCRATCH_LIMIT_ENFORCED" in diagnostic(inputs, code)
    with pytest.raises(ValueError, match="DECODER_REJECTED_INPUT"):
        diagnostic(inputs, "data=bytearray(2*1024*1024*1024)")


def test_pid_limit_and_orphan_deadline(inputs):
    code = r"""
import subprocess, errno
children = []
try:
    for _ in range(100):
        children.append(subprocess.Popen(['sleep', '5']))
except OSError as error:
    assert error.errno == errno.EAGAIN
    assert len(children) < 64
    print('PID_LIMIT_ENFORCED')
finally:
    for child in children: child.kill()
    for child in children: child.wait()
"""
    assert b"PID_LIMIT_ENFORCED" in diagnostic(inputs, code)
    started = time.monotonic()
    with pytest.raises(ValueError, match="DECODER_REJECTED_INPUT"):
        diagnostic(
            inputs,
            "from tools.sandbox_capture import arm_deadline; import time; arm_deadline(1); time.sleep(60)",
            timeout=15,
        )
    assert time.monotonic() - started < 15


def test_cancel_stops_and_removes_container(inputs, tmp_path, monkeypatch):
    source, metadata = inputs

    def sleeping_command(*args):
        command = sandbox_command(*args)
        command[-1:] = ["--entrypoint", "python", IMAGE, "-c", "import time; time.sleep(30)"]
        return command

    monkeypatch.setattr("backend.core.parser.sandbox_command", sleeping_command)
    started = time.monotonic()

    def cancel():
        if time.monotonic() - started > 0.4:
            raise ValueError("RUN_REVOKED")

    token = execution_check.set(cancel)
    # Controlled long-running child makes cancellation independent of decoder speed.
    try:
        with pytest.raises(ValueError, match="RUN_REVOKED"):
            analyze_isolated(source, tmp_path / "report.json", metadata)
    finally:
        execution_check.reset(token)
    names = subprocess.run(
        ["docker", "ps", "-aq", "--filter", "label=dojopulse.role=parser"],
        capture_output=True,
        check=True,
        timeout=15,
    ).stdout.strip()
    assert not names


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg absent")
def test_actual_valid_capture_remains_review_required(inputs, tmp_path):
    source, metadata = inputs
    run_bounded(
        [
            "ffmpeg",
            "-y",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=1920x1080:r=60:d=0.5",
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ]
    )
    result = analyze_isolated(source, tmp_path / "report.json", metadata)
    assert result["status"] == "REVIEW_REQUIRED", result
    assert result["source"]["duration_seconds"] == 0.5
    assert result["opportunities"] == []
    assert not result["artifacts_retained"]


@pytest.mark.skipif(
    not os.getenv("PARSER_MAX_PROFILE"),
    reason="Set PARSER_MAX_PROFILE=1 for the 600s/512MiB fixture",
)
def test_maximum_duration_and_size_capture(inputs, tmp_path):
    source, metadata = inputs
    run_bounded(
        [
            "ffmpeg",
            "-y",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=1920x1080:r=60:d=600",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-threads",
            "2",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        timeout=300,
    )
    # A valid MP4 free box exercises the exact byte ceiling without invented gameplay.
    remaining = 536870912 - source.stat().st_size
    assert remaining > 8
    with source.open("ab") as stream:
        stream.write(struct.pack(">I4s", remaining, b"free"))
        remaining -= 8
        while remaining:
            size = min(remaining, 1024 * 1024)
            stream.write(b"\0" * size)
            remaining -= size
    result = analyze_isolated(source, tmp_path / "report.json", metadata)
    assert result["status"] == "REVIEW_REQUIRED", result
    assert result["source"]["frame_count"] == 36000
    assert result["source"]["bytes"] == 536870912
    assert result["source"]["duration_seconds"] == 600
    print(json.dumps(result))
    with source.open("ab") as stream:
        stream.write(b"x")
    rejected = analyze_isolated(source, tmp_path / "report.json", metadata)
    assert rejected["status"] == "FAILED" and "FILE_TOO_LARGE" in rejected["issues"]
