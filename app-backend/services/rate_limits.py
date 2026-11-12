from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from core import clock
from core.errors import TooManyRequests
from core.security import hash_token
from models import RateLimitEvent


@dataclass(frozen=True)
class Limit:
    name: str
    max_events: int
    window: timedelta


LOGIN_FAILURES_PER_LOGIN = Limit("login", 5, timedelta(minutes=15))
LOGIN_FAILURES_PER_IP = Limit("login-ip", 20, timedelta(minutes=15))
CODE_REQUESTS_PER_IP = Limit("code-ip", 10, timedelta(minutes=15))
HOUSEHOLD_EMAILS = Limit("household-email", 20, timedelta(days=1))
PHOTO_UPLOADS_PER_KID = Limit("photo-kid", 30, timedelta(days=1))

# Events older than the longest window are never counted again.
KEEP_EVENTS_FOR = timedelta(days=1)

TOO_MANY = "Too many attempts. Try again later."


def _key(limit: Limit, value: str) -> str:
    return f"{limit.name}:{hash_token(value)}"


def check(db: Session, limit: Limit, value: str) -> None:
    """Raise TooManyRequests if `value` reached the limit within its window."""
    count = db.scalar(
        select(func.count())
        .select_from(RateLimitEvent)
        .where(
            RateLimitEvent.key == _key(limit, value),
            RateLimitEvent.created_at > clock.now() - limit.window,
        )
    )
    if count >= limit.max_events:
        raise TooManyRequests(TOO_MANY)


def record(db: Session, limit: Limit, value: str) -> None:
    """Count one event for `value`. The caller commits."""
    now = clock.now()
    db.execute(
        delete(RateLimitEvent).where(RateLimitEvent.created_at < now - KEEP_EVENTS_FOR)
    )
    db.add(RateLimitEvent(key=_key(limit, value), created_at=now))


def hit(db: Session, limit: Limit, value: str) -> None:
    """Check the limit, then count this event. The caller commits."""
    check(db, limit, value)
    record(db, limit, value)
