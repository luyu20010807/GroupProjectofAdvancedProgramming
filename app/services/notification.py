from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Notification


def notify(db: Session, user_id: int, title: str, content: str) -> None:
    db.add(Notification(user_id=user_id, title=title, content=content))
