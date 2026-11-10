import uuid

from fastapi import status

from api.deps import Db, Pagination, ParentMembership, household_router
from schemas.common import Page
from schemas.task import TaskCreate, TaskResponse, TaskUpdate
from services import tasks

router = household_router("/tasks", tags=["tasks"])


@router.get("")
def list_tasks(
    membership: ParentMembership,
    db: Db,
    page: Pagination,
    kid_id: uuid.UUID | None = None,
    archived: bool = False,
) -> Page[TaskResponse]:
    return tasks.list_tasks(db, membership.household_id, page, kid_id, archived)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, membership: ParentMembership, db: Db) -> TaskResponse:
    return tasks.task_response(tasks.create_task(db, membership, data))


@router.get("/{task_id}")
def get_task(task_id: uuid.UUID, membership: ParentMembership, db: Db) -> TaskResponse:
    return tasks.task_response(tasks.get_task(db, membership.household_id, task_id))


@router.patch("/{task_id}")
def update_task(
    task_id: uuid.UUID, changes: TaskUpdate, membership: ParentMembership, db: Db
) -> TaskResponse:
    return tasks.task_response(tasks.update_task(db, membership, task_id, changes))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_task(task_id: uuid.UUID, membership: ParentMembership, db: Db) -> None:
    tasks.archive_task(db, membership.household_id, task_id)
