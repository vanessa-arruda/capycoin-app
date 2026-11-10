import uuid
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.errors import Forbidden, NotFound, Unauthorized
from models import HouseholdMember, User, UserSession
from models.enums import UserRole
from schemas.common import PageParams
from services import auth

HOUSEHOLD_NOT_FOUND = "Household not found"


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


Db = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


def get_current_session(
    db: Db,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UserSession:
    if credentials is None:
        raise Unauthorized(auth.INVALID_SESSION)
    return auth.authenticate(db, credentials.credentials)


CurrentSession = Annotated[UserSession, Depends(get_current_session)]


def get_current_user(session: CurrentSession) -> User:
    return session.user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_parent_account(user: CurrentUser) -> User:
    if user.role != UserRole.PARENT:
        raise Forbidden("Only parents can do this")
    return user


ParentUser = Annotated[User, Depends(require_parent_account)]


def get_membership(
    household_id: uuid.UUID, user: CurrentUser, db: Db
) -> HouseholdMember:
    membership = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == user.id,
        )
    )
    # Same answer for a missing household and someone else's, so ids reveal nothing.
    if membership is None:
        raise NotFound(HOUSEHOLD_NOT_FOUND)
    return membership


Membership = Annotated[HouseholdMember, Depends(get_membership)]


def require_parent(membership: Membership) -> HouseholdMember:
    if membership.user.role != UserRole.PARENT:
        raise Forbidden("Only parents of this household can do this")
    return membership


ParentMembership = Annotated[HouseholdMember, Depends(require_parent)]


def require_admin(membership: ParentMembership) -> HouseholdMember:
    if not membership.is_admin:
        raise Forbidden("Only the household admin can do this")
    return membership


AdminMembership = Annotated[HouseholdMember, Depends(require_admin)]


def household_router(path: str = "", **kwargs: Any) -> APIRouter:
    """Router under /households/{household_id}{path} that only members can reach."""
    return APIRouter(
        prefix="/households/{household_id}" + path,
        dependencies=[Depends(get_membership)],
        **kwargs,
    )


def get_page_params(
    before: uuid.UUID | None = None, limit: Annotated[int, Query(ge=1, le=100)] = 50
) -> PageParams:
    return PageParams(before=before, limit=limit)


Pagination = Annotated[PageParams, Depends(get_page_params)]
