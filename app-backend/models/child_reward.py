from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class ChildReward(Base):
    __tablename__ = "child_rewards"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id"))
    reward_id = Column(Integer, ForeignKey("rewards.id"))
    status = Column(String, default="PENDING")  # PENDING, APPROVED, REJECTED
    redeemed_at = Column(DateTime, default=datetime.now)
    approved_by = Column(Integer, ForeignKey("parents.id"), nullable=True)

    child = relationship("Child", back_populates="rewards")
    reward = relationship("Reward", back_populates="redemptions")
    approver = relationship("Parent", foreign_keys=[approved_by])
