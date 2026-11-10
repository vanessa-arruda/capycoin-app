from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.errors import Conflict, InvalidInput
from models import User
from schemas.user import UserUpdate


def update_user(db: Session, user: User, changes: UserUpdate) -> User:
    fields = changes.model_fields_set
    if "display_name" in fields:
        if changes.display_name is None:
            raise InvalidInput("display_name cannot be empty")
        user.display_name = changes.display_name
    if "username" in fields:
        user.username = changes.username

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if "uq_users_username" in str(error.orig):
            raise Conflict("Username is already taken")
        if "ck_users_can_log_in" in str(error.orig):
            raise InvalidInput("A user without email needs a username")
        raise
    return user
