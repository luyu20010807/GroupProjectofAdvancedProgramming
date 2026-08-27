from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, init_db  # noqa: E402
from app.services.refund_service import process_timeouts  # noqa: E402


if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        print(process_timeouts(db))
    finally:
        db.close()
