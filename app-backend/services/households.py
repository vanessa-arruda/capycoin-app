import uuid

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from core.errors import InvalidInput
from core.storage import PhotoStore
from models import Household, HouseholdMember, Task, TaskSubmission, User
from models.enums import UserRole
from schemas.household import HouseholdCreate, HouseholdUpdate, MyHouseholdResponse


def create_household(db: Session, user: User, data: HouseholdCreate) -> Household:
    household = Household(name=data.name, timezone=data.timezone)
    household.members.append(HouseholdMember(user=user, is_admin=True))
    db.add(household)
    db.commit()
    return household


def list_user_households(db: Session, user: User) -> list[MyHouseholdResponse]:
    rows = db.execute(
        select(Household, HouseholdMember.is_admin)
        .join(HouseholdMember)
        .where(HouseholdMember.user_id == user.id)
        .order_by(Household.name, Household.id)
    )
    return [
        MyHouseholdResponse(
            id=household.id,
            name=household.name,
            timezone=household.timezone,
            is_admin=is_admin,
        )
        for household, is_admin in rows
    ]


def update_household(
    db: Session, household: Household, changes: HouseholdUpdate
) -> Household:
    for field in changes.model_fields_set:
        value = getattr(changes, field)
        if value is None:
            raise InvalidInput(f"{field} cannot be empty")
        setattr(household, field, value)
    db.commit()
    return household


def delete_household(
    db: Session, household: Household, confirm_name: str, store: PhotoStore
) -> None:
    if confirm_name != household.name:
        raise InvalidInput("confirm_name does not match the household name")
    photo_paths = delete_household_rows(db, household.id)
    db.commit()
    store.delete(photo_paths)


def delete_household_rows(db: Session, household_id: uuid.UUID) -> list[str]:
    """Delete a household, everything in it and its kids' accounts, without committing.

    Returns the photo paths to delete from storage after the commit.
    """
    photo_paths = db.scalars(
        select(TaskSubmission.photo_path)
        .join(Task)
        .where(
            Task.household_id == household_id, TaskSubmission.photo_path.is_not(None)
        )
    ).all()
    kid_ids = db.scalars(
        select(User.id)
        .join(HouseholdMember)
        .where(HouseholdMember.household_id == household_id, User.role == UserRole.KID)
    ).all()
    # The database deletes everything in the household (ON DELETE CASCADE).
    db.execute(delete(Household).where(Household.id == household_id))
    # A kid belongs to one household, so their account goes with it.
    db.execute(
        delete(User).where(
            User.id.in_(kid_ids), ~exists().where(HouseholdMember.user_id == User.id)
        )
    )
    return list(photo_paths)
