import hashlib
import hmac
import threading
import time

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import RateLimitBucket

_cleanup_lock = threading.Lock()
_last_cleanup = 0.0
_CLEANUP_INTERVAL_SECONDS = 3600


def _cleanup_expired_buckets(db: Session, now: int) -> None:
    global _last_cleanup
    if now - _last_cleanup < _CLEANUP_INTERVAL_SECONDS:
        return
    with _cleanup_lock:
        if now - _last_cleanup < _CLEANUP_INTERVAL_SECONDS:
            return
        db.execute(
            delete(RateLimitBucket).where(RateLimitBucket.expires_at < now)
        )
        db.commit()
        _last_cleanup = now


def consume_rate_limit(
    db: Session,
    subject: str,
    limit: int,
    window_seconds: int,
) -> None:
    now = int(time.time())
    window_start = now - now % window_seconds
    bucket_key = hmac.new(
        settings.secret_key.encode(),
        subject.encode(),
        hashlib.sha256,
    ).hexdigest()

    _cleanup_expired_buckets(db, now)
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        insert = sqlite_insert
    elif dialect == "postgresql":
        insert = postgresql_insert
    else:
        raise RuntimeError(f"Rate limiting is not supported for database dialect: {dialect}")

    statement = insert(RateLimitBucket).values(
        key=bucket_key,
        window_start=window_start,
        expires_at=window_start + window_seconds,
        count=1,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[RateLimitBucket.key, RateLimitBucket.window_start],
        set_={"count": RateLimitBucket.count + 1},
    )
    db.execute(statement)
    count = db.scalar(
        select(RateLimitBucket.count).where(
            RateLimitBucket.key == bucket_key,
            RateLimitBucket.window_start == window_start,
        )
    )
    db.commit()

    if count is not None and count > limit:
        retry_after = max(1, window_start + window_seconds - now)
        raise HTTPException(
            status_code=429,
            detail="Limite de requisições atingido. Tente novamente mais tarde.",
            headers={"Retry-After": str(retry_after)},
        )


def client_address(request_client_host: str | None) -> str:
    return request_client_host or "unknown"
