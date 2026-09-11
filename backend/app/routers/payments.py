from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.core import Invoice, Payment, User
from app.core.auth import get_current_user
from app.services.audit import create_audit_log

router = APIRouter(prefix="/api/v1/invoices/{invoice_id}/payments", tags=["payments"])

class PaymentCreateRequest(BaseModel):
    amount: float = Field(gt=0)
    payment_method: str = Field(min_length=1, max_length=100)
    reference: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=1000)
    paid_at: Optional[datetime] = None

class PaymentResponse(BaseModel):
    id: str
    business_id: str
    invoice_id: str
    amount: float
    currency_code: str
    payment_method: str
    reference: Optional[str]
    notes: Optional[str]
    paid_at: datetime
    created_at: datetime

class PaymentListResponse(BaseModel):
    invoice_id: str
    currency_code: str
    invoice_total: float
    amount_paid: float
    balance_due: float
    invoice_status: str
    payments: list[PaymentResponse]

def payment_response(payment: Payment) -> dict:
    return {"id": payment.id, "business_id": payment.business_id, "invoice_id": payment.invoice_id, "amount": payment.amount, "currency_code": payment.currency_code, "payment_method": payment.payment_method, "reference": payment.reference, "notes": payment.notes, "paid_at": payment.paid_at, "created_at": payment.created_at}

def get_tenant_invoice(db: Session, *, invoice_id: str, business_id: str) -> Invoice:
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.business_id == business_id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice

def get_amount_paid(db: Session, *, invoice_id: str, business_id: str) -> float:
    payments = db.query(Payment).filter(Payment.invoice_id == invoice_id, Payment.business_id == business_id).all()
    return sum(float(payment.amount) for payment in payments)

@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(invoice_id: str, payload: PaymentCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    business_id = current_user.business_id
    invoice = get_tenant_invoice(db, invoice_id=invoice_id, business_id=business_id)

    if invoice.status not in {"ISSUED", "PARTIALLY_PAID"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payments can only be recorded for ISSUED or PARTIALLY_PAID invoices")

    currency_code = invoice.currency_code
    amount_paid = get_amount_paid(db, invoice_id=invoice.id, business_id=business_id)
    total = float(invoice.total)
    balance_due = total - amount_paid

    if balance_due <= 0.00000001:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice is already fully paid")

    amount = float(payload.amount)

    if amount > balance_due + 0.00000001:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Payment exceeds invoice balance. Balance due: {balance_due}")

    payment_method = payload.payment_method.strip()
    if not payment_method:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment method cannot be blank")

    payment = Payment(business_id=business_id, invoice_id=invoice.id, amount=amount, currency_code=currency_code, payment_method=payment_method, reference=payload.reference, notes=payload.notes, paid_at=payload.paid_at or datetime.now(timezone.utc).replace(tzinfo=None))

    try:
        db.add(payment)
        db.flush()
        new_amount_paid = amount_paid + amount

        if abs(new_amount_paid - total) <= 0.00000001:
            invoice.status = "PAID"
        else:
            invoice.status = "PARTIALLY_PAID"

        create_audit_log(db=db, business_id=business_id, user_id=current_user.id, action="PAYMENT_CREATED", entity_type="payment", entity_id=payment.id, details=f"Invoice {invoice.id}; amount={amount}; currency={currency_code}; payment_method={payment.payment_method}; invoice_status={invoice.status}")

        db.commit()
        db.refresh(payment)
        return payment_response(payment)

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to record payment")

@router.get("", response_model=PaymentListResponse)
def list_invoice_payments(invoice_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    business_id = current_user.business_id
    invoice = get_tenant_invoice(db, invoice_id=invoice_id, business_id=business_id)

    payments = db.query(Payment).filter(Payment.invoice_id == invoice.id, Payment.business_id == business_id).order_by(Payment.paid_at.asc(), Payment.created_at.asc()).all()

    amount_paid = sum(float(payment.amount) for payment in payments)
    total = float(invoice.total)
    balance_due = max(total - amount_paid, 0.0)

    return {"invoice_id": invoice.id, "currency_code": invoice.currency_code, "invoice_total": total, "amount_paid": amount_paid, "balance_due": balance_due, "invoice_status": invoice.status, "payments": [payment_response(payment) for payment in payments]}
