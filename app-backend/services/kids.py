import uuid

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from core.errors import InvalidInput, NotFound
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
from models.enums import UserRole
from schemas.kid import KidCreate, KidResponse, KidUpdate
from services import auth, wallet
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
        balance=balance.balance,
        reserved=balance.reserved,
        available=balance.available,
    )


def create_kid(db: Session, household_id: uuid.UUID, data: KidCreate) -> User:
    kid = User(
        role=UserRole.KID,
        display_name=data.display_name,
        username=data.username,
        password_hash=hash_secret(data.password),
    )
    kid.memberships.append(HouseholdMember(household_id=household_id))
    db.add(kid)
    commit_user_changes(db)
    return kid


def update_kid(
    db: Session, household_id: uuid.UUID, kid_id: uuid.UUID, changes: KidUpdate
) -> User:
    kid = get_kid(db, household_id, kid_id)
    for field in changes.model_fields_set:
        if getattr(changes, field) is None:
            raise InvalidInput(f"{field} cannot be empty")
    if changes.display_name is not None:
        kid.display_name = changes.display_name
    if changes.username is not None:
        kid.username = changes.username
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
