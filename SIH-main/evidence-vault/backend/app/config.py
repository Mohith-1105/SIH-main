"""EvidenceVault Configuration"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from cryptography.fernet import Fernet

_DEV_SECRET = "dev-secret-key-change-in-production"


def _validate_secrets(demo_mode: bool, secret_key: str, encryption_key: str) -> None:
    if demo_mode:
        return
    weak = not secret_key or len(secret_key) < 32 or "dev" in secret_key.lower()
    if weak:
        raise RuntimeError(
            "SECRET_KEY must be a strong random value (32+ chars, no 'dev') when DEMO_MODE is off. "
            "Set a secure value in .env"
        )
    if not encryption_key:
        raise RuntimeError(
            "ENCRYPTION_KEY must be set in .env when DEMO_MODE is off"
        )


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./evidencevault.db"
    SECRET_KEY: str = _DEV_SECRET
    ENCRYPTION_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    MAX_UPLOAD_SIZE_MB: int = 25
    DEMO_MODE: bool = False
    RATE_LIMIT_MAX_ATTEMPTS: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 300
    LOCKOUT_SECONDS: int = 600
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Paths
    BASE_DIR: str = str(Path(__file__).resolve().parent.parent)
    STORAGE_DIR: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        _validate_secrets(self.DEMO_MODE, self.SECRET_KEY, self.ENCRYPTION_KEY)
        if not self.STORAGE_DIR:
            self.STORAGE_DIR = os.path.join(self.BASE_DIR, "storage", "evidence")
        os.makedirs(self.STORAGE_DIR, exist_ok=True)

        # Generate encryption key if not set (persisted by encryption module). Demo-only.
        if not self.ENCRYPTION_KEY:
            self.ENCRYPTION_KEY = Fernet.generate_key().decode()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()