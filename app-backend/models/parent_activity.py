from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class ParentActivity(Base):
    __tablename__ = "parent_activities"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id"))
    activity_id = Column(Integer, ForeignKey("activities.id"))
    points_override = Column(Integer, nullable=True)
    max_per_day = Column(Integer, nullable=True)
    max_per_week = Column(Integer, nullable=True)
    available_from = Column(DateTime, nullable=True)
    available_until = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    activity = relationship("Activity", back_populates="parent_links")
    parent = relationship("Parent", back_populates="parent_activities")
