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
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
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
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
CSRF_TRUSTED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"] if DEBUG else []
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 50,
}
