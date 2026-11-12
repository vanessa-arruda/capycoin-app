import uuid
from typing import Annotated

from fastapi import Depends, File, Form, UploadFile, status

from api.deps import Db, KidMembership, household_router
from core.storage import PhotoStore, get_photo_store
from schemas.kid_task import KidSubmissionResponse, KidTaskResponse
from services import kid_tasks, photos

router = household_router("/me/tasks", tags=["kid app"])

Note = Annotated[str | None, Form(max_length=500)]
Photo = Annotated[UploadFile | None, File()]


@router.get("")
def list_tasks(membership: KidMembership, db: Db) -> list[KidTaskResponse]:
    return kid_tasks.list_tasks(db, membership)


@router.get("/{task_id}")
def get_task(task_id: uuid.UUID, membership: KidMembership, db: Db) -> KidTaskResponse:
    return kid_tasks.get_task(db, membership, task_id)


@router.post("/{task_id}/submissions", status_code=status.HTTP_201_CREATED)
def submit_task(
    task_id: uuid.UUID,
    membership: KidMembership,
    db: Db,
    store: Annotated[PhotoStore, Depends(get_photo_store)],
    note: Note = None,
    photo: Photo = None,
) -> KidSubmissionResponse:
    note = note.strip() if note else None
    data = photos.read_upload(photo.file) if photo else None
    return kid_tasks.submission_response(
        kid_tasks.submit(db, membership, task_id, note, data, store)
    )
