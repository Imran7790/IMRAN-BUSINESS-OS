from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database import get_db
from app.models.core import Notification, User
from app.services.notifications import mark_notification_read

router = APIRouter(prefix='/api/v1/notifications', tags=['notifications'])


def notification_response(notification: Notification):
    return {
        'id': notification.id,
        'business_id': notification.business_id,
        'user_id': notification.user_id,
        'notification_type': notification.notification_type,
        'title': notification.title,
        'message': notification.message,
        'severity': notification.severity,
        'entity_type': notification.entity_type,
        'entity_id': notification.entity_id,
        'is_read': notification.is_read,
        'created_at': notification.created_at,
    }


@router.get('')
def list_notifications(
    unread: Optional[bool] = Query(default=None),
    notification_type: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Notification).filter(
        Notification.business_id == current_user.business_id
    )

    if unread is not None:
        query = query.filter(Notification.is_read == (not unread))

    if notification_type:
        query = query.filter(
            Notification.notification_type == notification_type.upper()
        )

    if severity:
        query = query.filter(
            Notification.severity == severity.upper()
        )

    notifications = (
        query
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .all()
    )

    return [notification_response(item) for item in notifications]


@router.get('/unread-count')
def unread_notification_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = (
        db.query(Notification)
        .filter(
            Notification.business_id == current_user.business_id,
            Notification.is_read == False,
        )
        .count()
    )

    return {'count': count}


@router.patch('/read-all')
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = (
        db.query(Notification)
        .filter(
            Notification.business_id == current_user.business_id,
            Notification.is_read == False,
        )
        .update(
            {Notification.is_read: True},
            synchronize_session=False,
        )
    )

    db.commit()
    return {'updated': updated}


@router.patch('/{notification_id}/read')
def mark_one_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = mark_notification_read(
        db=db,
        notification_id=notification_id,
        business_id=current_user.business_id,
    )

    if notification is None:
        raise HTTPException(status_code=404, detail='Notification not found')

    db.commit()
    db.refresh(notification)
    return notification_response(notification)
