from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.db.models.agent import Agent as AgentDB
from app.db.models.user import User
from app.models.agent import AgentCreate, AgentConfigSchema
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from sqlalchemy.orm import load_only
from app.db.models.knowledge_base import agent_knowledge
from app.db.models.knowledge_base import KnowledgeBase  
from sqlalchemy.sql.expression import delete, insert
from typing import List
import logging
from app.db.database import SessionLocal
from app.db.models.chat import Conversation

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

# MJ: This file will contain all the database operations related to the Agent model

async def get_db():
    async with SessionLocal() as session:
        #SH: Explicit transaction start
        await session.begin()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise

async def get_agents(db: AsyncSession, user_id: int):
    
    #SH: Retrieve all agents for a specific user.
    try:
        result = await db.execute(select(AgentDB).where(AgentDB.user_id == user_id))
        return result.scalars().all()  
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RA01: An error occurred while retrieving agents"
        )

async def get_public_agent(db: AsyncSession, agent_id: int):
    #SH: Get agent without user verification for public access
    try:
        result = await db.execute(
            select(AgentDB)
            .options(load_only(
                AgentDB.id,
                AgentDB.name,
                AgentDB.description,
                AgentDB.model_name,
                AgentDB.system_prompt,
                AgentDB.config,
            ))
            .where(AgentDB.id == agent_id)
        )
        agent = result.scalars().first()

        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )

        return agent

    except SQLAlchemyError as e:
        #SH: Log this if needed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RA02: An error occurred while retrieving public agent {agent_id}"
        )

#SH: Get agent
async def get_agent(db: AsyncSession, agent_id: int, user_id: str):
    
    #SH: Retrieve a specific agent by ID for a specific user
    try:
        result = await db.execute(select(AgentDB).where((AgentDB.id == agent_id) & (AgentDB.user_id == user_id)))
        return result.scalars().first() 
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RA02: An error occurred while retrieving agent {agent_id}"
        )

#SH: Create agent
async def create_agent(
    db: AsyncSession, 
    agent: AgentCreate, 
    user_id: str,  
    current_user: User,
    knowledge_base_ids: List[int] = []
) -> AgentDB:
    
    #SH: Create a new agent with default configuration.
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User have not any organization. Please Create First organization."
        )
    try:
        db_agent = AgentDB(
            name=agent.name,
            description=agent.description,
            user_id=user_id,
            organization_id=current_user.organization_id,
            config=AgentConfigSchema().model_dump()
        )
        
        #SH: Link knowledge base
        if knowledge_base_ids:
            await validate_knowledge_access(db, knowledge_base_ids, current_user.organization_id)
            await update_agent_knowledge(db, db_agent.id, knowledge_base_ids)
        
        db.add(db_agent)
        await db.commit()
        await db.refresh(db_agent)
        return db_agent

    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Error in Agent creation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RA03: Database error while creating agent"
        )

def validate_agent_config(config: AgentConfigSchema):
    if config.context_window_size < 500 or config.context_window_size > 8000:
        raise HTTPException(
            status_code=400,
            detail="Context window size must be between 500 and 8000 tokens"
        )
    if config.response_throttling < 0 or config.response_throttling > 5:
        raise HTTPException(
            status_code=400,
            detail="Response throttling must be between 0 and 5 seconds"
        )
    if config.max_retries < 0 or config.max_retries > 5:
        raise HTTPException(
            status_code=400,
            detail="Max retries must be between 0 and 5"
        )

#SH: Update agent config
async def update_agent_config(
    db: AsyncSession, 
    agent_id: int, 
    config: AgentConfigSchema,
    user_id: str
) -> AgentDB:
    
    #SH: Update the configuration of an existing agent.
    try:
        validate_agent_config(config)

        #SH: Fetch the agent
        result = await db.execute(select(AgentDB).where(AgentDB.id == agent_id))
        db_agent = result.scalars().first()
        
        if not db_agent:
            logger.error(f"Agent with ID {agent_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found"
            )
        
        #SH: Verify user permission
        if db_agent.user_id != user_id:
            logger.error(f"User {user_id} does not have permission to update agent {agent_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this agent"
            )

        #SH: Validate the config
        if not isinstance(config, AgentConfigSchema):
            logger.error("Invalid config format")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid configuration format"
            )
        #SH: Update core config
        db_agent.model_name = config.model_name
        db_agent.temperature = config.temperature
        db_agent.max_length = config.max_length
        db_agent.system_prompt = config.system_prompt

        db_agent.context_window_size = config.context_window_size
        db_agent.response_throttling = config.response_throttling
        db_agent.domain_focus = config.domain_focus
        db_agent.enable_fallback = config.enable_fallback
        db_agent.max_retries = config.max_retries

        #SH: Update widget settings
        db_agent.greeting_message = config.greeting_message
        db_agent.theme_color = config.theme_color
        db_agent.embed_code = config.embed_code
        db_agent.is_public = config.is_public           
        db_agent.config = config.model_dump()

        if config.knowledge_base_ids:
            await validate_knowledge_access(db, config.knowledge_base_ids, db_agent.organization_id)
            await update_agent_knowledge(db, agent_id, config.knowledge_base_ids)

        #SH: Commit changes
        await db.commit()
        await db.refresh(db_agent)
        
        logger.info(f"Agent {agent_id} configuration updated successfully")
        return db_agent
    
    except HTTPException as e:
        logger.error(f"HTTPException in update_agent_config: {e.detail}")
        raise e
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError in update_agent_config: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RA04: Database error while updating agent configuration"
        )
    except Exception as e:
        logger.error(f"Unexpected error in update_agent_config: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RA04: Unexpected error while updating agent configuration"
        )

#SH: Validate knowledge access
async def validate_knowledge_access(db: AsyncSession, knowledge_ids: List[int], organization_id: int):
    #SH: Check all KBs belong to the same organization
    result = await db.execute(
        select(KnowledgeBase)
        .where(
            KnowledgeBase.id.in_(knowledge_ids),
            KnowledgeBase.organization_id == organization_id
        )
    )
    valid_kbs = result.scalars().all()
    if len(valid_kbs) != len(knowledge_ids):
        invalid_ids = set(knowledge_ids) - {kb.id for kb in valid_kbs}
        raise HTTPException(
            status_code=400,
            detail=f"Invalid knowledge base IDs for organization: {invalid_ids}"
        )

async def update_agent_knowledge(
    db: AsyncSession,
    agent_id: int,
    knowledge_ids: List[int]
):
    #SH: Clear existing associations
    await db.execute(delete(agent_knowledge).where(agent_knowledge.c.agent_id == agent_id))
    
    #SH: Add new associations
    if knowledge_ids:
        insert_stmt = insert(agent_knowledge).values([
            {"agent_id": agent_id, "knowledge_id": kb_id}
            for kb_id in knowledge_ids
        ])
        await db.execute(insert_stmt)
    
    await db.commit()
    
def validate_agent_config(config: AgentConfigSchema):
    # SH: Validate context window size
    if config.context_window_size < 500 or config.context_window_size > 8000:
        raise HTTPException(
            status_code=400,
            detail="Context window size must be between 500 and 8000 tokens"
        )
    
    # SH: Validate response throttling
    if config.response_throttling < 0 or config.response_throttling > 5:
        raise HTTPException(
            status_code=400,
            detail="Response throttling must be between 0 and 5 seconds"
        )
    
    # SH: Validate max retries
    if config.max_retries < 0 or config.max_retries > 5:
        raise HTTPException(
            status_code=400,
            detail="Max retries must be between 0 and 5"
        )

def validate_personality_traits(traits: List[str]):
    # Validate personality traits against allowed options
    allowed_traits = settings.PERSONALITY_TRAITS
    invalid = [t for t in traits if t not in allowed_traits]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid personality traits: {', '.join(invalid)}. Allowed: {', '.join(allowed_traits)}"
        )
        
async def generate_personality_preview(
    db: AsyncSession,
    agent_id: int,
    traits: List[str],
    custom_prompt: str,
    preview_prompt: str,
    user_id:str
) -> str:
    # SH:Generate personality preview response
    # Fetch agent
    agent = await get_agent(db, agent_id, user_id)
    
    # SH: Build system prompt
    traits_str = ", ".join(traits) if traits else "default"
    system_prompt = f"You are an AI assistant with {traits_str} personality traits."
    if custom_prompt:
        system_prompt += f"\nAdditional guidelines: {custom_prompt}"
    
    # SH: Generate preview - simplified example
    preview_response = f"Preview response for '{preview_prompt}' with traits: {traits_str}"
    
    # SH: Return preview response
    return preview_response