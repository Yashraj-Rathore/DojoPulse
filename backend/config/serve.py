"""Linux container entry point: bounded HTTP only, no parser/background polling."""

import os

port = int(os.getenv("PORT", "8080"))
if not 1 <= port <= 65535:
    raise ValueError("INVALID_PORT")
os.execvp(
    "gunicorn",
    [
        "gunicorn",
        "backend.config.wsgi:application",
        "--bind",
        f"0.0.0.0:{port}",
        "--workers",
        "2",
        "--threads",
        "2",
        "--timeout",
        "60",
        "--graceful-timeout",
        "15",
        "--limit-request-line",
        "4096",
        "--limit-request-fields",
        "50",
        "--limit-request-field_size",
        "8190",
    ],
)
