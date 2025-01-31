from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

# MJ: This is database model used for Migrations & CRUD operations
class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True) 
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    # SH:Update this column
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False) 
    
    # SH: Relationships
    owner = relationship("User", back_populates="agents") 
    organization = relationship("Organization", back_populates="agents")