from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import AuditLog, User


def write_audit(
    db: Session,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: int,
    before_status: str = "",
    after_status: str = "",
    detail: str = "",
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            actor_role=actor.role if actor else "system",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_status=before_status,
            after_status=after_status,
            detail=detail,
        )
    )
