"""No network/credentials. Keep tmpfs alive for bounded coordinator retrieval, then die."""

import json
import time
from pathlib import Path

from analysis.normalization import normalize
from tools.sandbox_capture import arm_deadline


def main() -> None:
    arm_deadline(1800)
    try:
        normalize(Path("/input/source.mp4"), Path("/work/bundle"))
        result = {"state": "READY"}
    except (OSError, ValueError, TypeError, KeyError):
        result = {"state": "FAILED", "code": "PREVIEW_MEDIA_REJECTED"}
    Path("/work/status.json").write_text(json.dumps(result), encoding="utf-8")
    # Stopping the container destroys tmpfs. The credentialed coordinator copies only
    # three fixed files while it is alive, then removes this exact container.
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
