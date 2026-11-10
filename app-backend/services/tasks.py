import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core import clock
from core.errors import Conflict, InvalidInput, NotFound
from models import HouseholdMember, Task, TaskAssignment
from schemas.common import Page, PageParams
from schemas.task import TaskCreate, TaskResponse, TaskUpdate
from services import kids
from services.pagination import paginate

TASK_NOT_FOUND = "Task not found"
# Fields that can't be removed; description and due_at can be set to null.
REQUIRED_FIELDS = ("title", "reward", "recurrence", "starts_on", "kid_ids")


def task_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        reward=task.reward,
        recurrence=task.recurrence,
        starts_on=task.starts_on,
        due_at=task.due_at,
        archived_at=task.archived_at,
        kid_ids=sorted(a.kid_id for a in task.assignments),
        created_by=task.created_by,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def list_tasks(
    db: Session,
    household_id: uuid.UUID,
    page: PageParams,
    kid_id: uuid.UUID | None = None,
    archived: bool = False,
) -> Page[TaskResponse]:
    query = (
        select(Task)
        .where(
            Task.household_id == household_id,
            Task.archived_at.is_not(None) if archived else Task.archived_at.is_(None),
        )
        .options(selectinload(Task.assignments))
    )
    if kid_id is not None:
        query = query.where(Task.assignments.any(TaskAssignment.kid_id == kid_id))
    tasks, next_before = paginate(db, query, Task.id, page)
    return Page(items=[task_response(t) for t in tasks], next_before=next_before)


def get_task(db: Session, household_id: uuid.UUID, task_id: uuid.UUID) -> Task:
    task = db.scalar(
        select(Task)
        .where(Task.id == task_id, Task.household_id == household_id)
        .options(selectinload(Task.assignments))
    )
    if task is None:
        raise NotFound(TASK_NOT_FOUND)
    return task


def _check_due_at(starts_on: date, due_at: datetime | None, timezone: str) -> None:
    if due_at is not None and due_at.astimezone(ZoneInfo(timezone)).date() < starts_on:
        raise InvalidInput("due_at must not be before starts_on")


def create_task(db: Session, parent: HouseholdMember, data: TaskCreate) -> Task:
    household = parent.household
    kid_ids = list(dict.fromkeys(data.kid_ids))
    kids.check_kid_ids(db, household.id, kid_ids)
    _check_due_at(data.starts_on, data.due_at, household.timezone)

    task = Task(
        household_id=household.id,
        created_by=parent.user_id,
        title=data.title,
        description=data.description or None,
        reward=data.reward,
        recurrence=data.recurrence,
        starts_on=data.starts_on,
        due_at=data.due_at,
        assignments=[TaskAssignment(kid_id=kid_id) for kid_id in kid_ids],
    )
    db.add(task)
    db.commit()
    return task


def update_task(
    db: Session, parent: HouseholdMember, task_id: uuid.UUID, changes: TaskUpdate
) -> Task:
    household = parent.household
    task = get_task(db, household.id, task_id)
    if task.archived_at is not None:
        raise Conflict("Archived tasks cannot be changed")
    fields = changes.model_fields_set
    for field in REQUIRED_FIELDS:
        if field in fields and getattr(changes, field) is None:
            raise InvalidInput(f"{field} cannot be empty")
    # Check everything before changing the task, so a 422 leaves it untouched.
    values = changes.model_dump(include=fields - {"kid_ids"})
    _check_due_at(
        values.get("starts_on", task.starts_on),
        values.get("due_at", task.due_at),
        household.timezone,
    )
    if "kid_ids" in fields:
        kid_ids = list(dict.fromkeys(changes.kid_ids))
        kids.check_kid_ids(db, household.id, kid_ids)

    if "description" in values:
        values["description"] = values["description"] or None
    for field, value in values.items():
        setattr(task, field, value)
    if "kid_ids" in fields:
        _replace_assignments(task, kid_ids)
    db.commit()
    return task


def _replace_assignments(task: Task, kid_ids: list[uuid.UUID]) -> None:
    # Keep existing rows; deleting and re-adding the same key in one flush fails.
    task.assignments = [a for a in task.assignments if a.kid_id in kid_ids]
    assigned = {a.kid_id for a in task.assignments}
    task.assignments.extend(
        TaskAssignment(kid_id=kid_id) for kid_id in kid_ids if kid_id not in assigned
    )


def archive_task(db: Session, household_id: uuid.UUID, task_id: uuid.UUID) -> None:
    task = get_task(db, household_id, task_id)
    if task.archived_at is None:
        task.archived_at = clock.now()
        db.commit()
