from __future__ import annotations

import sys
from pathlib import Path

import uvicorn
from sqlalchemy import select

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, init_db  # noqa: E402
from app.models import User  # noqa: E402
from scripts.seed_demo import seed  # noqa: E402


def ensure_demo_data() -> None:
    init_db()
    db = SessionLocal()
    try:
        has_user = db.scalar(select(User.id).limit(1)) is not None
    finally:
        db.close()
    if not has_user:
        seed(reset=False)


if __name__ == "__main__":
    ensure_demo_data()
    print("\n星河商城已启动：http://127.0.0.1:8000")
    print("演示账号 user1 / merchant1 / admin，密码均为 123456\n")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
