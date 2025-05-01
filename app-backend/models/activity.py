from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from core.database import Base


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    default_points = Column(Integer, default=0)
    parent_links = relationship("ParentActivity", backref="activity")
