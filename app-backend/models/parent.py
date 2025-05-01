from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from core.database import Base


class Parent(Base):
    __tablename__ = "parents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    children = relationship("Child", back_populates="parent")
    activity_links = relationship("ParentActivity", backref="parent")
