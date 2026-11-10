from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from core.errors import InvalidInput
from models import Household, HouseholdMember, User
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


def delete_household(db: Session, household: Household, confirm_name: str) -> None:
    if confirm_name != household.name:
        raise InvalidInput("confirm_name does not match the household name")
    # The database deletes everything in the household (ON DELETE CASCADE).
    db.execute(delete(Household).where(Household.id == household.id))
    db.commit()
