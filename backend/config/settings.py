"""Local-only defaults. Production requires explicit secrets, PostgreSQL and release gates."""

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-only-do-not-deploy")
if not DEBUG and SECRET_KEY == "local-only-do-not-deploy":
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY for deployment")
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver").split(",")
ROOT_URLCONF = "backend.config.urls"
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "rest_framework",
    "backend.core",
]
MIDDLEWARE = [
    "backend.core.deployment.RestoreQuarantineMiddleware",
    "backend.core.telemetry.OperationsMetricsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "backend.core.security.PrivateResponseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "backend.core.accounts.AccountSessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
database_url = os.getenv("DATABASE_URL")
if database_url:
    database = urlparse(database_url)
    if database.scheme not in {"postgresql", "postgres"}:
        raise ImproperlyConfigured("PostgreSQL URL required")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": database.path.lstrip("/"),
            "USER": unquote(database.username or ""),
            "PASSWORD": unquote(database.password or ""),
            "HOST": database.hostname,
            "PORT": database.port or 5432,
            "CONN_MAX_AGE": 0,
        }
    }
elif os.getenv("ALLOW_SQLITE") == "1":
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "local.sqlite3"}
    }
else:
    raise ImproperlyConfigured("Set DATABASE_URL; ALLOW_SQLITE=1 is an explicit test-only fallback")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
STATIC_URL = "/static/"
PRIVATE_DATA_ROOT = Path(os.getenv("PRIVATE_DATA_ROOT", str(BASE_DIR / "private_data"))).resolve()
LOCAL_OPERATOR_UPLOADS = DEBUG and os.getenv("LOCAL_OPERATOR_UPLOADS", "0") == "1"
LOCAL_MATCH_IMPORTS = DEBUG and os.getenv("LOCAL_MATCH_IMPORTS", "0") == "1"
LOCAL_ACCOUNT_SIGNUP = DEBUG and os.getenv("LOCAL_ACCOUNT_SIGNUP", "0") == "1"
ACCOUNT_PUBLIC_ORIGIN = "http://127.0.0.1:3000"
DATA_SUPPRESSION_KEY = os.getenv("DATA_SUPPRESSION_KEY", SECRET_KEY)
SESSION_COOKIE_AGE = 7 * 24 * 60 * 60
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
EXTERNAL_UPLOADS_ENABLED = False  # Hosted ingestion gate cannot be bypassed with a flag.
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
FILE_UPLOAD_HANDLERS = [
    "backend.core.uploads.BoundedUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = (
    ["http://localhost:3000", "http://127.0.0.1:3000"]
    if DEBUG
    else [origin for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if origin]
)
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if os.getenv("TRUST_MANAGED_PROXY", "0") == "1" else None
)
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SAMESITE = "Lax"
STATIC_ROOT = BASE_DIR / "staticfiles"
REST_FRAMEWORK = {
    "DEFAULT_PARSER_CLASSES": [
        "backend.core.parsers.BoundedJSONParser",
        "backend.core.parsers.BoundedFormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": ["backend.core.security.AccountThrottle"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 50,
}

# Local deployment budgets. Hosted ingress also needs body/time/connection limits.
LOGIN_RATE = 10
API_READ_RATE = 300
API_WRITE_RATE = 60
OWNER_STORAGE_BYTES = 2 * 1024**3
GLOBAL_STORAGE_BYTES = 16 * 1024**3
GLOBAL_UPLOAD_SLOTS = 4
OWNER_PENDING_RUNS = 4
GLOBAL_PENDING_RUNS = 32
OWNER_DAILY_RUNS = 20
GLOBAL_ACTIVE_RUNS = 2
RUN_LEASE_SECONDS = 30
RUN_DEADLINE_SECONDS = 420
RUN_MAX_ATTEMPTS = 3
OWNER_MEDIA_SECONDS_PER_DAY = 7200
GLOBAL_MEDIA_SECONDS_PER_DAY = 86400
OWNER_PROCESSING_SECONDS_PER_DAY = 7200
GLOBAL_PROCESSING_SECONDS_PER_DAY = 86400
ASSET_RUNS_PER_DAY = 3  # Initial analysis plus two reanalyses; request retries are idempotent.
OPTIONAL_PROCESSING_PAUSED = os.getenv("OPTIONAL_PROCESSING_PAUSED", "0") == "1"
OPS_QUEUE_TARGET_SECONDS = 120
OPS_PROCESSING_TARGET_SECONDS = 390
OPS_COMPLETION_TARGET = 0.95
OPS_AVAILABILITY_TARGET = 0.99
OPS_MIN_SAMPLES = 20
OPS_RETENTION_DAYS = 30
OPS_MAX_ATTEMPT_SAMPLES = 20000
RESTORE_QUARANTINE = os.getenv("RESTORE_QUARANTINE", "0") == "1"
CONTROL_JOURNAL_ROOT = Path(
    os.getenv("CONTROL_JOURNAL_ROOT", str(PRIVATE_DATA_ROOT / "control-journal"))
)
CONTROL_JOURNAL_KEY = os.getenv("CONTROL_JOURNAL_KEY", SECRET_KEY)
DEPLOYMENT_NAMESPACE = os.getenv("DEPLOYMENT_NAMESPACE", "local")
CLOUD_MEDIA_RUNTIME_QUALIFIED = False  # Qualification requires a reviewed code/profile change.
GCS_PRIVATE_BUCKET = os.getenv("GCS_PRIVATE_BUCKET", "")
GOOGLE_TASK_QUEUE = os.getenv("GOOGLE_TASK_QUEUE", "")
GOOGLE_ANALYSIS_JOB = os.getenv("GOOGLE_ANALYSIS_JOB", "")
GOOGLE_TASK_TARGET = os.getenv("GOOGLE_TASK_TARGET", "")
GOOGLE_TASK_SERVICE_ACCOUNT = os.getenv("GOOGLE_TASK_SERVICE_ACCOUNT", "")
PARSER_BACKEND = os.getenv("PARSER_BACKEND", "docker")
PARSER_IMAGE = os.getenv("PARSER_IMAGE", "")  # Immutable sha256 image ID required.
if not DEBUG and PARSER_BACKEND != "docker":
    raise ImproperlyConfigured("Only the isolated parser is allowed outside local development")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"security": {"format": "%(message)s"}},
    "filters": {"redacted_request": {"()": "backend.core.logging.RedactedRequestLogFilter"}},
    "handlers": {
        "security": {"class": "logging.StreamHandler", "formatter": "security"},
        "redacted_request": {
            "class": "logging.StreamHandler",
            "formatter": "security",
            "filters": ["redacted_request"],
        },
    },
    "loggers": {
        "dojopulse.security": {"handlers": ["security"], "level": "INFO"},
        "django.request": {
            "handlers": ["redacted_request"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["redacted_request"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.server": {"handlers": ["redacted_request"], "level": "WARNING", "propagate": False},
    },
}
