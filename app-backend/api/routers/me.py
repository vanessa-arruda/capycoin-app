from fastapi import APIRouter, status

from api.deps import CurrentSession, CurrentUser, Db
from schemas.household import MyHouseholdResponse
from schemas.notification import Preference, PreferencesUpdate
from schemas.user import PasswordChange, UserResponse, UserUpdate
from services import auth, households, notifications, users

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


@router.get("/households")
def list_my_households(user: CurrentUser, db: Db) -> list[MyHouseholdResponse]:
    return households.list_user_households(db, user)


@router.get("/notification-preferences")
def list_notification_preferences(user: CurrentUser, db: Db) -> list[Preference]:
    return notifications.list_preferences(db, user)


@router.put("/notification-preferences")
def update_notification_preferences(
    payload: PreferencesUpdate, user: CurrentUser, db: Db
) -> list[Preference]:
    return notifications.update_preferences(db, user, payload.preferences)
