import uuid

from fastapi import status

from api.deps import AdminMembership, Db, ParentMembership, household_router
from schemas.kid import KidCreate, KidResponse, KidUpdate
from services import kids

router = household_router("/kids", tags=["kids"])


@router.get("")
def list_kids(membership: ParentMembership, db: Db) -> list[KidResponse]:
    return kids.list_kids(db, membership.household_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_kid(data: KidCreate, membership: AdminMembership, db: Db) -> KidResponse:
    kid = kids.create_kid(db, membership.household_id, data)
    return kids.kid_response(db, membership.household_id, kid)


@router.get("/{kid_id}")
def get_kid(kid_id: uuid.UUID, membership: ParentMembership, db: Db) -> KidResponse:
    kid = kids.get_kid(db, membership.household_id, kid_id)
    return kids.kid_response(db, membership.household_id, kid)


@router.patch("/{kid_id}")
def update_kid(
    kid_id: uuid.UUID, changes: KidUpdate, membership: AdminMembership, db: Db
) -> KidResponse:
    kid = kids.update_kid(db, membership.household_id, kid_id, changes)
    return kids.kid_response(db, membership.household_id, kid)


@router.delete("/{kid_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_kid(kid_id: uuid.UUID, membership: AdminMembership, db: Db) -> None:
    kids.remove_kid(db, membership.household_id, kid_id)
