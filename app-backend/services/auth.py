from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core import clock
from core.email import EmailMessage, EmailSender
from core.errors import Conflict, InvalidInput, TooManyRequests, Unauthorized
from core.security import (
    hash_secret,
    hash_token,
    new_otp_code,
    new_token,
    spend_verify_time,
    verify_secret,
)
from models import OtpCode, User, UserSession
from models.enums import OtpPurpose, UserRole

OTP_TTL = timedelta(minutes=10)
OTP_MAX_ATTEMPTS = 5
OTP_REQUEST_LIMIT = 3
OTP_REQUEST_WINDOW = timedelta(minutes=15)

SESSION_MAX_AGE = timedelta(days=30)
SESSION_IDLE_TIMEOUT = timedelta(days=7)
SESSION_TOUCH_INTERVAL = timedelta(minutes=5)

INVALID_CODE = "Invalid or expired code"
INVALID_LOGIN = "Invalid login or password"
INVALID_SESSION = "Not logged in"


@dataclass
class NewSession:
    token: str
    session: UserSession
    user: User


def issue_code(db: Session, email: str, purpose: OtpPurpose) -> str:
    """Store a new code for this email and purpose, and return it to be sent.

    Earlier codes for the same purpose stop working. The request limit counts
    codes of every purpose, since each one is an email to that address.
    """
    now = clock.now()
    recent = db.scalar(
        select(func.count())
        .select_from(OtpCode)
        .where(OtpCode.email == email, OtpCode.created_at > now - OTP_REQUEST_WINDOW)
    )
    if recent >= OTP_REQUEST_LIMIT:
        raise TooManyRequests("Too many codes requested. Try again later.")

    db.execute(
        update(OtpCode)
        .where(
            OtpCode.email == email,
            OtpCode.purpose == purpose,
            OtpCode.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    code = new_otp_code()
    db.add(
        OtpCode(
            email=email,
            purpose=purpose,
            code_hash=hash_secret(code),
            expires_at=now + OTP_TTL,
            created_at=now,
        )
    )
    db.commit()
    return code


def check_code(db: Session, email: str, code: str, purpose: OtpPurpose) -> OtpCode:
    """Return the matching code, locked. The caller sets consumed_at and commits.

    Raises Unauthorized for a wrong, expired or used code; wrong guesses count
    towards the attempt limit.
    """
    otp = db.scalar(
        select(OtpCode)
        .where(
            OtpCode.email == email,
            OtpCode.purpose == purpose,
            OtpCode.consumed_at.is_(None),
            OtpCode.expires_at > clock.now(),
            OtpCode.attempts < OTP_MAX_ATTEMPTS,
        )
        .order_by(OtpCode.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    if otp is None:
        spend_verify_time()
        raise Unauthorized(INVALID_CODE)
    if not verify_secret(code, otp.code_hash):
        otp.attempts += 1
        db.commit()
        raise Unauthorized(INVALID_CODE)
    return otp


def request_otp(db: Session, email: str, sender: EmailSender) -> None:
    code = issue_code(db, email, OtpPurpose.LOGIN)
    sender.send(
        EmailMessage(
            to=email,
            subject="Your Capycoin code",
            body=f"Your Capycoin code is {code}. It expires in 10 minutes.",
        )
    )


def verify_otp(
    db: Session, email: str, code: str, display_name: str | None
) -> tuple[NewSession, bool]:
    """Log in with a code, creating a parent account for a new email.

    Returns the session and whether an account was created.
    """
    otp = check_code(db, email, code, OtpPurpose.LOGIN)

    user = db.scalar(select(User).where(User.email == email))
    created = user is None
    if created:
        if display_name is None:
            # The code stays valid, so the client can resend it with a name.
            db.rollback()
            raise InvalidInput("display_name is required to create an account")
        user = User(role=UserRole.PARENT, email=email, display_name=display_name)
        db.add(user)

    otp.consumed_at = clock.now()
    try:
        new_session = create_session(db, user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict("An account with this email was just created. Try again.")
    return new_session, created


def login_with_password(db: Session, login: str, password: str) -> NewSession:
    user = db.scalar(
        select(User).where(or_(User.email == login, User.username == login))
    )
    if user is None or user.password_hash is None:
        spend_verify_time()
        raise Unauthorized(INVALID_LOGIN)
    if not verify_secret(password, user.password_hash):
        raise Unauthorized(INVALID_LOGIN)

    new_session = create_session(db, user)
    db.commit()
    return new_session


def authenticate(db: Session, token: str) -> UserSession:
    now = clock.now()
    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == hash_token(token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
            UserSession.last_used_at > now - SESSION_IDLE_TIMEOUT,
        )
    )
    if session is None:
        raise Unauthorized(INVALID_SESSION)

    if session.last_used_at < now - SESSION_TOUCH_INTERVAL:
        session.last_used_at = now
        db.commit()
    return session


def logout(db: Session, session: UserSession) -> None:
    session.revoked_at = clock.now()
    db.commit()


def change_password(
    db: Session,
    user: User,
    current_password: str | None,
    new_password: str,
    current_session: UserSession,
) -> None:
    if user.password_hash is not None and not (
        current_password and verify_secret(current_password, user.password_hash)
    ):
        raise InvalidInput("Current password is incorrect")

    user.password_hash = hash_secret(new_password)
    revoke_sessions(db, user, keep=current_session)
    db.commit()


def revoke_sessions(db: Session, user: User, keep: UserSession | None = None) -> None:
    query = update(UserSession).where(
        UserSession.user_id == user.id, UserSession.revoked_at.is_(None)
    )
    if keep is not None:
        query = query.where(UserSession.id != keep.id)
    db.execute(query.values(revoked_at=clock.now()))


def create_session(db: Session, user: User) -> NewSession:
    now = clock.now()
    token = new_token()
    session = UserSession(
        user=user,
        token_hash=hash_token(token),
        expires_at=now + SESSION_MAX_AGE,
        last_used_at=now,
        created_at=now,
    )
    db.add(session)
    return NewSession(token=token, session=session, user=user)
