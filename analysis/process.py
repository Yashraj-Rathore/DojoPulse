"""Bounded local subprocess execution; hosted hostile-media isolation is a separate gate."""

import subprocess
import tempfile
import time
from collections.abc import Callable
from contextlib import ExitStack
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

import psutil

execution_check: ContextVar[Callable[[], None] | None] = ContextVar("execution_check", default=None)


@dataclass(frozen=True)
class ProcessResult:
    stdout: bytes
    seconds: float
    cpu_seconds: float
    peak_rss_bytes: int


def run_bounded(
    argv: list[str],
    *,
    timeout: float = 30,
    max_output: int = 8_000_000,
    max_rss: int = 1_073_741_824,
    file_limits: dict[Path, int] | None = None,
    reject_stderr: bool = False,
    stdout_path: Path | None = None,
) -> ProcessResult:
    start = time.monotonic()
    peak = 0
    cpu = 0.0

    def check_files() -> None:
        for path, maximum in (file_limits or {}).items():
            if path.exists() and path.stat().st_size > maximum:
                raise ValueError("DECODER_FILE_LIMIT")

    with ExitStack() as stack:
        output = stack.enter_context(
            stdout_path.open("xb") if stdout_path else tempfile.TemporaryFile()
        )
        errors = stack.enter_context(tempfile.TemporaryFile())
        check = execution_check.get()
        if check:
            check()
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=errors,
            shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        monitor = psutil.Process(proc.pid)
        try:
            while proc.poll() is None:
                if check:
                    check()
                try:
                    processes = [monitor, *monitor.children(recursive=True)]
                    peak = max(peak, sum(p.memory_info().rss for p in processes))
                    cpu = max(cpu, sum(sum(p.cpu_times()[:2]) for p in processes))
                except psutil.NoSuchProcess:
                    pass
                if time.monotonic() - start > timeout:
                    raise ValueError("DECODER_TIMEOUT")
                if peak > max_rss:
                    raise ValueError("DECODER_MEMORY_LIMIT")
                if output.tell() > max_output or errors.tell() > min(max_output, 8_000_000):
                    raise ValueError("DECODER_OUTPUT_LIMIT")
                check_files()
                time.sleep(0.02)
            if proc.returncode:
                raise ValueError("DECODER_REJECTED_INPUT")
            check_files()
            if errors.tell() > min(max_output, 8_000_000):
                raise ValueError("DECODER_OUTPUT_LIMIT")
            if reject_stderr and errors.tell():
                raise ValueError("DECODER_REPORTED_ERRORS")
            if stdout_path and output.tell() > max_output:
                raise ValueError("DECODER_OUTPUT_LIMIT")
            output.seek(0)
            data = b"" if stdout_path else output.read(max_output + 1)
            if len(data) > max_output:
                raise ValueError("DECODER_OUTPUT_LIMIT")
            return ProcessResult(data, time.monotonic() - start, cpu, peak)
        finally:
            if proc.poll() is None:
                try:
                    for child in monitor.children(recursive=True):
                        child.kill()
                except psutil.NoSuchProcess:
                    pass
                proc.kill()
            proc.wait(timeout=5)
