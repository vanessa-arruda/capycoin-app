from sqlalchemy.orm import Session

# Minimum points required to reach each level (index + 1 = level number)
LEVEL_THRESHOLDS = [0, 100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500]


def get_level(points: int) -> int:
    level = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if points >= threshold:
            level = i + 1
    return level


def get_child_points(child_id: int, db: Session) -> int:
    from models import ChildActivity
    from models.child_activity import ActivityStatus
    rows = (
        db.query(ChildActivity)
        .filter(
            ChildActivity.child_id == child_id,
            ChildActivity.status == ActivityStatus.approved,
        )
        .all()
    )
    total = 0
    for row in rows:
        pa = _get_parent_activity(row, db)
        total += pa.points_override if (pa and pa.points_override) else (
            row.activity.default_points if row.activity else 0
        )
    return total


def _get_parent_activity(child_activity, db):
    from models import ParentActivity
    return (
        db.query(ParentActivity)
        .filter(ParentActivity.activity_id == child_activity.activity_id)
        .first()
    )
