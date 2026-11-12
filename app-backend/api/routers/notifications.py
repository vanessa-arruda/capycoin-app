import uuid

from fastapi import APIRouter, status

from api.deps import CurrentUser, Db, Pagination
from schemas.common import Page
from schemas.notification import NotificationResponse, ReadAll
from services import notifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    user: CurrentUser,
    db: Db,
    page: Pagination,
    household_id: uuid.UUID | None = None,
    unread: bool = False,
) -> Page[NotificationResponse]:
    return notifications.list_notifications(db, user, page, household_id, unread)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(user: CurrentUser, db: Db, payload: ReadAll | None = None) -> None:
    notifications.mark_all_read(db, user, payload.household_id if payload else None)


@router.get("/{notification_id}")
def get_notification(
    notification_id: uuid.UUID, user: CurrentUser, db: Db
) -> NotificationResponse:
    return notifications.notification_response(
        notifications.get_notification(db, user, notification_id)
    )


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(notification_id: uuid.UUID, user: CurrentUser, db: Db) -> None:
    notifications.mark_read(db, user, notification_id)
