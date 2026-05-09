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
    from models import ChildActivity, ChildReward, ParentActivity
    from models.child_activity import ActivityStatus

    approved_activities = (
        db.query(ChildActivity)
        .filter(
            ChildActivity.child_id == child_id,
            ChildActivity.status == ActivityStatus.approved,
        )
        .all()
    )

    earned = 0
    for row in approved_activities:
        pa = db.query(ParentActivity).filter(
            ParentActivity.activity_id == row.activity_id
        ).first()
        earned += pa.points_override if (pa and pa.points_override) else (
            row.activity.default_points if row.activity else 0
        )

    approved_redemptions = (
        db.query(ChildReward)
        .filter(
            ChildReward.child_id == child_id,
            ChildReward.status == "APPROVED",
        )
        .all()
    )
    spent = sum(r.reward.points_cost for r in approved_redemptions if r.reward)

    return max(0, earned - spent)
