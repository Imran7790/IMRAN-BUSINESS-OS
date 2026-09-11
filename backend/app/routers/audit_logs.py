from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import AuditLog
from app.core.auth import require_manager


router = APIRouter(
    prefix="/api/v1/audit-logs",
    tags=["Audit Logs"],
)


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    user_id: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    details: str | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    limit: int
    offset: int
    total: int


@router.get(
    "",
    response_model=AuditLogListResponse,
)
def list_audit_logs(
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(require_manager),
    db: Session = Depends(get_db),
):
    query = (
        db.query(AuditLog)
        .filter(
            AuditLog.business_id == current_user.business_id
        )
    )

    if action:
        query = query.filter(
            AuditLog.action == action
        )

    if entity_type:
        query = query.filter(
            AuditLog.entity_type == entity_type
        )

    total = query.count()

    logs = (
        query
        .order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return AuditLogListResponse(
        items=logs,
        limit=limit,
        offset=offset,
        total=total,
    )
