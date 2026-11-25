from sqlalchemy import delete, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.errors import Conflict, InvalidInput
from core.storage import PhotoStore
from models import Household, HouseholdMember, User
from schemas.user import UserUpdate
from services import households


def update_user(db: Session, user: User, changes: UserUpdate) -> User:
    fields = changes.model_fields_set
    if "display_name" in fields:
        if changes.display_name is None:
            raise InvalidInput("display_name cannot be empty")
        user.display_name = changes.display_name
    if "username" in fields:
        user.username = changes.username

    commit_user_changes(db)
    return user


def commit_user_changes(db: Session) -> None:
    """Commit, turning username and login constraint errors into API errors."""
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if "uq_users_username" in str(error.orig):
            raise Conflict("Username is already taken")
        if "uq_users_email" in str(error.orig):
            raise Conflict("Email is already in use")
        if "ck_users_can_log_in" in str(error.orig):
            raise InvalidInput("A user without email needs a username and a password")
        raise


def delete_account(
    db: Session, user: User, confirm_household_names: list[str], store: PhotoStore
) -> None:
    """Delete a parent's account.

    A household where the parent is admin and the only member is deleted with
    the account, once its name is confirmed. Admins of households with other
    members must delete the household or remove the members first.
    """
    admin_of = db.scalars(
        select(Household)
        .join(HouseholdMember)
        .where(HouseholdMember.user_id == user.id, HouseholdMember.is_admin)
        .order_by(Household.name, Household.id)
    ).all()
    for household in admin_of:
        others = select(HouseholdMember).where(
            HouseholdMember.household_id == household.id,
            HouseholdMember.user_id != user.id,
        )
        if db.scalar(select(exists(others))):
            raise Conflict(
                f'You are the admin of "{household.name}", which has other members. '
                "Delete the household or remove its members first."
            )
    unconfirmed = [h.name for h in admin_of if h.name not in confirm_household_names]
    if unconfirmed:
        names = ", ".join(f'"{name}"' for name in unconfirmed)
        raise InvalidInput(
            f"Confirm the names of the households deleted with your account: {names}"
        )

    photo_paths = []
    for household in admin_of:
        photo_paths += households.delete_household_rows(db, household.id)
    # Sessions, memberships and notifications go with the user (ON DELETE CASCADE).
    db.execute(delete(User).where(User.id == user.id))
    db.commit()
    store.delete(photo_paths)
