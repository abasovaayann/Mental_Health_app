"""Shared test setup.

The app's Settings model (app/config.py) requires DATABASE_URL and SECRET_KEY
with no defaults, and importing any app module triggers Settings(). We set
deterministic env vars here — before app imports happen — so the suite never
depends on a real .env or a running Postgres. A sqlite URL keeps engine
creation cheap (no connection is opened at import time).
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-characters-long")
os.environ.setdefault("ENVIRONMENT", "test")
