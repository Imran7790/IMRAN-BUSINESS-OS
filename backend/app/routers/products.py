from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Product
from app.core.auth import get_current_user
from app.services.audit import create_audit_log


router = APIRouter(
    prefix="/api/v1/products",
    tags=["Products"]
)


class ProductCreate(BaseModel):
    name: str
    sku: str | None = None
    type: str = "product"
    price: float = 0
    cost: float = 0
    quantity: float = 0
    reorder_level: float = 0
    target_quantity: float = 0


@router.post("")
def create_product(
    data: ProductCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = Product(
        business_id=current_user.business_id,
        name=data.name,
        sku=data.sku,
        type=data.type,
        price=data.price,
        cost=data.cost,
        quantity=data.quantity,
        reorder_level=data.reorder_level,
        target_quantity=data.target_quantity
    )

    db.add(product)
    db.flush()

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="CREATE",
        entity_type="PRODUCT",
        entity_id=product.id,
        details=f"Created product: {product.name}"
    )

    db.commit()
    db.refresh(product)

    return product


@router.get("")
def list_products(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return (
        db.query(Product)
        .filter(
            Product.business_id == current_user.business_id
        )
        .order_by(Product.id.desc())
        .all()
    )


@router.get("/{product_id}")
def get_product(
    product_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.business_id == current_user.business_id
        )
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product


@router.patch("/{product_id}/reorder-settings")
def update_reorder_settings(
    product_id: str,
    reorder_level: float,
    target_quantity: float,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if reorder_level < 0:
        raise HTTPException(status_code=400, detail="reorder_level must be >= 0")

    if target_quantity <= reorder_level:
        raise HTTPException(
            status_code=400,
            detail="target_quantity must be greater than reorder_level",
        )

    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.business_id == current_user.business_id,
        )
        .first()
    )

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.reorder_level = reorder_level
    product.target_quantity = target_quantity

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="UPDATE",
        entity_type="PRODUCT",
        entity_id=product.id,
        details=(
            f"Updated reorder settings: level={reorder_level}, "
            f"target={target_quantity}"
        ),
    )

    db.commit()
    db.refresh(product)
    return product

@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.business_id == current_user.business_id
        )
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    product_name = product.name

    create_audit_log(
        db=db,
        business_id=current_user.business_id,
        user_id=current_user.id,
        action="DELETE",
        entity_type="PRODUCT",
        entity_id=product.id,
        details=f"Deleted product: {product_name}"
    )

    db.delete(product)
    db.commit()

    return {
        "success": True,
        "message": "Product deleted"
    }
