from datetime import datetime, timezone
import uuid

from sqlalchemy.orm import Session

from app.models.core import Notification


def create_notification(
    db: Session,
    business_id: str,
    notification_type: str,
    title: str,
    message: str,
    severity: str = "INFO",
    user_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> Notification:
    if not business_id:
        raise ValueError("business_id is required")
    if not notification_type:
        raise ValueError("notification_type is required")
    if not title:
        raise ValueError("title is required")
    if not message:
        raise ValueError("message is required")

    notification = Notification(
        id=str(uuid.uuid4()),
        business_id=business_id,
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        severity=severity.upper(),
        entity_type=entity_type,
        entity_id=entity_id,
        is_read=False,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    db.add(notification)
    db.flush()
    return notification


def mark_notification_read(
    db: Session,
    notification_id: str,
    business_id: str,
) -> Notification | None:
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.business_id == business_id,
        )
        .first()
    )

    if notification is None:
        return None

    notification.is_read = True
    db.flush()
    return notification
