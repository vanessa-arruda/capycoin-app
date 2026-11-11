import uuid

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from core import clock
from core.email import EmailMessage, EmailSender
from core.errors import InvalidInput, NotFound, Unauthorized
from core.security import hash_secret
from models import (
    CreditTransaction,
    HouseholdMember,
    Notification,
    Prize,
    PrizeClaim,
    Task,
    TaskAssignment,
    TaskSubmission,
    User,
)
from models.enums import OtpPurpose, UserRole
from schemas.kid import KidCreate, KidResponse, KidUpdate
from services import auth, rate_limits, wallet
from services.users import commit_user_changes

KID_NOT_FOUND = "Kid not found"


def get_kid(db: Session, household_id: uuid.UUID, kid_id: uuid.UUID) -> User:
    kid = db.scalar(
        select(User)
        .join(HouseholdMember)
        .where(
            HouseholdMember.household_id == household_id,
            User.id == kid_id,
            User.role == UserRole.KID,
        )
    )
    if kid is None:
        raise NotFound(KID_NOT_FOUND)
    return kid


def check_kid_ids(
    db: Session, household_id: uuid.UUID, kid_ids: list[uuid.UUID]
) -> None:
    """Raise InvalidInput unless every id is a kid of this household."""
    found = set(
        db.scalars(
            select(User.id)
            .join(HouseholdMember)
            .where(
                HouseholdMember.household_id == household_id,
                User.role == UserRole.KID,
                User.id.in_(kid_ids),
            )
        )
    )
    if found != set(kid_ids):
        raise InvalidInput("kid_ids must all be kids of this household")


def list_kids(db: Session, household_id: uuid.UUID) -> list[KidResponse]:
    kids = db.scalars(
        select(User)
        .join(HouseholdMember)
        .where(HouseholdMember.household_id == household_id, User.role == UserRole.KID)
        .order_by(User.display_name, User.id)
    ).all()
    found = wallet.balances(db, household_id, (kid.id for kid in kids))
    return [_response(kid, found[kid.id]) for kid in kids]


def kid_response(db: Session, household_id: uuid.UUID, kid: User) -> KidResponse:
    return _response(kid, wallet.balances(db, household_id, [kid.id])[kid.id])


def _response(kid: User, balance: wallet.Balance) -> KidResponse:
    return KidResponse(
        id=kid.id,
        display_name=kid.display_name,
        username=kid.username,
        email=kid.email,
        balance=balance.balance,
        reserved=balance.reserved,
        available=balance.available,
    )


def send_email_code(
    db: Session, parent: HouseholdMember, email: str, sender: EmailSender
) -> None:
    rate_limits.hit(db, rate_limits.HOUSEHOLD_EMAILS, str(parent.household_id))
    code = auth.issue_code(db, email, OtpPurpose.EMAIL_VALIDATION)
    sender.send(
        EmailMessage(
            to=email,
            subject="Confirm your email for Capycoin",
            body=(
                f"{parent.user.display_name} wants to add this email address to "
                f'a kid\'s account in the household "{parent.household.name}" '
                "on Capycoin.\n\n"
                f"To confirm, give them this code: {code}. "
                "It expires in 10 minutes.\n\n"
                "If you don't know what this is, ignore this email. "
                "The address will not be added."
            ),
        )
    )


def _use_email_code(db: Session, email: str, code: str) -> None:
    try:
        otp = auth.check_code(db, email, code, OtpPurpose.EMAIL_VALIDATION)
    except Unauthorized:
        # A 401 would tell the client that the parent's session ended.
        raise InvalidInput(auth.INVALID_CODE)
    otp.consumed_at = clock.now()


def create_kid(db: Session, household_id: uuid.UUID, data: KidCreate) -> User:
    if data.email is not None:
        _use_email_code(db, data.email, data.code)
    kid = User(
        role=UserRole.KID,
        display_name=data.display_name,
        email=data.email,
        username=data.username,
        password_hash=hash_secret(data.password) if data.password else None,
    )
    kid.memberships.append(HouseholdMember(household_id=household_id))
    db.add(kid)
    commit_user_changes(db)
    return kid


def update_kid(
    db: Session, household_id: uuid.UUID, kid_id: uuid.UUID, changes: KidUpdate
) -> User:
    kid = get_kid(db, household_id, kid_id)
    fields = changes.model_fields_set
    for field in ("display_name", "password"):
        if field in fields and getattr(changes, field) is None:
            raise InvalidInput(f"{field} cannot be empty")

    if changes.display_name is not None:
        kid.display_name = changes.display_name
    if "username" in fields:
        kid.username = changes.username
    if "email" in fields and changes.email != kid.email:
        if changes.email is not None:
            _use_email_code(db, changes.email, changes.code)
        kid.email = changes.email
    if changes.password is not None:
        kid.password_hash = hash_secret(changes.password)
        auth.revoke_sessions(db, kid)

    commit_user_changes(db)
    return kid


def remove_kid(db: Session, household_id: uuid.UUID, kid_id: uuid.UUID) -> None:
    """Remove a kid and their data from one household.

    The account is deleted too when the kid belongs to no other household.
    """
    get_kid(db, household_id, kid_id)
    tasks = select(Task.id).where(Task.household_id == household_id)
    prizes = select(Prize.id).where(Prize.household_id == household_id)

    # Credits first: they reference submissions and claims without cascading.
    db.execute(
        delete(CreditTransaction).where(
            CreditTransaction.household_id == household_id,
            CreditTransaction.kid_id == kid_id,
        )
    )
    db.execute(
        delete(Notification).where(
            Notification.household_id == household_id,
            Notification.recipient_id == kid_id,
        )
    )
    db.execute(
        delete(PrizeClaim).where(
            PrizeClaim.kid_id == kid_id, PrizeClaim.prize_id.in_(prizes)
        )
    )
    db.execute(
        delete(TaskSubmission).where(
            TaskSubmission.kid_id == kid_id, TaskSubmission.task_id.in_(tasks)
        )
    )
    db.execute(
        delete(TaskAssignment).where(
            TaskAssignment.kid_id == kid_id, TaskAssignment.task_id.in_(tasks)
        )
    )
    db.execute(
        delete(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == kid_id,
        )
    )
    if not db.scalar(select(exists().where(HouseholdMember.user_id == kid_id))):
        db.execute(delete(User).where(User.id == kid_id))
    db.commit()
