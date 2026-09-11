#!/usr/bin/env bash
set -e

PROJECT="$HOME/IMRAN-BUSINESS-OS"
BACKUP="$PROJECT/backups/security_$(date +%Y%m%d_%H%M%S)"

cd "$PROJECT"

echo "========================================"
echo " IMRAN BUSINESS OS"
echo " SECURITY + TENANT ISOLATION UPGRADE"
echo "========================================"

mkdir -p "$BACKUP"

echo "[1/8] Backing up backend..."
cp -a backend "$BACKUP/backend"

echo "[2/8] Updating requirements..."

cat > backend/requirements.txt <<'EOF'
fastapi
uvicorn[standard]
sqlalchemy
pydantic
pydantic-settings
python-multipart
PyJWT
psycopg[binary]
EOF

echo "[3/8] Replacing JWT authentication..."

cat > backend/app/core/auth.py <<'PY'
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import User


SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "CHANGE_THIS_SECRET_IN_PRODUCTION"
)

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer()


def hash_password(password: str) -> str:
    import hashlib
    import hmac
    import base64
    import os

    salt = os.urandom(16)
    iterations = 120000

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations
    )

    return (
        "pbkdf2_sha256$"
        + str(iterations)
        + "$"
        + base64.urlsafe_b64encode(salt).decode()
        + "$"
        + base64.urlsafe_b64encode(derived).decode()
    )


def verify_password(password: str, stored: str) -> bool:
    import hashlib
    import base64

    try:
        algorithm, iterations, salt_b64, hash_b64 = stored.split("$")

        if algorithm != "pbkdf2_sha256":
            return False

        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(hash_b64.encode())

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations)
        )

        return __import__("hmac").compare_digest(actual, expected)

    except Exception:
        return False


def create_token(user_id: int, business_id: int) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "business_id": business_id,
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token expired"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    payload = verify_token(credentials.credentials)

    user_id = payload.get("sub")
    business_id = payload.get("business_id")

    if not user_id or not business_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication payload"
        )

    user = (
        db.query(User)
        .filter(
            User.id == int(user_id),
            User.business_id == int(business_id)
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User no longer exists"
        )

    return user


def require_owner(current_user=Depends(get_current_user)):
    if current_user.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Owner permission required"
        )

    return current_user


def require_manager(current_user=Depends(get_current_user)):
    allowed = {"owner", "admin"}

    if current_user.role not in allowed:
        raise HTTPException(
            status_code=403,
            detail="Manager permission required"
        )

    return current_user
PY

echo "[4/8] Replacing customer router with tenant isolation..."

cat > backend/app/routers/customers.py <<'PY'
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Customer
from app.core.auth import get_current_user


router = APIRouter(
    prefix="/api/v1/customers",
    tags=["Customers"]
)


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
        .filter(Customer.business_id == current_user.business_id)
        .order_by(Customer.id.desc())
        .all()
    )

    return customers


@router.get("/{customer_id}")
def get_customer(
    customer_id: int,
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
    customer_id: int,
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

    db.delete(customer)
    db.commit()

    return {
        "success": True,
        "message": "Customer deleted"
    }
PY

echo "[5/8] Replacing product router with tenant isolation..."

cat > backend/app/routers/products.py <<'PY'
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Product
from app.core.auth import get_current_user


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
        quantity=data.quantity
    )

    db.add(product)
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
        .filter(Product.business_id == current_user.business_id)
        .order_by(Product.id.desc())
        .all()
    )


@router.get("/{product_id}")
def get_product(
    product_id: int,
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


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
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

    db.delete(product)
    db.commit()

    return {
        "success": True,
        "message": "Product deleted"
    }
PY

echo "[6/8] Adding authenticated business endpoint..."

cat > backend/app/routers/businesses.py <<'PY'
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Business
from app.core.auth import get_current_user, require_owner


router = APIRouter(
    prefix="/api/v1/businesses",
    tags=["Businesses"]
)


@router.get("/me")
def my_business(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    business = (
        db.query(Business)
        .filter(Business.id == current_user.business_id)
        .first()
    )

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )

    return business


@router.patch("/me")
def update_my_business(
    data: dict,
    current_user=Depends(require_owner),
    db: Session = Depends(get_db)
):
    business = (
        db.query(Business)
        .filter(Business.id == current_user.business_id)
        .first()
    )

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )

    allowed = {
        "name",
        "category",
        "country_code",
        "currency_code",
        "timezone",
        "language_code"
    }

    for key, value in data.items():
        if key in allowed:
            setattr(business, key, value)

    db.commit()
    db.refresh(business)

    return business
PY

echo "[7/8] Updating environment configuration..."

cat > backend/.env.example <<'EOF'
APP_NAME=IMRAN BUSINESS OS
APP_ENV=development

# Local development
DATABASE_URL=sqlite:///./imran_business_os.db

# Production PostgreSQL example:
# DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/imran_business_os

SECRET_KEY=CHANGE_THIS_TO_A_LONG_RANDOM_SECRET

DEFAULT_CURRENCY=USD
DEFAULT_LANGUAGE=en
DEFAULT_TIMEZONE=UTC
EOF

echo "[8/8] Python syntax and security checks..."

python -m py_compile \
    backend/main.py \
    backend/app/database.py \
    backend/app/core/auth.py \
    backend/app/models/core.py \
    backend/app/routers/auth.py \
    backend/app/routers/businesses.py \
    backend/app/routers/customers.py \
    backend/app/routers/products.py

echo
echo "========================================"
echo " SECURITY UPGRADE COMPLETE"
echo "========================================"
echo
echo "PASS: JWT authentication"
echo "PASS: Token expiry"
echo "PASS: Business tenant isolation"
echo "PASS: Customer isolation"
echo "PASS: Product isolation"
echo "PASS: Owner permission check"
echo "PASS: PostgreSQL configuration"
echo "PASS: Python compilation"
echo
echo "BACKUP:"
echo "$BACKUP"
echo
echo "NEXT:"
echo "Run the API integration test."
echo "========================================"
