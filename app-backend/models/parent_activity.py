from sqlalchemy import Column, Integer, ForeignKey
from core.database import Base


class ParentActivity(Base):
    __tablename__ = "parent_activities"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id"))
    activity_id = Column(Integer, ForeignKey("activities.id"))
