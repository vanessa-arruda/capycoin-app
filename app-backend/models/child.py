from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base


class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("parents.id"))

    household_id = Column(Integer, ForeignKey("households.id"))

    parent = relationship("Parent", back_populates="children")
