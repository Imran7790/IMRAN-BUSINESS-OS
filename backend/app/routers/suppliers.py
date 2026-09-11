from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Supplier
from app.core.auth import get_current_user
from app.services.audit import create_audit_log


router = APIRouter(
    prefix="/api/v1/suppliers",
    tags=["Suppliers"],
)


class SupplierCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None


class SupplierResponse(BaseModel):
    id: str
    business_id: str
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None

    model_config = {
        "from_attributes": True
    }


class SupplierListResponse(BaseModel):
    items: list[SupplierResponse]
    limit: int
    offset: int
    total: int


@router.post(
    "",
    response_model=SupplierResponse,
)
def create_supplier(
    data: SupplierCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    supplier = Supplier(
        business_id=current_user.business_id,
        name=data.name,
        phone=data.phone,
        email=data.email,
        address=data.address,
    )

    db.add(supplier)
    db.flush()

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="CREATE",
        entity_type="SUPPLIER",
        entity_id=supplier.id,
        details=f"Created supplier: {supplier.name}",
    )

    db.commit()
    db.refresh(supplier)

    return supplier


@router.get(
    "",
    response_model=SupplierListResponse,
)
def list_suppliers(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Supplier)
        .filter(
            Supplier.business_id == current_user.business_id
        )
    )

    total = query.count()

    suppliers = (
        query
        .order_by(
            Supplier.name.asc(),
            Supplier.id.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return SupplierListResponse(
        items=suppliers,
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
)
def get_supplier(
    supplier_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    supplier = (
        db.query(Supplier)
        .filter(
            Supplier.id == supplier_id,
            Supplier.business_id == current_user.business_id,
        )
        .first()
    )

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found",
        )

    return supplier


@router.delete(
    "/{supplier_id}",
)
def delete_supplier(
    supplier_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    supplier = (
        db.query(Supplier)
        .filter(
            Supplier.id == supplier_id,
            Supplier.business_id == current_user.business_id,
        )
        .first()
    )

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found",
        )

    supplier_name = supplier.name

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="DELETE",
        entity_type="SUPPLIER",
        entity_id=supplier.id,
        details=f"Deleted supplier: {supplier_name}",
    )

    db.delete(supplier)
    db.commit()

    return {
        "message": "Supplier deleted",
        "id": supplier_id,
    }
