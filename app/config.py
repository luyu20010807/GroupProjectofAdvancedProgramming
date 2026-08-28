from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "星河商城")
    secret_key: str = os.getenv("SECRET_KEY", "change-this-secret-in-production")
    database_url: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'ecommerce.db').as_posix()}"
    )
    merchant_review_hours: int = int(os.getenv("MERCHANT_REVIEW_HOURS", "48"))
    return_deadline_days: int = int(os.getenv("RETURN_DEADLINE_DAYS", "7"))
    receipt_confirm_hours: int = int(os.getenv("RECEIPT_CONFIRM_HOURS", "72"))
    debug: bool = os.getenv("DEBUG", "1") == "1"


settings = Settings()
