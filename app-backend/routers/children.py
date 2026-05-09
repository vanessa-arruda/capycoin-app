from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import get_current_child
from core.levels import get_child_points, get_level
from models import Child
from schemas.child import ChildRead
from schemas.activity import ChildActivityRead
from schemas.reward import RedemptionRead

router = APIRouter(prefix="/children", tags=["children"])


@router.get("/me", response_model=ChildRead)
def get_me(
    current_child: Child = Depends(get_current_child),
    db: Session = Depends(get_db),
):
    points = get_child_points(current_child.id, db)
    return ChildRead(
        id=current_child.id,
        name=current_child.name,
        email=current_child.email,
        avatar=current_child.avatar,
        household_id=current_child.household_id,
        points_total=points,
        level=get_level(points),
    )


@router.get("/me/activities", response_model=list[ChildActivityRead])
def get_activities(current_child: Child = Depends(get_current_child)):
    return current_child.activities


@router.get("/me/rewards", response_model=list[RedemptionRead])
def get_rewards(current_child: Child = Depends(get_current_child)):
    return current_child.rewards
