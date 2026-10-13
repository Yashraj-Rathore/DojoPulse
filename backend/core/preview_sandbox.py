"""Independent isolated normalizer profile; never mount a host output or decode on host."""

import json
import subprocess
import time
from pathlib import Path

from django.conf import settings

from analysis.preview_bundle import FILES
from analysis.process import execution_check, run_bounded
from backend.core.parser import sandbox_command

COPY_FILE = """
import os, stat, sys
parent,filename=os.path.split(sys.argv[1])
directory=os.open(parent,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
try:
    descriptor=os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
finally:
    os.close(directory)
info=os.fstat(descriptor)
if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not 0 < info.st_size <= int(sys.argv[2]):
    raise SystemExit(2)
with os.fdopen(descriptor,'rb') as source:
    remaining=info.st_size
    while remaining:
        data=source.read(min(65536,remaining))
        if not data: raise SystemExit(2)
        sys.stdout.buffer.write(data)
        remaining-=len(data)
    if source.read(1): raise SystemExit(2)
"""


def command(image, name, source, metadata):
    argv = sandbox_command(image, name, source, metadata)
    argv.remove("--rm")
    argv.insert(2, "--detach")
    for old, new in (
        ("dojopulse.role=parser", "dojopulse.role=preview"),
        ("1g", "3g"),
        (
            "/work:rw,noexec,nosuid,nodev,size=512m,mode=1777",
            "/work:rw,noexec,nosuid,nodev,size=1152m,mode=1777",
        ),
    ):
        argv = [new if item == old else item for item in argv]
    argv[argv.index("--cpus") + 1] = "2"
    argv[-1:] = ["--entrypoint", "python", image, "-m", "tools.sandbox_recording_preview"]
    return argv


def remove_container(name):
    result = subprocess.run(
        ["docker", "rm", "--force", name],
        timeout=15,
        capture_output=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode and b"No such container" not in result.stderr:
        raise ValueError("PREVIEW_CLEANUP_UNCONFIRMED")


def normalize_isolated(source, destination, name):
    destination = Path(destination)
    if settings.PARSER_BACKEND == "local":
        if not settings.DEBUG or not settings.LOCAL_OPERATOR_UPLOADS:
            raise ValueError("LOCAL_PARSER_DISABLED")
        from analysis.normalization import normalize

        normalize(source, destination)
        return {"contract": "trusted-local-preview/1"}
    if settings.PARSER_BACKEND != "docker":
        raise ValueError("UNKNOWN_PARSER_BACKEND")
    metadata = destination.parent / "preview-input.json"
    metadata.write_text("{}", encoding="utf-8")
    metadata.chmod(0o644)
    started = time.monotonic()
    try:
        run_bounded(
            command(settings.PARSER_IMAGE, name, source, metadata), timeout=30, max_output=8192
        )
        while True:
            check = execution_check.get()
            if check:
                check()
            if time.monotonic() - started > 1800:
                raise ValueError("DECODER_TIMEOUT")
            state = run_bounded(
                ["docker", "inspect", "--format", "{{.State.Running}}", name],
                timeout=15,
                max_output=8192,
            ).stdout.strip()
            if state != b"true":
                raise ValueError("PREVIEW_CONTAINER_STOPPED")
            try:
                ready = run_bounded(
                    ["docker", "exec", name, "cat", "/work/status.json"],
                    timeout=15,
                    max_output=8192,
                )
            except ValueError as exc:
                if str(exc) != "DECODER_REJECTED_INPUT":
                    raise
                time.sleep(1)
                continue
            try:
                status = json.loads(ready.stdout)
            except (RecursionError, ValueError):
                raise ValueError("INVALID_PREVIEW_BUNDLE") from None
            if status != {"state": "READY"}:
                raise ValueError("PREVIEW_MEDIA_REJECTED")
            break
        destination.mkdir(exist_ok=False)
        for filename, maximum in FILES.items():
            path = destination / filename
            # Fixed regular-file descriptors and bounded raw bytes. Never extract tar,
            # copy a directory tree, follow links or mount a writable host output.
            run_bounded(
                [
                    "docker",
                    "exec",
                    name,
                    "python",
                    "-c",
                    COPY_FILE,
                    f"/work/bundle/{filename}",
                    str(maximum),
                ],
                timeout=90,
                max_output=maximum,
                stdout_path=path,
            )
            if path.is_symlink() or not path.is_file():
                raise ValueError("INVALID_PREVIEW_BUNDLE")
        return {"contract": "isolated-preview/1", "image_sha256": settings.PARSER_IMAGE}
    finally:
        try:
            remove_container(name)
        except (OSError, subprocess.TimeoutExpired):
            raise ValueError("PREVIEW_CLEANUP_UNCONFIRMED") from None
