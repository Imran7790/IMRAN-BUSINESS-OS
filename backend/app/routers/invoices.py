from datetime import date, datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import (
    Business,
    Customer,
    Invoice,
    InvoiceItem,
    Product,
    Payment,
    User,
)
from app.core.auth import get_current_user
from app.services.audit import create_audit_log


router = APIRouter(
    prefix="/api/v1/invoices",
    tags=["invoices"],
)


# ============================================================
# CONSTANTS
# ============================================================

VALID_STATUSES = {
    "DRAFT",
    "ISSUED",
    "PAID",
    "PARTIALLY_PAID",
    "OVERDUE",
    "CANCELLED",
}


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class InvoiceItemRequest(BaseModel):
    product_id: Optional[str] = None

    description: str = Field(
        min_length=1,
        max_length=500,
    )

    quantity: float = Field(
        gt=0,
    )

    unit_price: float = Field(
        ge=0,
    )


class InvoiceCreateRequest(BaseModel):
    customer_id: Optional[str] = None

    due_date: Optional[date] = None

    discount: float = Field(
        default=0,
        ge=0,
    )

    tax: float = Field(
        default=0,
        ge=0,
    )

    items: list[InvoiceItemRequest] = Field(
        min_length=1,
    )


class InvoiceUpdateRequest(BaseModel):
    customer_id: Optional[str] = None

    due_date: Optional[date] = None

    discount: float = Field(
        default=0,
        ge=0,
    )

    tax: float = Field(
        default=0,
        ge=0,
    )

    items: list[InvoiceItemRequest] = Field(
        min_length=1,
    )


# ============================================================
# RESPONSE BUILDERS
# ============================================================

def invoice_item_response(item: InvoiceItem):
    return {
        "id": item.id,
        "invoice_id": item.invoice_id,
        "product_id": item.product_id,
        "description": item.description,
        "quantity": item.quantity,
        "unit_price": item.unit_price,
        "line_total": item.line_total,
    }


def invoice_response(
    db: Session,
    invoice: Invoice,
):
    items = (
        db.query(InvoiceItem)
        .filter(
            InvoiceItem.invoice_id == invoice.id,
        )
        .all()
    )

    amount_paid = sum(float(payment.amount) for payment in db.query(Payment).filter(Payment.invoice_id == invoice.id, Payment.business_id == invoice.business_id).all())
    balance_due = max(float(invoice.total) - amount_paid, 0.0)

    return {
        "id": invoice.id,
        "business_id": invoice.business_id,
        "customer_id": invoice.customer_id,
        "invoice_number": invoice.invoice_number,
        "currency_code": invoice.currency_code,
        "subtotal": invoice.subtotal,
        "discount": invoice.discount,
        "tax": invoice.tax,
        "total": invoice.total,
        "amount_paid": amount_paid,
        "balance_due": balance_due,
        "status": invoice.status,
        "due_date": invoice.due_date,
        "issued_at": invoice.issued_at,
        "created_at": invoice.created_at,
        "items": [
            invoice_item_response(item)
            for item in items
        ],
    }


# ============================================================
# VALIDATION HELPERS
# ============================================================

def get_business_currency(
    db: Session,
    business_id: str,
) -> str:

    business = (
        db.query(Business)
        .filter(
            Business.id == business_id,
        )
        .first()
    )

    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found",
        )

    return business.currency_code


def validate_customer(
    db: Session,
    *,
    business_id: str,
    customer_id: Optional[str],
):

    if customer_id is None:
        return None

    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.business_id == business_id,
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    return customer


def validate_items(
    db: Session,
    *,
    business_id: str,
    items: list[InvoiceItemRequest],
):
    validated = []
    subtotal = 0.0

    for item_data in items:

        if item_data.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item quantity must be greater than zero",
            )

        if item_data.unit_price < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unit price cannot be negative",
            )

        product = None

        if item_data.product_id:

            product = (
                db.query(Product)
                .filter(
                    Product.id == item_data.product_id,
                    Product.business_id == business_id,
                )
                .first()
            )

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Product not found",
                )

        line_total = (
            float(item_data.quantity)
            * float(item_data.unit_price)
        )

        subtotal += line_total

        validated.append(
            {
                "product": product,
                "product_id": item_data.product_id,
                "description": item_data.description,
                "quantity": float(item_data.quantity),
                "unit_price": float(item_data.unit_price),
                "line_total": line_total,
            }
        )

    return validated, subtotal


def generate_invoice_number() -> str:
    """
    Generates a globally unique invoice number.

    Example:
    INV-20260909-A1B2C3D4
    """

    today = datetime.now(timezone.utc).replace(tzinfo=None)

    return (
        f"INV-{today.strftime('%Y%m%d')}-"
        f"{uuid.uuid4().hex[:8].upper()}"
    )


# ============================================================
# CREATE INVOICE
# ============================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_invoice(
    payload: InvoiceCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    business_id = current_user.business_id

    currency_code = get_business_currency(
        db,
        business_id,
    )

    validate_customer(
        db,
        business_id=business_id,
        customer_id=payload.customer_id,
    )

    validated_items, subtotal = validate_items(
        db,
        business_id=business_id,
        items=payload.items,
    )

    discount = float(payload.discount)
    tax = float(payload.tax)

    if discount > subtotal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discount cannot exceed subtotal",
        )

    taxable_amount = subtotal - discount
    total = taxable_amount + tax

    invoice = Invoice(
        business_id=business_id,
        customer_id=payload.customer_id,
        invoice_number=generate_invoice_number(),
        currency_code=currency_code,
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        total=total,
        status="DRAFT",
        due_date=payload.due_date,
    )

    db.add(invoice)
    db.flush()

    for item_data in validated_items:

        item = InvoiceItem(
            invoice_id=invoice.id,
            product_id=item_data["product_id"],
            description=item_data["description"],
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            line_total=item_data["line_total"],
        )

        db.add(item)

    create_audit_log(
        db=db,
        business_id=business_id,
        user_id=current_user.id,
        action="CREATE",
        entity_type="INVOICE",
        entity_id=invoice.id,
        details=(
            f"invoice_number={invoice.invoice_number};"
            f"subtotal={subtotal};"
            f"discount={discount};"
            f"tax={tax};"
            f"total={total};"
            f"status=DRAFT"
        ),
    )

    db.commit()
    db.refresh(invoice)

    return invoice_response(
        db,
        invoice,
    )


# ============================================================
# LIST INVOICES
# ============================================================

@router.get("")
def list_invoices(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    invoice_status: Optional[str] = Query(
        default=None,
        alias="status",
    ),
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    business_id = current_user.business_id

    query = (
        db.query(Invoice)
        .filter(
            Invoice.business_id == business_id,
        )
    )

    if invoice_status:
        invoice_status = invoice_status.upper()

        if invoice_status not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid invoice status",
            )

        query = query.filter(
            Invoice.status == invoice_status,
        )

    if customer_id:
        query = query.filter(
            Invoice.customer_id == customer_id,
        )

    total_count = query.count()

    invoices = (
        query
        .order_by(
            Invoice.created_at.desc(),
        )
        .offset(
            (page - 1) * page_size,
        )
        .limit(page_size)
        .all()
    )

    return {
        "page": page,
        "page_size": page_size,
        "total": total_count,
        "pages": (
            (total_count + page_size - 1)
            // page_size
            if total_count
            else 0
        ),
        "items": [
            invoice_response(
                db,
                invoice,
            )
            for invoice in invoices
        ],
    }


# ============================================================
# GET ONE INVOICE
# ============================================================

@router.get("/{invoice_id}")
def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    invoice = (
        db.query(Invoice)
        .filter(
            Invoice.id == invoice_id,
            Invoice.business_id == current_user.business_id,
        )
        .first()
    )

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    return invoice_response(
        db,
        invoice,
    )


# ============================================================
# UPDATE DRAFT
# ============================================================

@router.patch("/{invoice_id}")
def update_invoice(
    invoice_id: str,
    payload: InvoiceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    invoice = (
        db.query(Invoice)
        .filter(
            Invoice.id == invoice_id,
            Invoice.business_id == current_user.business_id,
        )
        .first()
    )

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    if invoice.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DRAFT invoices can be edited",
        )

    validate_customer(
        db,
        business_id=current_user.business_id,
        customer_id=payload.customer_id,
    )

    validated_items, subtotal = validate_items(
        db,
        business_id=current_user.business_id,
        items=payload.items,
    )

    discount = float(payload.discount)
    tax = float(payload.tax)

    if discount > subtotal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discount cannot exceed subtotal",
        )

    total = (
        subtotal
        - discount
        + tax
    )

    invoice.customer_id = payload.customer_id
    invoice.subtotal = subtotal
    invoice.discount = discount
    invoice.tax = tax
    invoice.total = total
    invoice.due_date = payload.due_date

    db.query(InvoiceItem).filter(
        InvoiceItem.invoice_id == invoice.id,
    ).delete(
        synchronize_session=False,
    )

    for item_data in validated_items:

        db.add(
            InvoiceItem(
                invoice_id=invoice.id,
                product_id=item_data["product_id"],
                description=item_data["description"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                line_total=item_data["line_total"],
            )
        )

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="UPDATE",
        entity_type="INVOICE",
        entity_id=invoice.id,
        details=(
            f"invoice_number={invoice.invoice_number};"
            f"subtotal={subtotal};"
            f"discount={discount};"
            f"tax={tax};"
            f"total={total}"
        ),
    )

    db.commit()
    db.refresh(invoice)

    return invoice_response(
        db,
        invoice,
    )


# ============================================================
# ISSUE INVOICE
# ============================================================

@router.post("/{invoice_id}/issue")
def issue_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    invoice = (
        db.query(Invoice)
        .filter(
            Invoice.id == invoice_id,
            Invoice.business_id == current_user.business_id,
        )
        .first()
    )

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    if invoice.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DRAFT invoices can be issued",
        )

    invoice.status = "ISSUED"
    invoice.issued_at = datetime.now(timezone.utc).replace(tzinfo=None)

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="ISSUE",
        entity_type="INVOICE",
        entity_id=invoice.id,
        details=(
            f"invoice_number={invoice.invoice_number};"
            f"total={invoice.total};"
            f"status=ISSUED"
        ),
    )

    db.commit()
    db.refresh(invoice)

    return invoice_response(
        db,
        invoice,
    )


# ============================================================
# CANCEL INVOICE
# ============================================================

@router.post("/{invoice_id}/cancel")
def cancel_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    invoice = (
        db.query(Invoice)
        .filter(
            Invoice.id == invoice_id,
            Invoice.business_id == current_user.business_id,
        )
        .first()
    )

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    if invoice.status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already cancelled",
        )

    if invoice.status in {
        "PAID",
        "PARTIALLY_PAID",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paid invoices cannot be cancelled",
        )

    invoice.status = "CANCELLED"

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="CANCEL",
        entity_type="INVOICE",
        entity_id=invoice.id,
        details=(
            f"invoice_number={invoice.invoice_number};"
            f"total={invoice.total};"
            f"status=CANCELLED"
        ),
    )

    db.commit()
    db.refresh(invoice)

    return invoice_response(
        db,
        invoice,
    )
