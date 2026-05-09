from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import get_current_parent
from core.levels import get_child_points, get_level
from models import Parent
from schemas.parent import ParentRead
from schemas.child import ChildSummary

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
