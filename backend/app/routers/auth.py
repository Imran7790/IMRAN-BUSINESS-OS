from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.core import Business, User
from app.core.auth import (
    hash_password,
    verify_password,
    create_token,
    verify_token
)


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["authentication"]
)


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    business_name: str
    business_category: str
    country_code: str
    currency_code: str
    timezone: str
    language_code: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db)
):

    email = payload.email.strip().lower()

    if len(payload.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters"
        )

    existing = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Email is already registered"
        )

    business = Business(
        id=str(uuid4()),
        name=payload.business_name.strip(),
        category=payload.business_category.strip(),
        country_code=payload.country_code.upper(),
        currency_code=payload.currency_code.upper(),
        timezone=payload.timezone,
        language_code=payload.language_code
    )

    user = User(
        id=str(uuid4()),
        business_id=business.id,
        email=email,
        password_hash=hash_password(
            payload.password
        ),
        role="owner"
    )

    db.add(business)
    db.add(user)
    db.commit()

    token = create_token(
        user.id,
        business.id
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role
        },
        "business": {
            "id": business.id,
            "name": business.name,
            "category": business.category,
            "country_code": business.country_code,
            "currency_code": business.currency_code,
            "timezone": business.timezone,
            "language_code": business.language_code
        }
    }


@router.post("/login")
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):

    email = payload.email.strip().lower()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if user is None or not verify_password(
        payload.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_token(
        user.id,
        user.business_id
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role
        },
        "business_id": user.business_id
    }


def authenticated_user(
    authorization: str | None = Header(
        default=None
    )
):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    if not authorization.lower().startswith(
        "bearer "
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header"
        )

    token = authorization[7:].strip()

    try:
        return verify_token(token)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


@router.get("/me")
def current_user(
    auth=Depends(authenticated_user),
    db: Session = Depends(get_db)
):

    user = db.get(
        User,
        auth["sub"]
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User no longer exists"
        )

    business = db.get(
        Business,
        user.business_id
    )

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role
        },
        "business": {
            "id": business.id,
            "name": business.name,
            "category": business.category,
            "country_code": business.country_code,
            "currency_code": business.currency_code,
            "timezone": business.timezone,
            "language_code": business.language_code
        }
    }
