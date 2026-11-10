import uuid
from datetime import timedelta

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core import clock
from core.config import settings
from core.email import EmailMessage, EmailSender
from core.errors import Conflict, Forbidden, NotFound
from core.security import hash_token, new_token
from models import Household, HouseholdInvitation, HouseholdMember, User
from models.enums import InvitationStatus

INVITATION_TTL = timedelta(days=7)
INVITATION_NOT_FOUND = "Invitation not found"


def list_invitations(db: Session, household_id: uuid.UUID) -> list[HouseholdInvitation]:
    return list(
        db.scalars(
            select(HouseholdInvitation)
            .where(
                HouseholdInvitation.household_id == household_id,
                HouseholdInvitation.status == InvitationStatus.PENDING,
                HouseholdInvitation.expires_at > clock.now(),
            )
            .order_by(HouseholdInvitation.created_at.desc())
        )
    )


def create_invitation(
    db: Session, admin: HouseholdMember, email: str, sender: EmailSender
) -> HouseholdInvitation:
    now = clock.now()
    household = admin.household
    is_member = db.scalar(
        select(
            exists().where(
                HouseholdMember.household_id == household.id,
                HouseholdMember.user_id == User.id,
                User.email == email,
            )
        )
    )
    if is_member:
        raise Conflict("This person is already a member")

    pending = db.scalar(
        select(HouseholdInvitation)
        .where(
            HouseholdInvitation.household_id == household.id,
            HouseholdInvitation.email == email,
            HouseholdInvitation.status == InvitationStatus.PENDING,
        )
        .with_for_update()
    )
    if pending is not None:
        if pending.expires_at > now:
            raise Conflict("This email already has a pending invitation")
        pending.status = InvitationStatus.REVOKED
        db.flush()

    token = new_token()
    invitation = HouseholdInvitation(
        household_id=household.id,
        email=email,
        invited_by=admin.user_id,
        token_hash=hash_token(token),
        expires_at=now + INVITATION_TTL,
        created_at=now,
    )
    db.add(invitation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict("This email already has a pending invitation")

    sender.send(_invitation_email(email, household, admin.user, token))
    return invitation


def _invitation_email(
    email: str, household: Household, inviter: User, token: str
) -> EmailMessage:
    # The token goes in the fragment, which browsers don't send to servers.
    link = f"{settings.app_url}/invitations/accept#token={token}"
    return EmailMessage(
        to=email,
        subject=f"Join {household.name} on Capycoin",
        body=(
            f'{inviter.display_name} invited you to join "{household.name}" '
            "on Capycoin.\n\n"
            "Sign up or log in with this email address, then open this link "
            f"to accept:\n{link}\n\nThe link expires in 7 days."
        ),
    )


def revoke_invitation(
    db: Session, household_id: uuid.UUID, invitation_id: uuid.UUID
) -> None:
    invitation = db.scalar(
        select(HouseholdInvitation).where(
            HouseholdInvitation.id == invitation_id,
            HouseholdInvitation.household_id == household_id,
            HouseholdInvitation.status == InvitationStatus.PENDING,
        )
    )
    if invitation is None:
        raise NotFound(INVITATION_NOT_FOUND)
    invitation.status = InvitationStatus.REVOKED
    db.commit()


def accept_invitation(db: Session, user: User, token: str) -> Household:
    now = clock.now()
    invitation = db.scalar(
        select(HouseholdInvitation)
        .where(
            HouseholdInvitation.token_hash == hash_token(token),
            HouseholdInvitation.status == InvitationStatus.PENDING,
            HouseholdInvitation.expires_at > now,
        )
        .with_for_update()
    )
    if invitation is None:
        raise NotFound(INVITATION_NOT_FOUND)
    if invitation.email != user.email:
        raise Forbidden("This invitation is for another email address")
    if db.get(HouseholdMember, (invitation.household_id, user.id)) is not None:
        raise Conflict("You are already a member of this household")

    db.add(HouseholdMember(household_id=invitation.household_id, user_id=user.id))
    invitation.status = InvitationStatus.ACCEPTED
    invitation.responded_at = now
    db.commit()
    return invitation.household
