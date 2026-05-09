from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from core.database import get_db
from core.auth import get_current_parent, get_current_child
from models import Activity, ParentActivity, ChildActivity, Parent, Child
from models.child_activity import ActivityStatus
from schemas.activity import (
    ActivityCreate, ActivityRead,
    ParentActivityConfig, ParentActivityRead,
    ChildActivityCreate, ChildActivityRead,
    ReviewRequest, PendingReviewRead,
)

router = APIRouter(tags=["activities"])


@router.get("/activities", response_model=list[ActivityRead])
def list_activities(db: Session = Depends(get_db)):
    return db.query(Activity).all()


@router.post("/activities", response_model=ActivityRead, status_code=201)
def create_activity(
    payload: ActivityCreate,
    db: Session = Depends(get_db),
    _: Parent = Depends(get_current_parent),
):
    activity = Activity(**payload.model_dump())
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@router.post("/activities/{activity_id}/enable", response_model=ParentActivityRead)
def enable_activity(
    activity_id: int,
    config: ParentActivityConfig,
    db: Session = Depends(get_db),
    current_parent: Parent = Depends(get_current_parent),
):
    if not db.query(Activity).filter(Activity.id == activity_id).first():
        raise HTTPException(status_code=404, detail="Activity not found")

    pa = db.query(ParentActivity).filter(
        ParentActivity.parent_id == current_parent.id,
        ParentActivity.activity_id == activity_id,
    ).first()

    if pa:
        for key, value in config.model_dump(exclude_none=True).items():
            setattr(pa, key, value)
        pa.is_active = True
    else:
        pa = ParentActivity(
            parent_id=current_parent.id,
            activity_id=activity_id,
            is_active=True,
            **config.model_dump(exclude_none=True),
        )
        db.add(pa)

    db.commit()
    db.refresh(pa)
    return pa


@router.post("/activities/{activity_id}/disable", response_model=ParentActivityRead)
def disable_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_parent: Parent = Depends(get_current_parent),
):
    pa = db.query(ParentActivity).filter(
        ParentActivity.parent_id == current_parent.id,
        ParentActivity.activity_id == activity_id,
    ).first()
    if not pa:
        raise HTTPException(status_code=404, detail="Activity not enabled")
    pa.is_active = False
    db.commit()
    db.refresh(pa)
    return pa


@router.get("/child-activities/pending", response_model=list[PendingReviewRead])
def get_pending_reviews(
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
):
    child_ids = [c.id for c in current_parent.children]
    pending = (
        db.query(ChildActivity)
        .filter(
            ChildActivity.child_id.in_(child_ids),
            ChildActivity.status == ActivityStatus.pending,
            ChildActivity.submitted_at.isnot(None),
        )
        .all()
    )
    return [
        PendingReviewRead(
            id=ca.id,
            child_name=ca.child.name,
            activity_name=ca.activity.name,
            submitted_at=ca.submitted_at,
        )
        for ca in pending
    ]


@router.post("/child-activities", response_model=ChildActivityRead, status_code=201)
def pick_activity(
    payload: ChildActivityCreate,
    db: Session = Depends(get_db),
    current_child: Child = Depends(get_current_child),
):
    pa = db.query(ParentActivity).filter(
        ParentActivity.activity_id == payload.activity_id,
        ParentActivity.is_active == True,
    ).first()
    if not pa:
        raise HTTPException(status_code=404, detail="Activity not available")

    child_activity = ChildActivity(
        child_id=current_child.id,
        activity_id=payload.activity_id,
    )
    db.add(child_activity)
    db.commit()
    db.refresh(child_activity)
    return child_activity


@router.post("/child-activities/{child_activity_id}/submit", response_model=ChildActivityRead)
def submit_activity(
    child_activity_id: int,
    db: Session = Depends(get_db),
    current_child: Child = Depends(get_current_child),
):
    ca = db.query(ChildActivity).filter(
        ChildActivity.id == child_activity_id,
        ChildActivity.child_id == current_child.id,
    ).first()
    if not ca:
        raise HTTPException(status_code=404, detail="Activity not found")
    if ca.submitted_at is not None:
        raise HTTPException(status_code=400, detail="Activity already submitted")
    ca.submitted_at = datetime.now()
    db.commit()
    db.refresh(ca)
    return ca


@router.patch("/child-activities/{child_activity_id}/review", response_model=ChildActivityRead)
def review_activity(
    child_activity_id: int,
    payload: ReviewRequest,
    db: Session = Depends(get_db),
    current_parent: Parent = Depends(get_current_parent),
):
    ca = db.query(ChildActivity).filter(ChildActivity.id == child_activity_id).first()
    if not ca:
        raise HTTPException(status_code=404, detail="Activity not found")
    try:
        ca.status = ActivityStatus(payload.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status. Use APPROVED or REJECTED")
    ca.reviewed_at = datetime.now()
    ca.reviewed_by = current_parent.id
    db.commit()
    db.refresh(ca)
    return ca
