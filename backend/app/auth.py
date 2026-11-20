import base64
import binascii
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi import Cookie, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.models import SessionLocal, User

bearer = HTTPBearer(auto_error=False)


def optional_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    access_token_cookie: str | None = Cookie(default=None, alias="flowforge_access"),
) -> str | None:
    if credentials:
        return credentials.credentials
    if settings.app_env.lower() == "production":
        return access_token_cookie
    return access_token_cookie


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{binascii.hexlify(salt).decode()}${binascii.hexlify(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_text, digest_text = stored.split("$", 1)
        if len(salt_text) == 32 and len(digest_text) == 64:
            salt = binascii.unhexlify(salt_text)
            expected = binascii.unhexlify(digest_text)
        else:
            salt = base64.b64decode(salt_text, altchars=b"-_", validate=True)
            expected = base64.b64decode(digest_text, altchars=b"-_", validate=True)
    except (ValueError, TypeError, binascii.Error):
        return False
    if not salt or len(expected) != hashlib.sha256().digest_size:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return hmac.compare_digest(candidate, expected)


def create_token(user_id: int) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes),
        },
        settings.secret_key,
        algorithm="HS256",
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    access_token_cookie: str | None = Cookie(default=None, alias="flowforge_access"),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticação necessária",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = access_token_cookie if settings.app_env.lower() == "production" else None
    if credentials:
        token = credentials.credentials
    if not token:
        raise unauthorized
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        user = db.get(User, int(claims["sub"]))
    except (jwt.PyJWTError, TypeError, ValueError, KeyError):
        raise unauthorized from None
    if user is None:
        raise unauthorized
    return user


def get_optional_user(
    token: str | None = Depends(optional_bearer_token),
    db: Session = Depends(get_db),
) -> User | None:
    if not token:
        return None
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        return db.get(User, int(claims["sub"]))
    except (jwt.PyJWTError, TypeError, ValueError, KeyError):
        return None
