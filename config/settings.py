"""
Paul Frendach — one house, three rooms.

Settings are env-driven so dev and production differ only by environment,
never by editing this file.
"""

from pathlib import Path
import os
import sys

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# ---------------------------------------------------------------- core

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-only-insecure-key-change-before-deploy",
)
DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "paulfrendach.com")
SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:8000")

# ---------------------------------------------------------------- The LAB
#
# The Train room is a wrapper over The LAB's public API: the coach's services,
# prices and intake form live in their LAB account, and this site renders them.
# Both values come from the coach, not from us — LAB_API_KEY is issued by them
# in Settings -> API keys and can be revoked without anyone here being told.
#
# Unset is a supported state. Every LAB call is wrapped, and the Train room
# degrades to an honest "ask directly" rather than a stack trace, so a dev box
# with no key still renders the site.
LAB_API_BASE = os.environ.get("LAB_API_BASE", "")
LAB_API_KEY = os.environ.get("LAB_API_KEY", "")
LAB_TIMEOUT = float(os.environ.get("LAB_TIMEOUT", "10"))
# Trap: Cloudflare answers a default library User-Agent with an HTML 403 rather
# than our JSON, so the client names itself on every request.
LAB_USER_AGENT = os.environ.get("LAB_USER_AGENT", f"{SITE_DOMAIN}/1.0 (+LAB API client)")
# Services and the intake form are read on nearly every Train page view and
# change when the coach edits them, which is rarely.
LAB_CACHE_SECONDS = int(os.environ.get("LAB_CACHE_SECONDS", "120"))
# A `lab_live_` key writes into the coach's REAL account: a real lead, a real
# chat thread, a real email to them. Reads are always allowed; writes with a
# live key have to be armed deliberately, so a dev box pointed at production
# cannot quietly fill their inbox with "asdf". Test keys are unaffected — that
# is what they are for.
LAB_ALLOW_LIVE_WRITES = env_bool("LAB_ALLOW_LIVE_WRITES", False)

# The test suite must never reach The LAB, and above all must never reach it
# with a live key: `apps/house` renders every room to check the chrome, which
# means an ordinary `manage.py test` would otherwise fire real requests at a
# real coach's account using whatever is in .env. Blanking the config here
# makes every unmocked call fail instantly and locally; tests that exercise the
# client override these settings explicitly.
if "test" in sys.argv:
    LAB_API_BASE = ""
    LAB_API_KEY = ""
    LAB_ALLOW_LIVE_WRITES = False

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",
    "apps.house",
    "apps.lab",
    "apps.train",
    "apps.create",
    "apps.build",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.house.context_processors.house",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------- data

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------- i18n

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TIME_ZONE", "America/New_York")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------- static / media

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Django 5.1+ storages block. WhiteNoise compresses and hashes in production;
# dev keeps plain static so a missing hash never 500s a page mid-edit.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

# ---------------------------------------------------------------- mail

if env_bool("EMAIL_LIVE", False):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", f"hello@{SITE_DOMAIN}")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", DEFAULT_FROM_EMAIL)

# ---------------------------------------------------------------- security

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
