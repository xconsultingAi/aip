from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.database import Base

# SH: This is database model used for Migrations & CRUD operations
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    name = Column(String, nullable=False) 
    user_id = Column(String, nullable=False)
    # SH:Relationships with user and agent table
    users = relationship("User", back_populates="organization") 
    agents = relationship("Agent", back_populates="organization")
    