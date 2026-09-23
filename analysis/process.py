"""Bounded local subprocess execution; hosted hostile-media isolation is a separate gate."""

import subprocess
import tempfile
import time
from dataclasses import dataclass

import psutil


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
) -> ProcessResult:
    start = time.monotonic()
    peak = 0
    cpu = 0.0
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
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
                if output.tell() > max_output or errors.tell() > max_output:
                    raise ValueError("DECODER_OUTPUT_LIMIT")
                time.sleep(0.02)
            if proc.returncode:
                raise ValueError("DECODER_REJECTED_INPUT")
            output.seek(0)
            data = output.read(max_output + 1)
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
