from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Customer
from app.core.auth import get_current_user
from app.services.audit import create_audit_log

router = APIRouter(
    prefix="/api/v1/customers",
    tags=["Customers"]
)


class CustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None


class CustomerCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None


@router.post("")
def create_customer(
    data: CustomerCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    customer = Customer(
        business_id=current_user.business_id,
        name=data.name,
        phone=data.phone,
        email=data.email,
        address=data.address
    )

    db.add(customer)
    db.flush()

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="CREATE",
        entity_type="CUSTOMER",
        entity_id=customer.id,
        details=f"Created customer: {customer.name}",
    )

    db.commit()
    db.refresh(customer)

    return {
        "id": customer.id,
        "business_id": customer.business_id,
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "address": customer.address
    }


@router.get("")
def list_customers(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    customers = (
        db.query(Customer)
        .filter(
            Customer.business_id == current_user.business_id
        )
        .order_by(Customer.id.desc())
        .all()
    )

    return customers


@router.get("/{customer_id}")
def get_customer(
    customer_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.business_id == current_user.business_id
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    return customer


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.business_id == current_user.business_id
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    customer_name = customer.name

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="DELETE",
        entity_type="CUSTOMER",
        entity_id=customer.id,
        details=f"Deleted customer: {customer_name}",
    )

    db.delete(customer)
    db.commit()

    return {
        "success": True,
        "message": "Customer deleted"
    }


@router.patch("/{customer_id}")
def update_customer(
    customer_id: str,
    data: CustomerUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.business_id == current_user.business_id
        )
        .first()
    )

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    changes = data.model_dump(exclude_unset=True)

    if "name" in changes and changes["name"] is not None:
        if not changes["name"].strip():
            raise HTTPException(
                status_code=400,
                detail="Customer name cannot be empty"
            )
        customer.name = changes["name"].strip()

    for field in ("phone", "email", "address"):
        if field in changes:
            value = changes[field]
            setattr(customer, field, value.strip() if isinstance(value, str) else value)

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="UPDATE",
        entity_type="CUSTOMER",
        entity_id=customer.id,
        details=f"Updated customer: {customer.name}",
    )

    db.commit()
    db.refresh(customer)

    return {
        "id": customer.id,
        "business_id": customer.business_id,
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "address": customer.address
    }
