from typing import Optional

from sqlalchemy.orm import Session

from app.models.core import AuditLog


def create_audit_log(
    db: Session,
    business_id: str,
    user_id: Optional[str],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[str] = None,
) -> AuditLog:
    """
    Create an audit record for an authenticated business action.

    business_id and user_id must come from the server-side
    authenticated context, not from untrusted client input.
    """

    audit = AuditLog(
        business_id=business_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )

    db.add(audit)
    db.flush()

    return audit
