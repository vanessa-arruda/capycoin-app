from fastapi import APIRouter, status

from api.deps import CurrentSession, CurrentUser, Db
from schemas.user import PasswordChange, UserResponse, UserUpdate
from services import auth, users

router = APIRouter(prefix="/me", tags=["me"])


@router.get("")
def get_me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch("")
def update_me(changes: UserUpdate, user: CurrentUser, db: Db) -> UserResponse:
    return UserResponse.model_validate(users.update_user(db, user, changes))


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: PasswordChange, session: CurrentSession, db: Db) -> None:
    auth.change_password(
        db, session.user, payload.current_password, payload.new_password, session
    )
