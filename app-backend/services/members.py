import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import Conflict, InvalidInput, NotFound
from models import HouseholdMember, User
from models.enums import UserRole
from schemas.member import MemberResponse


def list_members(db: Session, household_id: uuid.UUID) -> list[MemberResponse]:
    rows = db.execute(
        select(HouseholdMember, User)
        .join(User)
        .where(HouseholdMember.household_id == household_id)
        .order_by(
            HouseholdMember.is_admin.desc(),
            User.role.desc(),
            User.display_name,
            User.id,
        )
    )
    return [
        MemberResponse(
            user_id=user.id,
            role=user.role,
            display_name=user.display_name,
            username=user.username,
            email=user.email,
            is_admin=member.is_admin,
            joined_at=member.created_at,
        )
        for member, user in rows
    ]


def remove_parent(db: Session, admin: HouseholdMember, user_id: uuid.UUID) -> None:
    member = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == admin.household_id,
            HouseholdMember.user_id == user_id,
        )
    )
    if member is None:
        raise NotFound("Member not found")
    if member.user_id == admin.user_id:
        raise Conflict("The admin cannot remove themselves")
    if member.user.role != UserRole.PARENT:
        raise InvalidInput("Kids are removed through the kid endpoints")

    db.delete(member)
    db.commit()
