"""
Test settings — used by pytest (locally and in CI).

Locally: uses SQLite in-memory so no Postgres install is needed.
CI: DATABASE_URL env var overrides to the Postgres service container.

All required env vars that have no default in settings.py are stubbed here
so that importing the main settings module never raises KeyError.
"""

import os

# Stub required env vars before importing main settings (settings.py uses
# os.environ['KEY'] — no .get() — for these, so they must exist).
os.environ.setdefault("SECRET_KEY", "django-insecure-test-key-not-for-production")
os.environ.setdefault("EMAIL_HOST_PASSWORD", "test-placeholder")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_placeholder")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")
os.environ.setdefault("STRIPE_PRICE_PREMIUM_MONTHLY", "price_placeholder")

from workpal.settings import *  # noqa: E402, F401, F403

# ── Database ──────────────────────────────────────────────────────────────────
# Use the CI Postgres if DATABASE_URL is set, otherwise fall back to SQLite.
if not os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

# ── Speed ─────────────────────────────────────────────────────────────────────
# Bcrypt is slow — use the fast MD5 hasher in tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# ── Email ─────────────────────────────────────────────────────────────────────
# Never send real email from tests.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ── Storage ───────────────────────────────────────────────────────────────────
# Use local filesystem storage so tests don't need AWS credentials.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
