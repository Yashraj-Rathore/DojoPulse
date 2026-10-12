"""Actual bounded codec conversions are software fixtures, never gameplay approval."""

import copy
import json
import shutil
import subprocess
import sys

import pytest

from analysis import normalization
from analysis.contracts import digest
from analysis.media import file_hash, probe
from analysis.normalization import normalize, policy, timestamp, verify_preservation
from analysis.process import run_bounded
from analysis.timing import timing_quality, timing_window_supported


def generate(path, *, codec="h264", gaps=False, offset=0, audio=True, full_range=False):
    encoder = "libx265" if codec == "hevc" else "libx264"
    filters = []
    if gaps:
        filters.append("select=not(eq(n\\,8))")
    if offset:
        filters.append(f"setpts=PTS+{offset}/TB")
    argv = [
        "ffmpeg",
        "-v",
        "error",
        "-nostdin",
        "-n",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=s=1920x1080:r=60:d=0.5",
    ]
    if audio:
        argv += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=0.5"]
    argv += ["-map", "0:v:0"]
    if audio:
        argv += ["-map", "1:a:0", "-c:a", "aac"]
    if filters:
        argv += ["-vf", ",".join(filters)]
    argv += ["-c:v", encoder, "-threads", "2", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    if codec == "hevc":
        argv += ["-x265-params", "pools=1:frame-threads=1:log-level=error"]
    if full_range:
        argv += [
            "-color_range",
            "pc",
            "-colorspace",
            "bt709",
            "-color_trc",
            "bt709",
            "-color_primaries",
            "bt709",
        ]
    argv += [
        "-fps_mode",
        "passthrough",
        "-enc_time_base",
        "1:60000000",
        "-video_track_timescale",
        "60000000",
        str(path),
    ]
    run_bounded(argv, timeout=60)


@pytest.mark.media
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg absent")
@pytest.mark.parametrize(
    ("codec", "gaps", "offset", "audio", "full_range"),
    [
        ("h264", False, 0, True, False),
        ("hevc", True, 0, True, True),
        ("hevc", True, 2, False, False),
    ],
)
def test_actual_conversion_preserves_every_frame_pts_gap_audio_and_source(
    tmp_path, codec, gaps, offset, audio, full_range
):
    source = tmp_path / "private-owner-export.mp4"
    generate(source, codec=codec, gaps=gaps, offset=offset, audio=audio, full_range=full_range)
    original_hash = file_hash(source)
    output = tmp_path / "bundle"
    result = normalize(source, output, game_build="operator-declared-build")
    assert result["source"]["sha256"] == file_hash(source) == original_hash
    assert result["derivative"]["sha256"] == file_hash(output / "preview.mp4")
    assert result["status"] == "PREVIEW_READY"
    assert result["analysis_version"] == "local-recording-normalizer/1"
    assert result["source"]["color"] == result["derivative"]["color"]
    assert result["quality"]["frame_count"] == (29 if gaps else 30)
    assert result["quality"]["gaps_over_limit"] == int(gaps)
    assert result["quality"]["first_pts_us"] == offset * 1_000_000
    assert result["preservation"]["maximum_video_pts_error_us"] == 0
    assert result["preservation"]["maximum_audio_timestamp_error_us"] <= 22
    assert result["strict_capture_profile_media_compatible"] is (not gaps)
    assert result["precise_gameplay_analysis_approved"] is False
    assert result["scientific_gate_approval"] is False
    assert result["canonical_publication"] is False
    assert result["provenance"]["automatic_acquisition"] is False
    assert result["provenance"]["build_verified"] is False
    timeline = json.loads((output / "timeline.json").read_text("utf-8"))
    assert timeline["source_pts_us"] == timeline["derived_pts_us"]
    assert result["timeline"]["content_hash"] == digest(timeline)
    assert result == json.loads((output / "report.json").read_text("utf-8"))
    assert set(p.name for p in output.iterdir()) == {"preview.mp4", "timeline.json", "report.json"}
    assert str(source) not in json.dumps(result)
    if gaps:
        with pytest.raises(ValueError):
            probe(output / "preview.mp4")  # Existing strict worker admission was not relaxed.
        gap = result["quality"]["unknown_intervals"][0]
        assert not timing_window_supported(result["quality"], gap["start_us"], gap["end_us"])
    else:
        assert probe(output / "preview.mp4")["frame_count"] == 30


def test_timing_unknown_intervals_and_boundary_windows():
    limits = policy()
    quality = timing_quality([0, 16667, 50000, 66667], limits)
    assert quality["gaps_over_limit"] == 1
    assert not quality["timing_matches_declared_profile"]
    assert timing_window_supported(quality, 0, 16667)
    assert not timing_window_supported(quality, 16666, 16668)
    assert not timing_window_supported(quality, -1, 100)
    assert not timing_window_supported(quality, 50000, 70000)
    assert not timing_window_supported(quality, 2, 2)
    jitter = timing_quality([0, 18000, 34667], limits)
    assert jitter["unknown_intervals"][0]["reason"] == "IRREGULAR_PERIOD"


@pytest.mark.parametrize("times", [[0], [0, 0], [20, 10], [-1, 16667], [0, 600000001]])
def test_invalid_timeline_is_rejected(times):
    with pytest.raises(ValueError):
        timing_quality(times, policy())


@pytest.mark.parametrize("value", ["nan", "Infinity", "-Infinity", "not-a-time"])
def test_non_finite_timestamps_rejected(value):
    with pytest.raises(ValueError):
        timestamp(value)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("count", "FRAME_COUNT"),
        ("pts", "FRAME_TIMESTAMPS"),
        ("audio_count", "AUDIO_PACKET_COUNT"),
        ("audio_data", "AUDIO_DATA"),
        ("audio_time", "AUDIO_TIMESTAMPS"),
        ("quality", "QUALITY_INTERVALS"),
        ("codec", "OUTPUT_CODEC"),
        ("color", "COLOR_DECLARATIONS"),
    ],
)
def test_preservation_checks_detect_changed_evidence(mutation, message):
    original = {
        "times_us": [0, 16667],
        "audio": {},
        "audio_packets": [{"pts_us": 0, "dts_us": 0, "duration_us": 21333, "data_hash": "a"}],
        "quality": {"unknown_intervals": []},
        "video": {"codec_name": "h264", "color_range": "tv"},
    }
    derived = copy.deepcopy(original)
    if mutation == "count":
        derived["times_us"].append(33333)
    elif mutation == "pts":
        derived["times_us"][1] += 100
    elif mutation == "audio_count":
        derived["audio_packets"] = []
    elif mutation == "audio_data":
        derived["audio_packets"][0]["data_hash"] = "b"
    elif mutation == "audio_time":
        derived["audio_packets"][0]["pts_us"] += 100
    elif mutation == "quality":
        derived["quality"]["unknown_intervals"] = [{"start_us": 0}]
    elif mutation == "codec":
        derived["video"]["codec_name"] = "hevc"
    elif mutation == "color":
        derived["video"]["color_range"] = "pc"
    with pytest.raises(ValueError, match=message):
        verify_preservation(original, derived, policy())


def test_no_overwrite_or_oversize_or_external_path_access(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"not-media")
    output = tmp_path / "existing"
    output.mkdir()
    (output / "keep").write_text("existing result")
    with pytest.raises(FileExistsError):
        normalize(source, output)
    assert (output / "keep").read_text() == "existing result"
    limits = policy()
    limits["max_bytes"] = 1
    monkeypatch.setattr(normalization, "policy", lambda: limits)
    with pytest.raises(ValueError, match="FILE_TOO_LARGE"):
        normalize(source, tmp_path / "new")
    assert not (tmp_path / "new").exists()


@pytest.mark.parametrize("linked_parent", [False, True])
def test_source_or_ancestor_symlink_rejected(tmp_path, linked_parent):
    real = tmp_path / "real"
    real.mkdir()
    source = real / "source.mp4"
    source.write_bytes(b"private")
    link = tmp_path / "link"
    try:
        link.symlink_to(real if linked_parent else source, target_is_directory=linked_parent)
    except OSError:
        pytest.skip("OS does not permit creating a symlink")
    with pytest.raises(ValueError, match="LINKED_PATH"):
        normalize(link / "source.mp4" if linked_parent else link, tmp_path / "out")


def test_failures_remove_owned_output_only_and_do_not_touch_original(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"trusted-selected-invalid")
    output = tmp_path / "bundle"

    def fail(*args):
        (output / "preview.mp4").write_bytes(b"incomplete")
        raise ValueError("DECODER_TIMEOUT")

    monkeypatch.setattr(normalization, "inspect", fail)
    with pytest.raises(ValueError, match="DECODER_TIMEOUT"):
        normalize(source, output)
    assert not output.exists()
    assert source.read_bytes() == b"trusted-selected-invalid"


def test_cli_failure_redacts_private_paths(tmp_path):
    source = tmp_path / "SECRET_PLAYER.mp4"
    source.write_bytes(b"invalid")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.normalize_recording",
            str(source),
            "--output-dir",
            str(tmp_path / "PRIVATE_OUTPUT"),
        ],
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 2
    assert b"SECRET_PLAYER" not in result.stderr + result.stdout
    assert b"PRIVATE_OUTPUT" not in result.stderr + result.stdout
    assert b"DECODER_REJECTED_INPUT" in result.stderr


def test_process_file_limit_catches_fast_exit(tmp_path):
    output = tmp_path / "too-large"
    with pytest.raises(ValueError, match="FILE_LIMIT"):
        run_bounded(
            [
                sys.executable,
                "-c",
                "import sys; open(sys.argv[1],'wb').write(b'x'*2000)",
                str(output),
            ],
            file_limits={output: 100},
        )


def test_decoder_error_output_cannot_succeed_with_exit_zero():
    with pytest.raises(ValueError, match="DECODER_REPORTED_ERRORS"):
        run_bounded(
            [sys.executable, "-c", "import sys; sys.stderr.write('decode error')"],
            reject_stderr=True,
        )


@pytest.mark.media
@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg absent")
def test_changed_selected_source_is_rejected_and_derivative_removed(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    generate(source, audio=False)
    real_inspect = normalization.inspect

    def inspect_and_change(path, limits):
        result = real_inspect(path, limits)
        if path.name == "preview.mp4":
            with source.open("ab") as stream:
                stream.write(b"source-changed")
        return result

    monkeypatch.setattr(normalization, "inspect", inspect_and_change)
    with pytest.raises(ValueError, match="SOURCE_CHANGED"):
        normalize(source, tmp_path / "bundle")
    assert not (tmp_path / "bundle").exists()


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"codec_name": "vp9"}, "UNSUPPORTED_CODEC"),
        ({"width": 1280}, "UNSUPPORTED_RESOLUTION"),
        ({"pix_fmt": "yuv420p10le"}, "UNSUPPORTED_PIXEL_FORMAT"),
        ({"color_transfer": "smpte2084"}, "HDR_UNSUPPORTED"),
        ({"color_space": "bt2020nc"}, "UNSUPPORTED_COLOR_SPACE"),
        ({"field_order": "tt"}, "INTERLACING_UNSUPPORTED"),
        ({"side_data_list": [{"rotation": 90}]}, "ROTATION_UNSUPPORTED"),
        ({"r_frame_rate": "120/1"}, "UNSUPPORTED_NOMINAL_RATE"),
    ],
)
def test_unsupported_profile_is_rejected_before_frame_scan(tmp_path, monkeypatch, change, message):
    video = {
        "codec_type": "video",
        "codec_name": "hevc",
        "width": 1920,
        "height": 1080,
        "pix_fmt": "yuv420p",
        "r_frame_rate": "60/1",
    }
    video.update(change)
    calls = []

    def fake_probe(path, args, limits):
        calls.append(args)
        return {"streams": [video], "format": {"duration": "1", "format_name": "mov,mp4"}}

    monkeypatch.setattr(normalization, "probe_json", fake_probe)
    with pytest.raises(ValueError, match=message):
        normalization.inspect(tmp_path / "source.mp4", policy())
    assert len(calls) == 1


@pytest.mark.parametrize("message", ["DECODER_TIMEOUT", "SECRET_PLAYER_PRIVATE_PATH"])
def test_cli_only_allowlists_error_codes(tmp_path, monkeypatch, capsys, message):
    from tools import normalize_recording

    def fail(*args, **kwargs):
        raise ValueError(message)

    monkeypatch.setattr(normalize_recording, "normalize", fail)
    monkeypatch.setattr(sys, "argv", ["normalize_recording", "source.mp4", "--output-dir", "new"])
    with pytest.raises(SystemExit) as exc:
        normalize_recording.main()
    assert exc.value.code == 2
    output = capsys.readouterr().err
    assert "SECRET_PLAYER" not in output
    assert (
        "DECODER_TIMEOUT" if message == "DECODER_TIMEOUT" else "INVALID_INPUT_OR_OUTPUT"
    ) in output
