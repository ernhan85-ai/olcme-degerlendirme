import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog


def audit(db: Session, *, org_id: uuid.UUID | None, actor_id: uuid.UUID | None, action: str,
          entity_type: str, entity_id: uuid.UUID | str | None = None, **details) -> None:
    db.add(AuditLog(organization_id=org_id, actor_id=actor_id, action=action, entity_type=entity_type,
                    entity_id=str(entity_id) if entity_id else None, details=details))
