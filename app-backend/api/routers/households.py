from fastapi import APIRouter, status

from api.deps import (
    AdminMembership,
    Db,
    Membership,
    ParentMembership,
    ParentUser,
    household_router,
)
from schemas.household import (
    HouseholdCreate,
    HouseholdDelete,
    HouseholdResponse,
    HouseholdUpdate,
)
from services import households

router = APIRouter(prefix="/households", tags=["households"])
household = household_router(tags=["households"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_household(
    data: HouseholdCreate, user: ParentUser, db: Db
) -> HouseholdResponse:
    return HouseholdResponse.model_validate(households.create_household(db, user, data))


@household.get("")
def get_household(membership: Membership) -> HouseholdResponse:
    return HouseholdResponse.model_validate(membership.household)


@household.patch("")
def update_household(
    changes: HouseholdUpdate, membership: ParentMembership, db: Db
) -> HouseholdResponse:
    return HouseholdResponse.model_validate(
        households.update_household(db, membership.household, changes)
    )


@household.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_household(
    payload: HouseholdDelete, membership: AdminMembership, db: Db
) -> None:
    households.delete_household(db, membership.household, payload.confirm_name)
