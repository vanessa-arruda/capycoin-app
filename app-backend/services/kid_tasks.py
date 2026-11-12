"""The kid's side of tasks: what to do now, and marking it done."""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from core import clock
from core.errors import Conflict, NotFound
from core.storage import PhotoStore
from models import HouseholdMember, Task, TaskAssignment, TaskSubmission
from models.enums import NotificationType, Recurrence, ReviewStatus
from schemas.kid_task import KidSubmissionResponse, KidTaskResponse
from services import notifications, photos, rate_limits
from services.tasks import TASK_NOT_FOUND

ALREADY_SUBMITTED = "This task is already done or waiting for a parent"
# Order of the kid's list: to do, then waiting for a parent, then done.
STATUS_ORDER = {None: 0, ReviewStatus.DENIED: 0, ReviewStatus.PENDING: 1}


@dataclass(frozen=True)
class Period:
    start: date
    end: date | None


def household_today(timezone: str) -> date:
    return clock.now().astimezone(ZoneInfo(timezone)).date()


def current_period(task: Task, today: date) -> Period:
    match task.recurrence:
        case Recurrence.DAILY:
            return Period(today, today)
        case Recurrence.WEEKLY:
            monday = today - timedelta(days=today.weekday())
            return Period(monday, monday + timedelta(days=6))
        case Recurrence.MONTHLY:
            first = today.replace(day=1)
            next_month = (first + timedelta(days=32)).replace(day=1)
            return Period(first, next_month - timedelta(days=1))
    return Period(task.starts_on, None)


def _kid_tasks(kid: HouseholdMember):
    return (
        select(Task)
        .join(TaskAssignment)
        .where(
            Task.household_id == kid.household_id,
            Task.archived_at.is_(None),
            TaskAssignment.kid_id == kid.user_id,
        )
    )


def _in_period(task: Task, period: Period):
    # A one-off task has a single period, so all its submissions count, even
    # ones made before a parent moved starts_on.
    if task.recurrence == Recurrence.NONE:
        return TaskSubmission.task_id == task.id
    return and_(
        TaskSubmission.task_id == task.id, TaskSubmission.period_start == period.start
    )


def _latest_submissions(
    db: Session, kid_id: uuid.UUID, periods: Iterable[tuple[Task, Period]]
) -> dict[uuid.UUID, TaskSubmission]:
    conditions = [_in_period(task, period) for task, period in periods]
    if not conditions:
        return {}
    rows = db.scalars(
        select(TaskSubmission)
        .where(TaskSubmission.kid_id == kid_id, or_(*conditions))
        .options(joinedload(TaskSubmission.reviewer))
        .order_by(TaskSubmission.id)
    )
    # Ids are UUIDv7, so the last one per task is the latest.
    return {row.task_id: row for row in rows}


def submission_response(submission: TaskSubmission) -> KidSubmissionResponse:
    reviewer = submission.reviewer
    return KidSubmissionResponse(
        id=submission.id,
        status=submission.status,
        note=submission.note,
        has_photo=submission.photo_path is not None,
        submitted_at=submission.submitted_at,
        reviewed_at=submission.reviewed_at,
        review_note=submission.review_note,
        reviewed_by_name=reviewer.display_name if reviewer else None,
    )


def task_response(
    task: Task, period: Period, submission: TaskSubmission | None
) -> KidTaskResponse:
    return KidTaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        reward=task.reward,
        recurrence=task.recurrence,
        starts_on=task.starts_on,
        due_at=task.due_at,
        period_start=period.start,
        period_end=period.end,
        submission=submission_response(submission) if submission else None,
    )


def _is_listed(task: Task, submission: TaskSubmission | None, today: date) -> bool:
    if task.starts_on > today:
        return False
    ended = task.due_at is not None and task.due_at <= clock.now()
    if task.recurrence != Recurrence.NONE:
        return not ended
    status = submission.status if submission else None
    if status == ReviewStatus.APPROVED:
        return False
    return not ended or status == ReviewStatus.PENDING


def _sort_key(item: KidTaskResponse):
    status = item.submission.status if item.submission else None
    return (
        STATUS_ORDER.get(status, 2),
        item.due_at is None,
        item.due_at.timestamp() if item.due_at else 0,
        item.title,
        item.id,
    )


def list_tasks(db: Session, kid: HouseholdMember) -> list[KidTaskResponse]:
    today = household_today(kid.household.timezone)
    tasks = db.scalars(_kid_tasks(kid).where(Task.starts_on <= today)).all()
    periods = [(task, current_period(task, today)) for task in tasks]
    latest = _latest_submissions(db, kid.user_id, periods)
    items = [
        task_response(task, period, latest.get(task.id))
        for task, period in periods
        if _is_listed(task, latest.get(task.id), today)
    ]
    return sorted(items, key=_sort_key)


def _get_task(db: Session, kid: HouseholdMember, task_id: uuid.UUID) -> Task:
    task = db.scalar(_kid_tasks(kid).where(Task.id == task_id))
    if task is None:
        raise NotFound(TASK_NOT_FOUND)
    return task


def get_task(db: Session, kid: HouseholdMember, task_id: uuid.UUID) -> KidTaskResponse:
    task = _get_task(db, kid, task_id)
    period = current_period(task, household_today(kid.household.timezone))
    latest = _latest_submissions(db, kid.user_id, [(task, period)])
    return task_response(task, period, latest.get(task.id))


def submit(
    db: Session,
    kid: HouseholdMember,
    task_id: uuid.UUID,
    note: str | None,
    photo: bytes | None,
    store: PhotoStore,
) -> TaskSubmission:
    task = _get_task(db, kid, task_id)
    today = household_today(kid.household.timezone)
    if task.starts_on > today:
        raise Conflict("This task has not started yet")
    if task.due_at is not None and task.due_at <= clock.now():
        raise Conflict("This task is past its due time")
    period = current_period(task, today)
    active = db.scalar(
        select(TaskSubmission.id).where(
            TaskSubmission.kid_id == kid.user_id,
            TaskSubmission.status != ReviewStatus.DENIED,
            _in_period(task, period),
        )
    )
    if active is not None:
        raise Conflict(ALREADY_SUBMITTED)
    if photo is not None:
        rate_limits.hit(db, rate_limits.PHOTO_UPLOADS_PER_KID, str(kid.user_id))
        photo = photos.clean(photo)

    submission = TaskSubmission(
        task_id=task.id,
        kid_id=kid.user_id,
        period_start=period.start,
        note=note or None,
        submitted_at=clock.now(),
    )
    db.add(submission)
    try:
        db.flush()
    except IntegrityError:
        # Another request for the same period got in first.
        db.rollback()
        raise Conflict(ALREADY_SUBMITTED)

    if photo is not None:
        submission.photo_path = photos.path_for(kid.household_id, submission.id)
        store.save(submission.photo_path, photo)
    notifications.notify_parents(
        db,
        kid.household_id,
        NotificationType.TASK_SUBMITTED,
        task_submission_id=submission.id,
    )
    try:
        db.commit()
    except Exception:
        if submission.photo_path is not None:
            store.delete([submission.photo_path])
        raise
    return submission
