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
            User.id == user_id,
            User.business_id == business_id
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
