from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class Reward(Base):
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    points_cost = Column(Integer, nullable=False)
    household_id = Column(Integer, ForeignKey("households.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    household = relationship("Household", back_populates="rewards")
    redemptions = relationship("ChildReward", back_populates="reward")
