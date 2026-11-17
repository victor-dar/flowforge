import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.models import SessionLocal, User

bearer = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"{base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_text, digest_text = stored.split("$", 1)
        salt = base64.urlsafe_b64decode(salt_text)
        expected = base64.urlsafe_b64decode(digest_text)
    except (ValueError, TypeError):
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return hmac.compare_digest(candidate, expected)


def create_token(user_id: int) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"sub": str(user_id), "exp": int(time.time()) + settings.access_token_minutes * 60}).encode()).rstrip(b"=").decode()
    signature = hmac.new(settings.secret_key.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação necessária", headers={"WWW-Authenticate": "Bearer"})
    if not credentials:
        raise unauthorized
    try:
        header, payload, signature = credentials.credentials.split(".")
        expected = hmac.new(settings.secret_key.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        actual = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if not hmac.compare_digest(expected, actual) or data["exp"] < time.time():
            raise ValueError("invalid token")
        user = db.get(User, int(data["sub"]))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise unauthorized from None
    if not user:
        raise unauthorized
    return user
