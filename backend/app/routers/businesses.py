from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Business
from app.core.auth import get_current_user, require_owner
from app.services.audit import create_audit_log


router = APIRouter(
    prefix="/api/v1/businesses",
    tags=["Businesses"]
)


@router.get("/me")
def my_business(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    business = (
        db.query(Business)
        .filter(Business.id == current_user.business_id)
        .first()
    )

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )

    return business


@router.patch("/me")
def update_my_business(
    data: dict,
    current_user=Depends(require_owner),
    db: Session = Depends(get_db)
):
    business = (
        db.query(Business)
        .filter(Business.id == current_user.business_id)
        .first()
    )

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )

    allowed = {
        "name",
        "category",
        "country_code",
        "currency_code",
        "timezone",
        "language_code"
    }

    changed_fields = []

    for key, value in data.items():
        if key in allowed:
            old_value = getattr(business, key)

            if old_value != value:
                setattr(business, key, value)
                changed_fields.append(key)

    if changed_fields:
        create_audit_log(
            db=db,
            business_id=current_user.business_id,
            user_id=current_user.id,
            action="UPDATE",
            entity_type="BUSINESS",
            entity_id=business.id,
            details=f"Updated business fields: {', '.join(changed_fields)}"
        )

    db.commit()
    db.refresh(business)

    return business
