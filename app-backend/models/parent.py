from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base


class Parent(Base):
    __tablename__ = "parents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    household_id = Column(Integer, ForeignKey("households.id"))

    household = relationship("Household", back_populates="parents")
    children = relationship("Child", back_populates="parent", overlaps="household")
    activities = relationship("Activity", back_populates="parent", overlaps="household")
