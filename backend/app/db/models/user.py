from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

# MJ: This is the database model used for Migrations & CRUD operations
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True) 
    # SH: Organization_id 
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False) 
    
    # SH: Relationships with agent and organization table
    organization = relationship("Organization", back_populates="users")
    agents = relationship("Agent", back_populates="owner")