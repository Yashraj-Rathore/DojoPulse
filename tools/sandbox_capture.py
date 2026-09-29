"""Container entrypoint: bounded lifetime, ephemeral artifacts, JSON-only result."""

import json
import signal
import sys
from pathlib import Path

from tools.analyze_capture import analyze


def arm_deadline(seconds: int = 300) -> None:
    if sys.platform == "win32":
        raise RuntimeError("Sandbox entrypoint requires Linux")

    def expired(signum: int, frame: object) -> None:
        raise SystemExit(124)

    signal.signal(signal.SIGALRM, expired)
    signal.alarm(seconds)


def main() -> None:
    # PID 1 also exits if the coordinator dies. Docker tears down its descendants.
    arm_deadline()  # Explicit handler is required for Linux container PID 1.
    report = analyze(
        Path("/input/source.mp4"), Path("/work/report.json"), Path("/input/metadata.json")
    )
    report.pop("artifacts", None)
    report["artifacts_retained"] = False
    print(json.dumps(report, allow_nan=False))


if __name__ == "__main__":
    main()
