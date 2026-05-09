from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import get_current_parent
from core.levels import get_child_points, get_level
from models import Parent, ParentActivity
from schemas.parent import ParentRead
from schemas.child import ChildSummary
from schemas.activity import ParentActivityRead
from schemas.reward import RewardRead, PendingRedemptionRead
from models import Reward, ChildReward

router = APIRouter(prefix="/parents", tags=["parents"])


@router.get("/me", response_model=ParentRead)
def get_me(current_parent: Parent = Depends(get_current_parent)):
    return current_parent


@router.get("/me/children", response_model=list[ChildSummary])
def get_children(
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
):
    result = []
    for child in current_parent.children:
        points = get_child_points(child.id, db)
        result.append(
            ChildSummary(
                id=child.id,
                name=child.name,
                avatar=child.avatar,
                points_total=points,
                level=get_level(points),
            )
        )
    return result


@router.get("/me/activities", response_model=list[ParentActivityRead])
def get_parent_activities(
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
):
    return db.query(ParentActivity).filter(ParentActivity.parent_id == current_parent.id).all()


@router.get("/me/rewards", response_model=list[RewardRead])
def get_parent_rewards(
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
):
    return db.query(Reward).filter(Reward.household_id == current_parent.household_id).all()


@router.get("/me/redemptions/pending", response_model=list[PendingRedemptionRead])
def get_pending_redemptions(
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
):
    child_ids = [c.id for c in current_parent.children]
    pending = (
        db.query(ChildReward)
        .filter(ChildReward.child_id.in_(child_ids), ChildReward.status == "PENDING")
        .all()
    )
    return [
        PendingRedemptionRead(
            id=r.id,
            child_name=r.child.name,
            reward_name=r.reward.name,
            points_cost=r.reward.points_cost,
            redeemed_at=r.redeemed_at,
        )
        for r in pending
    ]
