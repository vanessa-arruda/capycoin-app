import uuid
from typing import Annotated

from fastapi import Depends, status

from api.deps import AdminMembership, Db, ParentMembership, household_router
from core.email import EmailSender, get_email_sender
from core.storage import PhotoStore, get_photo_store
from schemas.kid import KidCreate, KidEmailCode, KidResponse, KidUpdate
from services import kids

router = household_router("/kids", tags=["kids"])


@router.get("")
def list_kids(membership: ParentMembership, db: Db) -> list[KidResponse]:
    return kids.list_kids(db, membership.household_id)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_kid(data: KidCreate, membership: AdminMembership, db: Db) -> KidResponse:
    kid = kids.create_kid(db, membership.household_id, data)
    return kids.kid_response(db, membership.household_id, kid)


@router.post("/email-code", status_code=status.HTTP_202_ACCEPTED)
def send_email_code(
    payload: KidEmailCode,
    membership: AdminMembership,
    db: Db,
    sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> None:
    kids.send_email_code(db, membership, payload.email, sender)


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
def remove_kid(
    kid_id: uuid.UUID,
    membership: AdminMembership,
    db: Db,
    store: Annotated[PhotoStore, Depends(get_photo_store)],
) -> None:
    kids.remove_kid(db, membership.household_id, kid_id, store)
