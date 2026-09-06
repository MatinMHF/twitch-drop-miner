"""Application settings and environment configuration."""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General App Config
    APP_NAME: str = "Twitch Drop Miner"
    APP_VERSION: str = "3.2.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    BASE_URL: str = "https://localhost:8080"
    TIMEZONE: str = "UTC"

    # Data & Storage
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data"))
    DATABASE_URL: Optional[str] = None

    # Security & Encryption (Must be configured or auto-generated for security)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    CSRF_SECRET: str = os.getenv("CSRF_SECRET", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    REQUIRE_HTTPS: bool = os.getenv("REQUIRE_HTTPS", "false").lower() in ("true", "1", "yes")

    # Rate Limiting
    RATE_LIMIT_LOGIN: str = "10/minute"
    RATE_LIMIT_DEVICE_FLOW: str = "20/minute"
    RATE_LIMIT_API: str = "120/minute"

    # Mining Engine Defaults
    POLL_INTERVAL_MINUTES: int = 30
    WATCH_HEARTBEAT_SECONDS: int = 60
    AUTO_CLAIM_DROPS: bool = True
    AUTO_FAILOVER_STREAMERS: bool = True
    MAX_MINING_RETRIES: int = 5

    # CORS Allowed Origins
    CORS_ORIGINS: List[str] = ["*"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure data directory exists
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Setup default SQLite database in DATA_DIR if not explicitly set
        if not self.DATABASE_URL:
            db_path = self.DATA_DIR / "twitch_miner.db"
            self.DATABASE_URL = f"sqlite+aiosqlite:///{db_path.resolve().as_posix()}"

        # If keys are missing, load or persist persistent keys inside DATA_DIR
        secret_file = self.DATA_DIR / ".master_secrets"
        if not self.SECRET_KEY or not self.ENCRYPTION_KEY or not self.CSRF_SECRET:
            if secret_file.exists():
                try:
                    lines = secret_file.read_text(encoding="utf-8").splitlines()
                    for line in lines:
                        if "=" in line:
                            k, v = line.strip().split("=", 1)
                            if k == "SECRET_KEY" and not self.SECRET_KEY:
                                self.SECRET_KEY = v
                            elif k == "ENCRYPTION_KEY" and not self.ENCRYPTION_KEY:
                                self.ENCRYPTION_KEY = v
                            elif k == "CSRF_SECRET" and not self.CSRF_SECRET:
                                self.CSRF_SECRET = v
                except Exception:
                    pass

            # Generate any remaining missing keys and persist
            updated = False
            if not self.SECRET_KEY:
                self.SECRET_KEY = secrets.token_hex(32)
                updated = True
            if not self.ENCRYPTION_KEY:
                self.ENCRYPTION_KEY = secrets.token_hex(32)
                updated = True
            if not self.CSRF_SECRET:
                self.CSRF_SECRET = secrets.token_hex(32)
                updated = True

            if updated:
                secret_file.write_text(
                    f"SECRET_KEY={self.SECRET_KEY}\n"
                    f"ENCRYPTION_KEY={self.ENCRYPTION_KEY}\n"
                    f"CSRF_SECRET={self.CSRF_SECRET}\n",
                    encoding="utf-8",
                )


settings = Settings()
