import uuid
from typing import Annotated

from fastapi import Form, status

from api.deps import Db, KidMembership, household_router
from schemas.kid_task import KidSubmissionResponse, KidTaskResponse
from services import kid_tasks

router = household_router("/me/tasks", tags=["kid app"])

Note = Annotated[str | None, Form(max_length=500)]


@router.get("")
def list_tasks(membership: KidMembership, db: Db) -> list[KidTaskResponse]:
    return kid_tasks.list_tasks(db, membership)


@router.get("/{task_id}")
def get_task(task_id: uuid.UUID, membership: KidMembership, db: Db) -> KidTaskResponse:
    return kid_tasks.get_task(db, membership, task_id)


@router.post("/{task_id}/submissions", status_code=status.HTTP_201_CREATED)
def submit_task(
    task_id: uuid.UUID, membership: KidMembership, db: Db, note: Note = None
) -> KidSubmissionResponse:
    note = note.strip() if note else None
    return kid_tasks.submission_response(
        kid_tasks.submit(db, membership, task_id, note)
    )
