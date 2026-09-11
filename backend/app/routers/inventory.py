from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Product
from app.models.core import StockMovement, User
from app.services.stock_alerts import get_stock_alert
from app.core.auth import get_current_user
from app.services.audit import create_audit_log
from app.services.inventory_service import apply_stock_movement


router = APIRouter(
    prefix="/api/v1/inventory",
    tags=["inventory"],
)


VALID_MOVEMENT_TYPES = {
    "PURCHASE",
    "SALE",
    "ADJUSTMENT_IN",
    "ADJUSTMENT_OUT",
    "RETURN_IN",
    "RETURN_OUT",
}


INBOUND_TYPES = {
    "PURCHASE",
    "ADJUSTMENT_IN",
    "RETURN_IN",
}


OUTBOUND_TYPES = {
    "SALE",
    "ADJUSTMENT_OUT",
    "RETURN_OUT",
}


class StockMovementCreate(BaseModel):
    product_id: str
    movement_type: str
    quantity: float = Field(gt=0)
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None


class StockMovementResponse(BaseModel):
    id: str
    business_id: str
    product_id: str
    user_id: Optional[str]
    movement_type: str
    quantity: float
    quantity_before: float
    quantity_after: float
    reference_type: Optional[str]
    reference_id: Optional[str]

    model_config = ConfigDict(from_attributes=True)


@router.get("/stock-alerts")
def list_stock_alerts(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    products = (
        db.query(Product)
        .filter(Product.business_id == current_user.business_id)
        .order_by(Product.name.asc(), Product.id.asc())
        .all()
    )

    alerts = []
    for product in products:
        recommendation = get_stock_alert(product)
        if recommendation is None:
            continue

        alerts.append({
            "product_id": recommendation.product_id,
            "product_name": recommendation.product_name,
            "sku": recommendation.sku,
            "stock_status": recommendation.stock_status,
            "current_quantity": recommendation.current_quantity,
            "reorder_level": recommendation.reorder_level,
            "target_quantity": recommendation.target_quantity,
            "suggested_order_quantity": recommendation.suggested_order_quantity,
            "unit_cost": recommendation.unit_cost,
            "estimated_cost": recommendation.estimated_cost,
        })

    return {
        "count": len(alerts),
        "alerts": alerts,
    }

@router.post(
    "/movements",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_movement(
    payload: StockMovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movement = apply_stock_movement(
        db=db,
        business_id=current_user.business_id,
        user=current_user,
        product_id=payload.product_id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
    )

    db.commit()
    db.refresh(movement)

    return movement


@router.get(
    "/movements",
    response_model=list[StockMovementResponse],
)
def list_stock_movements(
    product_id: Optional[str] = Query(default=None),
    movement_type: Optional[str] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(StockMovement)
        .filter(
            StockMovement.business_id == current_user.business_id
        )
    )

    if product_id:
        query = query.filter(
            StockMovement.product_id == product_id
        )

    if movement_type:
        normalized_type = movement_type.upper().strip()

        if normalized_type not in VALID_MOVEMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid movement_type",
            )

        query = query.filter(
            StockMovement.movement_type == normalized_type
        )

    return (
        query
        .order_by(
            StockMovement.created_at.desc(),
            StockMovement.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get(
    "/movements/{movement_id}",
    response_model=StockMovementResponse,
)
def get_stock_movement(
    movement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movement = (
        db.query(StockMovement)
        .filter(
            StockMovement.id == movement_id,
            StockMovement.business_id == current_user.business_id,
        )
        .first()
    )

    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock movement not found",
        )

    return movement
