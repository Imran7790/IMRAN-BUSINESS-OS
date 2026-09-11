from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.core import Product, StockMovement, User
from app.services.audit import create_audit_log
from app.services.stock_alerts import sync_stock_notification


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


def apply_stock_movement(
    db: Session,
    *,
    business_id: str,
    user: User,
    product_id: str,
    movement_type: str,
    quantity: float,
    reference_type: Optional[str] = None,
    reference_id: Optional[str] = None,
) -> StockMovement:
    """
    Apply one inventory movement.

    Product.quantity is the authoritative current balance.
    StockMovement is the immutable movement ledger.
    """

    movement_type = movement_type.upper().strip()

    if movement_type not in INBOUND_TYPES | OUTBOUND_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid movement_type",
        )

    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than zero",
        )

    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.business_id == business_id,
        )
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    quantity_before = float(product.quantity or 0)

    if movement_type in INBOUND_TYPES:
        quantity_after = quantity_before + float(quantity)
    else:
        quantity_after = quantity_before - float(quantity)

        if quantity_after < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient stock",
            )

    product.quantity = quantity_after

    movement = StockMovement(
        business_id=business_id,
        product_id=product.id,
        user_id=user.id,
        movement_type=movement_type,
        quantity=float(quantity),
        quantity_before=quantity_before,
        quantity_after=quantity_after,
        reference_type=reference_type,
        reference_id=reference_id,
    )

    db.add(movement)
    db.flush()

    create_audit_log(
        db=db,
        business_id=business_id,
        user_id=user.id,
        action="CREATE",
        entity_type="STOCK_MOVEMENT",
        entity_id=movement.id,
        details=(
            f"product_id={product.id};"
            f"movement_type={movement_type};"
            f"quantity={quantity};"
            f"quantity_before={quantity_before};"
            f"quantity_after={quantity_after};"
            f"reference_type={reference_type};"
            f"reference_id={reference_id}"
        ),
    )

    sync_stock_notification(db=db, product=product, user_id=user.id)

    return movement
