from datetime import date, datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Business, Customer, Product, Quotation, QuotationItem, User, Sale, SaleItem
from app.core.auth import get_current_user
from app.services.audit import create_audit_log
from app.services.inventory_service import apply_stock_movement

router = APIRouter(
    prefix="/api/v1/quotations",
    tags=["quotations"],
)

VALID_STATUSES = {
    "DRAFT",
    "SENT",
    "ACCEPTED",
    "REJECTED",
    "EXPIRED",
    "CANCELLED",
    "CONVERTED",
}


class QuotationItemRequest(BaseModel):
    product_id: Optional[str] = None
    description: str = Field(min_length=1, max_length=500)
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)


class QuotationCreateRequest(BaseModel):
    customer_id: Optional[str] = None
    valid_until: Optional[date] = None
    discount: float = Field(default=0, ge=0)
    tax: float = Field(default=0, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)
    items: list[QuotationItemRequest] = Field(min_length=1)


class QuotationUpdateRequest(BaseModel):
    customer_id: Optional[str] = None
    valid_until: Optional[date] = None
    discount: float = Field(default=0, ge=0)
    tax: float = Field(default=0, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)
    items: list[QuotationItemRequest] = Field(min_length=1)


def validate_customer(db: Session, business_id: str, customer_id: Optional[str]):
    if customer_id is None:
        return None
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.business_id == business_id,
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


def validate_items(db: Session, business_id: str, items: list[QuotationItemRequest]):
    validated = []
    for item in items:
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be greater than zero")
        if item.unit_price < 0:
            raise HTTPException(status_code=400, detail="Unit price cannot be negative")

        product = None
        if item.product_id:
            product = db.query(Product).filter(
                Product.id == item.product_id,
                Product.business_id == business_id,
            ).first()
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

        validated.append((item, product))
    return validated


def calculate_totals(items: list[QuotationItemRequest], discount: float, tax: float):
    subtotal = sum(item.quantity * item.unit_price for item in items)
    if discount > subtotal:
        raise HTTPException(status_code=400, detail="Discount cannot exceed subtotal")
    taxable = subtotal - discount
    total = taxable + tax
    return round(subtotal, 2), round(discount, 2), round(tax, 2), round(total, 2)


def generate_quotation_number(db: Session):
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    for _ in range(10):
        number = f"QT-{today}-{uuid.uuid4().hex[:8].upper()}"
        exists = db.query(Quotation.id).filter(
            Quotation.quotation_number == number
        ).first()
        if not exists:
            return number
    raise HTTPException(status_code=500, detail="Could not generate quotation number")


def quotation_response(db: Session, quotation: Quotation):
    items = db.query(QuotationItem).filter(
        QuotationItem.quotation_id == quotation.id
    ).all()

    return {
        "id": quotation.id,
        "business_id": quotation.business_id,
        "customer_id": quotation.customer_id,
        "quotation_number": quotation.quotation_number,
        "currency_code": quotation.currency_code,
        "subtotal": float(quotation.subtotal),
        "discount": float(quotation.discount),
        "tax": float(quotation.tax),
        "total": float(quotation.total),
        "status": quotation.status,
        "valid_until": quotation.valid_until,
        "notes": quotation.notes,
        "created_at": quotation.created_at,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "description": item.description,
                "quantity": float(item.quantity),
                "unit_price": float(item.unit_price),
                "line_total": float(item.line_total),
            }
            for item in items
        ],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_quotation(
    payload: QuotationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = db.query(Business).filter(Business.id == current_user.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    validate_customer(db, business.id, payload.customer_id)
    validated_items = validate_items(db, business.id, payload.items)
    subtotal, discount, tax, total = calculate_totals(
        payload.items,
        payload.discount,
        payload.tax,
    )

    quotation = Quotation(
        id=str(uuid.uuid4()),
        business_id=business.id,
        customer_id=payload.customer_id,
        quotation_number=generate_quotation_number(db),
        currency_code=business.currency_code,
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        total=total,
        status="DRAFT",
        valid_until=payload.valid_until,
        notes=payload.notes,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(quotation)
    db.flush()

    for item, product in validated_items:
        db.add(QuotationItem(
            id=str(uuid.uuid4()),
            quotation_id=quotation.id,
            product_id=item.product_id,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=round(item.quantity * item.unit_price, 2),
        ))

    create_audit_log(
        db,
        business.id,
        current_user.id,
        "QUOTATION_CREATED",
        "quotation",
        quotation.id,
        f"Quotation {quotation.quotation_number} created",
    )
    db.commit()
    db.refresh(quotation)
    return quotation_response(db, quotation)


@router.get("")
def list_quotations(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Quotation).filter(
        Quotation.business_id == current_user.business_id
    )

    if status_filter:
        normalized = status_filter.upper()
        if normalized not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid quotation status")
        query = query.filter(Quotation.status == normalized)

    if customer_id:
        validate_customer(db, current_user.business_id, customer_id)
        query = query.filter(Quotation.customer_id == customer_id)

    quotations = query.order_by(Quotation.created_at.desc()).all()
    return [quotation_response(db, quotation) for quotation in quotations]


@router.get("/{quotation_id}")
def get_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(
        Quotation.id == quotation_id,
        Quotation.business_id == current_user.business_id,
    ).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    return quotation_response(db, quotation)


@router.patch("/{quotation_id}")
def update_quotation(
    quotation_id: str,
    payload: QuotationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(
        Quotation.id == quotation_id,
        Quotation.business_id == current_user.business_id,
    ).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    if quotation.status != "DRAFT":
        raise HTTPException(
            status_code=400,
            detail="Only DRAFT quotations can be edited",
        )

    validate_customer(db, current_user.business_id, payload.customer_id)
    validated_items = validate_items(db, current_user.business_id, payload.items)
    subtotal, discount, tax, total = calculate_totals(
        payload.items,
        payload.discount,
        payload.tax,
    )

    quotation.customer_id = payload.customer_id
    quotation.subtotal = subtotal
    quotation.discount = discount
    quotation.tax = tax
    quotation.total = total
    quotation.valid_until = payload.valid_until
    quotation.notes = payload.notes

    db.query(QuotationItem).filter(
        QuotationItem.quotation_id == quotation.id
    ).delete(synchronize_session=False)

    for item, product in validated_items:
        db.add(QuotationItem(
            id=str(uuid.uuid4()),
            quotation_id=quotation.id,
            product_id=item.product_id,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=round(item.quantity * item.unit_price, 2),
        ))

    create_audit_log(
        db,
        current_user.business_id,
        current_user.id,
        "QUOTATION_UPDATED",
        "quotation",
        quotation.id,
        f"Quotation {quotation.quotation_number} updated",
    )
    db.commit()
    db.refresh(quotation)
    return quotation_response(db, quotation)


@router.post("/{quotation_id}/send")
def send_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(
        Quotation.id == quotation_id,
        Quotation.business_id == current_user.business_id,
    ).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    if quotation.status != "DRAFT":
        raise HTTPException(status_code=400, detail="Only DRAFT quotations can be sent")

    quotation.status = "SENT"
    create_audit_log(
        db,
        current_user.business_id,
        current_user.id,
        "QUOTATION_SENT",
        "quotation",
        quotation.id,
        f"Quotation {quotation.quotation_number} sent",
    )
    db.commit()
    db.refresh(quotation)
    return quotation_response(db, quotation)


@router.post("/{quotation_id}/accept")
def accept_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(
        Quotation.id == quotation_id,
        Quotation.business_id == current_user.business_id,
    ).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    if quotation.status != "SENT":
        raise HTTPException(status_code=400, detail="Only SENT quotations can be accepted")

    if quotation.valid_until and quotation.valid_until < date.today():
        quotation.status = "EXPIRED"
        create_audit_log(
            db,
            current_user.business_id,
            current_user.id,
            "QUOTATION_EXPIRED",
            "quotation",
            quotation.id,
            f"Quotation {quotation.quotation_number} expired",
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Quotation has expired")

    quotation.status = "ACCEPTED"
    create_audit_log(
        db,
        current_user.business_id,
        current_user.id,
        "QUOTATION_ACCEPTED",
        "quotation",
        quotation.id,
        f"Quotation {quotation.quotation_number} accepted",
    )
    db.commit()
    db.refresh(quotation)
    return quotation_response(db, quotation)


@router.post("/{quotation_id}/convert-to-sale")
def convert_quotation_to_sale(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business_id = current_user.business_id

    quotation = (
        db.query(Quotation)
        .filter(
            Quotation.id == quotation_id,
            Quotation.business_id == business_id,
        )
        .first()
    )

    if quotation is None:
        raise HTTPException(status_code=404, detail="Quotation not found")

    if quotation.status == "CONVERTED":
        raise HTTPException(
            status_code=409,
            detail="Quotation has already been converted to a sale",
        )

    if quotation.status != "ACCEPTED":
        raise HTTPException(
            status_code=400,
            detail="Only ACCEPTED quotations can be converted to a sale",
        )

    if quotation.valid_until and quotation.valid_until < date.today():
        quotation.status = "EXPIRED"
        create_audit_log(
            db,
            business_id,
            current_user.id,
            "QUOTATION_EXPIRED",
            "quotation",
            quotation.id,
            f"Quotation {quotation.quotation_number} expired before conversion",
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Quotation has expired")

    items = (
        db.query(QuotationItem)
        .filter(QuotationItem.quotation_id == quotation.id)
        .order_by(QuotationItem.id.asc())
        .all()
    )

    if not items:
        raise HTTPException(status_code=400, detail="Quotation has no items")

    for item in items:
        if item.product_id is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Quotation item '{item.description}' is not linked to a "
                    "product and cannot be converted to a sale"
                ),
            )

        product = (
            db.query(Product)
            .filter(
                Product.id == item.product_id,
                Product.business_id == business_id,
            )
            .first()
        )

        if product is None:
            raise HTTPException(
                status_code=404,
                detail=f"Product not found: {item.product_id}",
            )

    sale = Sale(
        id=str(uuid.uuid4()),
        business_id=business_id,
        customer_id=quotation.customer_id,
        currency_code=quotation.currency_code,
        subtotal=float(quotation.subtotal),
        total=float(quotation.total),
        status="COMPLETED",
    )

    db.add(sale)
    db.flush()

    try:
        for item in items:
            db.add(
                SaleItem(
                    id=str(uuid.uuid4()),
                    sale_id=sale.id,
                    product_id=item.product_id,
                    quantity=float(item.quantity),
                    unit_price=float(item.unit_price),
                    line_total=float(item.line_total),
                )
            )

            apply_stock_movement(
                db,
                business_id=business_id,
                user=current_user,
                product_id=item.product_id,
                movement_type="SALE",
                quantity=float(item.quantity),
                reference_type="SALE",
                reference_id=sale.id,
            )

        quotation.status = "CONVERTED"

        create_audit_log(
            db=db,
            business_id=business_id,
            user_id=current_user.id,
            action="CREATE",
            entity_type="SALE",
            entity_id=sale.id,
            details=(
                f"Sale created from quotation {quotation.quotation_number}; "
                f"quotation_id={quotation.id}; "
                f"total={sale.total} {sale.currency_code}"
            ),
        )

        create_audit_log(
            db=db,
            business_id=business_id,
            user_id=current_user.id,
            action="QUOTATION_CONVERTED",
            entity_type="quotation",
            entity_id=quotation.id,
            details=(
                f"Quotation {quotation.quotation_number} converted to sale; "
                f"sale_id={sale.id}"
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
        .filter(SaleItem.sale_id == sale.id)
        .all()
    )

    return sale

@router.post("/{quotation_id}/reject")
def reject_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(
        Quotation.id == quotation_id,
        Quotation.business_id == current_user.business_id,
    ).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    if quotation.status != "SENT":
        raise HTTPException(status_code=400, detail="Only SENT quotations can be rejected")

    quotation.status = "REJECTED"
    create_audit_log(
        db,
        current_user.business_id,
        current_user.id,
        "QUOTATION_REJECTED",
        "quotation",
        quotation.id,
        f"Quotation {quotation.quotation_number} rejected",
    )
    db.commit()
    db.refresh(quotation)
    return quotation_response(db, quotation)


@router.post("/{quotation_id}/cancel")
def cancel_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(
        Quotation.id == quotation_id,
        Quotation.business_id == current_user.business_id,
    ).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    if quotation.status in {"ACCEPTED", "REJECTED", "EXPIRED", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Quotation cannot be cancelled in its current status")

    quotation.status = "CANCELLED"
    create_audit_log(
        db,
        current_user.business_id,
        current_user.id,
        "QUOTATION_CANCELLED",
        "quotation",
        quotation.id,
        f"Quotation {quotation.quotation_number} cancelled",
    )
    db.commit()
    db.refresh(quotation)
    return quotation_response(db, quotation)


@router.post("/{quotation_id}/expire")
def expire_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quotation = db.query(Quotation).filter(
        Quotation.id == quotation_id,
        Quotation.business_id == current_user.business_id,
    ).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    if quotation.status != "SENT":
        raise HTTPException(status_code=400, detail="Only SENT quotations can expire")

    if not quotation.valid_until or quotation.valid_until >= date.today():
        raise HTTPException(status_code=400, detail="Quotation is not expired")

    quotation.status = "EXPIRED"
    create_audit_log(
        db,
        current_user.business_id,
        current_user.id,
        "QUOTATION_EXPIRED",
        "quotation",
        quotation.id,
        f"Quotation {quotation.quotation_number} expired",
    )
    db.commit()
    db.refresh(quotation)
    return quotation_response(db, quotation)
