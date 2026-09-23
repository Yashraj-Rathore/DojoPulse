import shutil
import sys

import pytest

from analysis.media import probe
from analysis.process import run_bounded
from tools.analyze_capture import analyze

pytestmark = pytest.mark.media


def test_malformed_and_oversized_source(tmp_path):
    source = tmp_path / "invalid.mp4"
    source.write_bytes(b"not video")
    with pytest.raises(ValueError):
        probe(source)
    with pytest.raises(ValueError, match="FILE_TOO_LARGE"):
        probe(source, {"max_bytes": 1})


def test_process_timeout_and_output_limit():
    with pytest.raises(ValueError, match="TIMEOUT"):
        run_bounded([sys.executable, "-c", "import time; time.sleep(3)"], timeout=0.1)
    with pytest.raises(ValueError, match="OUTPUT_LIMIT"):
        run_bounded([sys.executable, "-c", "print('x'*100000)"], max_output=100)


def test_process_memory_exhaustion_is_killed():
    with pytest.raises(ValueError, match="MEMORY_LIMIT"):
        run_bounded(
            [sys.executable, "-c", "import time; data=bytearray(64*1024*1024); time.sleep(3)"],
            max_rss=32 * 1024 * 1024,
        )


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg absent")
def test_generated_video_end_to_end_abstains(tmp_path):
    source = tmp_path / "synthetic.mp4"
    run_bounded(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=1920x1080:r=60:d=0.5",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        timeout=30,
    )
    result = analyze(source, tmp_path / "report.json")
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["opportunities"] == []
    assert result["automatic_gameplay_validated"] is False
    assert result["cost"]["derived_bytes"] > 0
