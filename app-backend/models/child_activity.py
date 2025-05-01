from sqlalchemy import Column, Integer, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from core.database import Base


class ActivityStatus(str, enum.Enum):
    pending = "PENDING"
    approved = "APPROVED"
    rejected = "REJECTED"


class ChildActivity(Base):
    __tablename__ = "child_activities"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"))
    activity_id = Column(Integer, ForeignKey("activities.id"))
    status = Column(Enum(ActivityStatus), default=ActivityStatus.pending)

    picked_at = Column(DateTime, default=datetime.now)  # when kid starts it
    submitted_at = Column(DateTime, nullable=True)  # when kid marks it done
    reviewed_at = Column(DateTime, nullable=True)  # when parent reviewed
    reviewed_by = Column(Integer, ForeignKey("parents.id"), nullable=True)  # parent ID

    child = relationship("Child", back_populates="activities")
    activity = relationship("Activity")
    reviewer = relationship("Parent", foreign_keys=[reviewed_by])
