import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.environ.get(
        "EDUMATCH_SECRET_KEY",
        "change-this-development-key-before-deployment"
    )

    DEBUG = True

    DATABASE_PATH = PROJECT_ROOT / "database" / "edumatch.db"

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    SESSION_PERMANENT = False