import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from api.deps import AdminMembership, Db, ParentUser, household_router
from core.email import EmailSender, get_email_sender
from schemas.household import HouseholdResponse
from schemas.invitation import InvitationAccept, InvitationCreate, InvitationResponse
from services import invitations

router = household_router("/invitations", tags=["invitations"])
accept_router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.get("")
def list_invitations(membership: AdminMembership, db: Db) -> list[InvitationResponse]:
    return [
        InvitationResponse.model_validate(invitation)
        for invitation in invitations.list_invitations(db, membership.household_id)
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: InvitationCreate,
    membership: AdminMembership,
    db: Db,
    sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> InvitationResponse:
    return InvitationResponse.model_validate(
        invitations.create_invitation(db, membership, payload.email, sender)
    )


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(
    invitation_id: uuid.UUID, membership: AdminMembership, db: Db
) -> None:
    invitations.revoke_invitation(db, membership.household_id, invitation_id)


@accept_router.post("/accept")
def accept_invitation(
    payload: InvitationAccept, user: ParentUser, db: Db
) -> HouseholdResponse:
    return HouseholdResponse.model_validate(
        invitations.accept_invitation(db, user, payload.token)
    )
