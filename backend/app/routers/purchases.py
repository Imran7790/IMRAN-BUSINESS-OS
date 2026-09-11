from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Purchase, PurchaseItem, Product, Supplier
from app.core.auth import get_current_user
from app.services.audit import create_audit_log
from app.services.inventory_service import apply_stock_movement

router = APIRouter(
    prefix="/api/v1/purchases",
    tags=["Purchases"],
)


class PurchaseItemCreate(BaseModel):
    product_id: str
    quantity: float
    unit_cost: float | None = None


class PurchaseCreate(BaseModel):
    supplier_id: str | None = None
    currency_code: str
    items: list[PurchaseItemCreate]


class PurchaseItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    purchase_id: str
    product_id: str
    quantity: float
    unit_cost: float
    line_total: float


class PurchaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    supplier_id: str | None
    currency_code: str
    subtotal: float
    total: float
    status: str
    created_at: datetime
    items: list[PurchaseItemResponse] = []


class PurchaseListResponse(BaseModel):
    items: list[PurchaseResponse]
    limit: int
    offset: int
    total: int


@router.post(
    "",
    response_model=PurchaseResponse,
)
def create_purchase(
    data: PurchaseCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not data.items:
        raise HTTPException(
            status_code=400,
            detail="Purchase must contain at least one item",
        )

    if data.currency_code != current_user.business.currency_code:
        raise HTTPException(
            status_code=400,
            detail="Currency does not match business currency",
        )

    supplier = None

    if data.supplier_id:
        supplier = (
            db.query(Supplier)
            .filter(
                Supplier.id == data.supplier_id,
                Supplier.business_id == current_user.business_id,
            )
            .first()
        )

        if not supplier:
            raise HTTPException(
                status_code=404,
                detail="Supplier not found",
            )

    purchase = Purchase(
        business_id=current_user.business_id,
        supplier_id=data.supplier_id,
        currency_code=data.currency_code,
        subtotal=0,
        total=0,
        status="COMPLETED",
    )

    db.add(purchase)
    db.flush()

    subtotal = 0.0

    try:
        for item_data in data.items:
            product = (
                db.query(Product)
                .filter(
                    Product.id == item_data.product_id,
                    Product.business_id == current_user.business_id,
                )
                .first()
            )

            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product not found: {item_data.product_id}",
                )

            if item_data.quantity <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Quantity must be greater than zero",
                )

            unit_cost = (
                product.cost
                if item_data.unit_cost is None
                else item_data.unit_cost
            )

            if unit_cost is None:
                raise HTTPException(
                    status_code=400,
                    detail="Unit cost is required",
                )

            if unit_cost < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Unit cost cannot be negative",
                )

            line_total = item_data.quantity * unit_cost
            subtotal += line_total

            purchase_item = PurchaseItem(
                purchase_id=purchase.id,
                product_id=product.id,
                quantity=item_data.quantity,
                unit_cost=unit_cost,
                line_total=line_total,
            )

            db.add(purchase_item)

            apply_stock_movement(
                db,
                business_id=current_user.business_id,
                user=current_user,
                product_id=product.id,
                movement_type="PURCHASE",
                quantity=item_data.quantity,
                reference_type="PURCHASE",
                reference_id=purchase.id,
            )

        purchase.subtotal = subtotal
        purchase.total = subtotal

        create_audit_log(
            db=db,
            business_id=current_user.business_id,
            user_id=current_user.id,
            action="CREATE",
            entity_type="PURCHASE",
            entity_id=purchase.id,
            details=(
                f"Created purchase with total "
                f"{purchase.total} {purchase.currency_code}"
            ),
        )

        db.commit()

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

    db.refresh(purchase)

    purchase.items = (
        db.query(PurchaseItem)
        .filter(PurchaseItem.purchase_id == purchase.id)
        .all()
    )

    return purchase


@router.get(
    "",
    response_model=PurchaseListResponse,
)
def list_purchases(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Purchase)
        .filter(
            Purchase.business_id == current_user.business_id
        )
    )

    total = query.count()

    purchases = (
        query
        .order_by(
            Purchase.created_at.desc(),
            Purchase.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    for purchase in purchases:
        purchase.items = (
            db.query(PurchaseItem)
            .filter(
                PurchaseItem.purchase_id == purchase.id
            )
            .all()
        )

    return PurchaseListResponse(
        items=purchases,
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get(
    "/{purchase_id}",
    response_model=PurchaseResponse,
)
def get_purchase(
    purchase_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    purchase = (
        db.query(Purchase)
        .filter(
            Purchase.id == purchase_id,
            Purchase.business_id == current_user.business_id,
        )
        .first()
    )

    if not purchase:
        raise HTTPException(
            status_code=404,
            detail="Purchase not found",
        )

    purchase.items = (
        db.query(PurchaseItem)
        .filter(
            PurchaseItem.purchase_id == purchase.id
        )
        .all()
    )

    return purchase


@router.delete(
    "/{purchase_id}",
)
def delete_purchase(
    purchase_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    purchase = (
        db.query(Purchase)
        .filter(
            Purchase.id == purchase_id,
            Purchase.business_id == current_user.business_id,
        )
        .first()
    )

    if not purchase:
        raise HTTPException(
            status_code=404,
            detail="Purchase not found",
        )

    purchase_total = purchase.total

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="DELETE",
        entity_type="PURCHASE",
        entity_id=purchase.id,
        details=(
            f"Deleted purchase with total "
            f"{purchase_total} {purchase.currency_code}"
        ),
    )

    db.query(PurchaseItem).filter(
        PurchaseItem.purchase_id == purchase.id
    ).delete(
        synchronize_session=False
    )

    db.delete(purchase)
    db.commit()

    return {
        "message": "Purchase deleted",
        "id": purchase_id,
    }


@router.post(
    "/{purchase_id}/cancel",
)
def cancel_purchase(
    purchase_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    purchase = (
        db.query(Purchase)
        .filter(
            Purchase.id == purchase_id,
            Purchase.business_id == current_user.business_id,
        )
        .first()
    )

    if not purchase:
        raise HTTPException(
            status_code=404,
            detail="Purchase not found",
        )

    if purchase.status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Purchase is already cancelled",
        )

    if purchase.status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail=(
                "Purchase cannot be cancelled "
                f"from status {purchase.status}"
            ),
        )

    items = (
        db.query(PurchaseItem)
        .filter(
            PurchaseItem.purchase_id == purchase.id
        )
        .all()
    )

    try:
        for item in items:
            apply_stock_movement(
                db,
                business_id=current_user.business_id,
                user=current_user,
                product_id=item.product_id,
                movement_type="RETURN_OUT",
                quantity=item.quantity,
                reference_type="PURCHASE_CANCELLATION",
                reference_id=purchase.id,
            )

        purchase.status = "CANCELLED"

        create_audit_log(
            db=db,
            business_id=current_user.business_id,
            user_id=current_user.id,
            action="CANCEL",
            entity_type="PURCHASE",
            entity_id=purchase.id,
            details=(
                f"Cancelled purchase with total "
                f"{purchase.total} {purchase.currency_code}"
            ),
        )

        db.commit()

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

    return {
        "message": "Purchase cancelled",
        "id": purchase.id,
        "status": purchase.status,
    }
