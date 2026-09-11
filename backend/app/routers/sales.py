from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Customer, Sale, SaleItem, Product
from app.core.auth import get_current_user
from app.services.audit import create_audit_log
from app.services.inventory_service import apply_stock_movement

router = APIRouter(
    prefix="/api/v1/sales",
    tags=["Sales"],
)


class SaleItemCreate(BaseModel):
    product_id: str
    quantity: float
    unit_price: float | None = None


class SaleCreate(BaseModel):
    customer_id: str | None = None
    currency_code: str
    items: list[SaleItemCreate]


class SaleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sale_id: str
    product_id: str
    quantity: float
    unit_price: float
    line_total: float


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    customer_id: str | None
    currency_code: str
    subtotal: float
    total: float
    status: str
    created_at: datetime
    items: list[SaleItemResponse] = []


class SaleListResponse(BaseModel):
    items: list[SaleResponse]
    limit: int
    offset: int
    total: int


@router.post(
    "",
    response_model=SaleResponse,
)
def create_sale(
    data: SaleCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not data.items:
        raise HTTPException(
            status_code=400,
            detail="Sale must contain at least one item",
        )

    if data.currency_code != current_user.business.currency_code:
        raise HTTPException(
            status_code=400,
            detail="Currency does not match business currency",
        )

    customer = None

    if data.customer_id:
        customer = (
            db.query(Customer)
            .filter(
                Customer.id == data.customer_id,
                Customer.business_id == current_user.business_id,
            )
            .first()
        )

        if not customer:
            raise HTTPException(
                status_code=404,
                detail="Customer not found",
            )

    sale = Sale(
        business_id=current_user.business_id,
        customer_id=data.customer_id,
        currency_code=data.currency_code,
        subtotal=0,
        total=0,
        status="COMPLETED",
    )

    db.add(sale)
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

            unit_price = (
                product.price
                if item_data.unit_price is None
                else item_data.unit_price
            )

            if unit_price < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Unit price cannot be negative",
                )

            line_total = item_data.quantity * unit_price
            subtotal += line_total

            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=item_data.quantity,
                unit_price=unit_price,
                line_total=line_total,
            )

            db.add(sale_item)

            apply_stock_movement(
                db,
                business_id=current_user.business_id,
                user=current_user,
                product_id=product.id,
                movement_type="SALE",
                quantity=item_data.quantity,
                reference_type="SALE",
                reference_id=sale.id,
            )

        sale.subtotal = subtotal
        sale.total = subtotal

        create_audit_log(
            db=db,
            business_id=current_user.business_id,
            user_id=current_user.id,
            action="CREATE",
            entity_type="SALE",
            entity_id=sale.id,
            details=(
                f"Created sale with total "
                f"{sale.total} {sale.currency_code}"
            ),
        )

        db.commit()

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

    db.refresh(sale)

    sale.items = (
        db.query(SaleItem)
        .filter(
            SaleItem.sale_id == sale.id
        )
        .all()
    )

    return sale


@router.get(
    "",
    response_model=SaleListResponse,
)
def list_sales(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Sale)
        .filter(
            Sale.business_id == current_user.business_id
        )
    )

    total = query.count()

    sales = (
        query
        .order_by(
            Sale.created_at.desc(),
            Sale.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    for sale in sales:
        sale.items = (
            db.query(SaleItem)
            .filter(
                SaleItem.sale_id == sale.id
            )
            .all()
        )

    return SaleListResponse(
        items=sales,
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get(
    "/{sale_id}",
    response_model=SaleResponse,
)
def get_sale(
    sale_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sale = (
        db.query(Sale)
        .filter(
            Sale.id == sale_id,
            Sale.business_id == current_user.business_id,
        )
        .first()
    )

    if not sale:
        raise HTTPException(
            status_code=404,
            detail="Sale not found",
        )

    sale.items = (
        db.query(SaleItem)
        .filter(
            SaleItem.sale_id == sale.id
        )
        .all()
    )

    return sale


@router.post(
    "/{sale_id}/cancel",
)
def cancel_sale(
    sale_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sale = (
        db.query(Sale)
        .filter(
            Sale.id == sale_id,
            Sale.business_id == current_user.business_id,
        )
        .first()
    )

    if not sale:
        raise HTTPException(
            status_code=404,
            detail="Sale not found",
        )

    if sale.status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Sale is already cancelled",
        )

    if sale.status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail=f"Sale cannot be cancelled from status {sale.status}",
        )

    items = (
        db.query(SaleItem)
        .filter(SaleItem.sale_id == sale.id)
        .all()
    )

    try:
        for item in items:
            apply_stock_movement(
                db,
                business_id=current_user.business_id,
                user=current_user,
                product_id=item.product_id,
                movement_type="RETURN_IN",
                quantity=item.quantity,
                reference_type="SALE_CANCELLATION",
                reference_id=sale.id,
            )

        sale.status = "CANCELLED"

        create_audit_log(
            db=db,
            business_id=current_user.business_id,
            user_id=current_user.id,
            action="CANCEL",
            entity_type="SALE",
            entity_id=sale.id,
            details=(
                f"Cancelled sale with total "
                f"{sale.total} {sale.currency_code}"
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
        "message": "Sale cancelled",
        "id": sale.id,
        "status": sale.status,
    }


@router.delete(
    "/{sale_id}",
)
def delete_sale(
    sale_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sale = (
        db.query(Sale)
        .filter(
            Sale.id == sale_id,
            Sale.business_id == current_user.business_id,
        )
        .first()
    )

    if not sale:
        raise HTTPException(
            status_code=404,
            detail="Sale not found",
        )

    sale_total = sale.total

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="DELETE",
        entity_type="SALE",
        entity_id=sale.id,
        details=(
            f"Deleted sale with total "
            f"{sale_total} {sale.currency_code}"
        ),
    )

    db.query(SaleItem).filter(
        SaleItem.sale_id == sale.id
    ).delete(
        synchronize_session=False
    )

    db.delete(sale)
    db.commit()

    return {
        "message": "Sale deleted",
        "id": sale_id,
    }
