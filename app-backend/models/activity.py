from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    default_points = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=True, default=datetime.now)
    parent_links = relationship("ParentActivity", backref="activity")
