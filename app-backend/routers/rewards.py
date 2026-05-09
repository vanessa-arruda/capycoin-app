from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import get_current_parent, get_current_child
from core.levels import get_child_points
from models import Reward, ChildReward, Parent, Child
from schemas.reward import RewardCreate, RewardRead, RedemptionRead, RedemptionReview

router = APIRouter(prefix="/rewards", tags=["rewards"])


@router.get("", response_model=list[RewardRead])
def list_rewards(
    db: Session = Depends(get_db),
    current_child: Child = Depends(get_current_child),
):
    return (
        db.query(Reward)
        .filter(
            Reward.household_id == current_child.household_id,
            Reward.is_active == True,
        )
        .all()
    )


@router.post("", response_model=RewardRead, status_code=201)
def create_reward(
    payload: RewardCreate,
    db: Session = Depends(get_db),
    current_parent: Parent = Depends(get_current_parent),
):
    reward = Reward(**payload.model_dump(), household_id=current_parent.household_id)
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return reward


@router.post("/{reward_id}/redeem", response_model=RedemptionRead, status_code=201)
def redeem_reward(
    reward_id: int,
    db: Session = Depends(get_db),
    current_child: Child = Depends(get_current_child),
):
    reward = db.query(Reward).filter(Reward.id == reward_id, Reward.is_active == True).first()
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")

    points = get_child_points(current_child.id, db)
    if points < reward.points_cost:
        raise HTTPException(status_code=400, detail="Not enough points to redeem this reward")

    redemption = ChildReward(child_id=current_child.id, reward_id=reward_id)
    db.add(redemption)
    db.commit()
    db.refresh(redemption)
    return redemption


@router.patch("/redemptions/{redemption_id}", response_model=RedemptionRead)
def review_redemption(
    redemption_id: int,
    payload: RedemptionReview,
    db: Session = Depends(get_db),
    current_parent: Parent = Depends(get_current_parent),
):
    redemption = db.query(ChildReward).filter(ChildReward.id == redemption_id).first()
    if not redemption:
        raise HTTPException(status_code=404, detail="Redemption not found")
    if payload.status not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=400, detail="Invalid status. Use APPROVED or REJECTED")
    redemption.status = payload.status
    redemption.approved_by = current_parent.id
    db.commit()
    db.refresh(redemption)
    return redemption
