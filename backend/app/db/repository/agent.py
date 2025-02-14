from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models.agent import Agent as AgentDB
from app.models.agent import AgentCreate, AgentConfigSchema
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from app.models.agent import AgentOut
from app.db.models.organization import Organization

#MJ: This file will contain all the database operations related to the Agent model

async def get_agents(db: AsyncSession, user_id: int):
    try:
        result = await db.execute(select(AgentDB).where(AgentDB.user_id == user_id))
        return result.scalars().all()  
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RA01: An error occurred while retrieving agents"
        )

async def get_agent(db: AsyncSession, agent_id: int, user_id: int):
    try:
        result = await db.execute(select(AgentDB).where((AgentDB.id == agent_id) & (AgentDB.user_id == user_id)))
        return result.scalars().first() 
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RA02: An error occurred while retrieving agent {agent_id}"
        )

async def create_agent(db: AsyncSession, agent: AgentCreate, user_id: int, organization_id: int) -> AgentDB:
    try:
        db_agent = AgentDB(
            name=agent.name,
            description=agent.description,
            user_id=user_id,
            organization_id=int(agent.organization_id),
            
            #SH: For model configuration
            model_name=agent.config.model_name,
            temperature=agent.config.temperature,
            max_length=agent.config.max_length,
            system_prompt=agent.config.system_prompt,
            config=agent.config.model_dump()
        )
        
        db.add(db_agent)
        await db.commit()
        await db.refresh(db_agent)
        return db_agent
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RA03: An error occurred creating new agent"
        )

async def update_agent_config(db: AsyncSession, agent_id: int, config: AgentConfigSchema):
    agent = await db.get(AgentDB, agent_id)
    agent.config = config.model_dump()
    await db.commit()
    return agent
