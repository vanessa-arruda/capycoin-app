import uuid

from fastapi import status

from api.deps import AdminMembership, Db, ParentMembership, household_router
from schemas.member import MemberResponse
from services import members

router = household_router("/members", tags=["members"])


@router.get("")
def list_members(membership: ParentMembership, db: Db) -> list[MemberResponse]:
    return members.list_members(db, membership.household_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(user_id: uuid.UUID, membership: AdminMembership, db: Db) -> None:
    members.remove_parent(db, membership, user_id)
