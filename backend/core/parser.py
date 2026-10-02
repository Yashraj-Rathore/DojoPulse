"""No credentials, database, host output mount or network reach the media parser."""

import json
import math
import re
import subprocess
import uuid
from pathlib import Path

from django.conf import settings

from analysis.process import run_bounded


def sandbox_command(image, name, source, metadata):
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise ValueError("PARSER_IMAGE_NOT_PINNED")
    paths = [Path(source).resolve(strict=True), Path(metadata).resolve(strict=True)]
    if any(not p.is_file() or "," in str(p) for p in paths):
        raise ValueError("INVALID_PARSER_INPUT")
    return [
        "docker",
        "run",
        "--name",
        name,
        "--label",
        "dojopulse.role=parser",
        "--rm",
        "--pull",
        "never",
        "--network",
        "none",
        "--log-driver",
        "none",
        "--read-only",
        "--user",
        "10001:10001",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges=true",
        "--pids-limit",
        "64",
        "--cpus",
        "1",
        "--memory",
        "1g",
        "--memory-swap",
        "1g",
        "--ulimit",
        "nofile=128:128",
        "--ulimit",
        "core=0:0",
        "--tmpfs",
        "/work:rw,noexec,nosuid,nodev,size=512m,mode=1777",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777",
        "--mount",
        f"type=bind,source={paths[0]},target=/input/source.mp4,readonly",
        "--mount",
        f"type=bind,source={paths[1]},target=/input/metadata.json,readonly",
        image,
    ]


def validate_report(raw):
    if not isinstance(raw, dict) or raw.get("status") not in {"FAILED", "REVIEW_REQUIRED"}:
        raise ValueError("INVALID_PARSER_REPORT")
    if raw.get("opportunities") != [] or raw.get("automatic_gameplay_validated") is not False:
        raise ValueError("INVALID_PARSER_REPORT")
    # Only explicitly shaped data crosses into the credentialed coordinator.
    result = {
        "status": raw["status"],
        "opportunities": [],
        "automatic_gameplay_validated": False,
        "schema_version": "capture-report/1",
        "artifacts_retained": False,
        "issues": [],
    }
    issues = raw.get("issues", [])
    if not isinstance(issues, list) or len(issues) > 20:
        raise ValueError("INVALID_PARSER_REPORT")
    result["issues"] = [
        code
        if isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", code)
        else "MEDIA_VALIDATION_FAILED"
        for code in issues
    ]
    if raw["status"] == "REVIEW_REQUIRED":
        source = raw.get("source", {})
        sha = source.get("source_sha256") if isinstance(source, dict) else None
        if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
            raise ValueError("INVALID_PARSER_REPORT")
        # Keep only media facts needed by callers; discard arbitrary paths and objects.
        result["source"] = {"source_sha256": sha}
        duration = source.get("duration_seconds")
        if (
            type(duration) not in {int, float}
            or not math.isfinite(duration)
            or not 0 < duration <= 600
        ):
            raise ValueError("INVALID_PARSER_REPORT")
        result["source"]["duration_seconds"] = duration
        for field in ("bytes", "duration_us", "width", "height", "frame_count"):
            value = source.get(field)
            if value is not None:
                if type(value) is not int or not 0 < value <= 1_000_000_000:
                    raise ValueError("INVALID_PARSER_REPORT")
                result["source"][field] = value
    cost = raw.get("cost", {})
    if isinstance(cost, dict):
        result["cost"] = {
            key: value
            for key, value in cost.items()
            if key
            in {
                "processing_seconds",
                "decoder_cpu_seconds",
                "decoder_peak_rss_bytes",
                "derived_bytes",
            }
            and type(value) in {float, int}
            and math.isfinite(value)
            and 0 <= value <= 10**12
        }
    return result


def analyze_isolated(source, output, metadata):
    if settings.PARSER_BACKEND == "local":
        if not settings.DEBUG or not settings.LOCAL_OPERATOR_UPLOADS:
            raise ValueError("LOCAL_PARSER_DISABLED")
        from tools.analyze_capture import analyze

        return validate_report(analyze(source, output, metadata))
    if settings.PARSER_BACKEND != "docker":
        raise ValueError("UNKNOWN_PARSER_BACKEND")
    name = "dojopulse-parser-" + uuid.uuid4().hex
    command = sandbox_command(settings.PARSER_IMAGE, name, source, metadata)
    try:
        result = run_bounded(command, timeout=330, max_output=1_048_576)
        try:
            return validate_report(json.loads(result.stdout))
        except RecursionError as error:
            raise ValueError("INVALID_PARSER_REPORT") from error
    finally:
        # Docker processes live outside the CLI process tree. Remove only our unique container.
        try:
            cleanup = subprocess.run(
                ["docker", "rm", "--force", name],
                timeout=15,
                capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
            if cleanup.returncode and b"No such container" not in cleanup.stderr:
                raise ValueError("PARSER_CLEANUP_UNCONFIRMED")
        except (OSError, subprocess.TimeoutExpired):
            from backend.core.security import audit

            audit("parser_cleanup", "RUNTIME_UNAVAILABLE")
            raise ValueError("PARSER_CLEANUP_UNCONFIRMED") from None
