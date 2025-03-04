from fastapi import APIRouter, status, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.responses import success_response, error_response
from app.dependencies.auth import get_current_user
from app.models.agent import AgentCreate, AgentOut, ALLOWED_MODELS, AgentConfigSchema
from app.models.knowledge_base import KnowledgeBaseCreate, KnowledgeLinkRequest
from app.db.repository.agent import get_agents, get_agent, create_agent, update_agent_config
from app.db.repository.knowledge_base import create_knowledge_entry, get_agent_knowledge
from app.services.llm_services import generate_llm_response
from app.db.database import get_db
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models.user import UserOut as User
from sqlalchemy import select
from app.db.models.agent import Agent
from app.db.models.knowledge_base import KnowledgeBase



# MJ: This is our Main Router for all the routes related to Agents

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    dependencies=[Depends(get_current_user)] # MJ: Ensure secure routes for agents
)

@router.get("/", response_model=list[AgentOut])
async def read_agents(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
    agents = await get_agents(db, current_user.user_id)
    
    if not agents:
        return error_response(message="No agents found", http_status=status.HTTP_404_NOT_FOUND)
    
    # Convert to Pydantic model
    agents_out = [AgentOut.model_validate(agent.__dict__) for agent in agents]  
    return success_response("Agents retrieved successfully", data=agents_out)
@router.get("/{agent_id}", response_model=AgentOut)
async def read_agent(
        agent_id: int, 
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
    agent = await get_agent(db, agent_id, current_user.user_id) 
    if not agent:
        return error_response(
            message=f"Agent with ID {agent_id} not found",
            http_status=status.HTTP_404_NOT_FOUND
        )
    # Convert SQLAlchemy object to Pydantic model
    return AgentOut.model_validate(agent, from_attributes=True)
       
@router.post("/", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_new_agent(
    agent: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new agent with default configuration.
    """
    try:
        new_agent = await create_agent(
            db=db,
            agent=agent,
            user_id=current_user.user_id,
            current_user=current_user 
        )        
        agent_dict = new_agent.__dict__
        agent_dict.pop('_sa_instance_state', None)  
        return success_response(
            "Agent created successfully",
            AgentOut(**agent_dict)
        )
    
    except IntegrityError:
        return error_response(
            message="An agent with the same details already exists.",
            http_status=status.HTTP_400_BAD_REQUEST
        )
    except SQLAlchemyError:
        return error_response(
            message="An unexpected error occurred while creating the agent.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception:
        return error_response(
            message="An unexpected error occurred.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# agent configuration
@router.put("/{agent_id}/config", response_model=AgentOut)
async def update_agent_configuration(
    agent_id: int,
    config: AgentConfigSchema = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the configuration of an existing agent.
    """
    # Validate configuration
    if config.model_name not in ALLOWED_MODELS:
        return error_response(
            message=f"Invalid model selected. Allowed models: {ALLOWED_MODELS}",
            http_status=status.HTTP_400_BAD_REQUEST
        )
    if not (0 <= config.temperature <= 1):
        return error_response(
            message="Temperature must be between 0 and 1",
            http_status=status.HTTP_400_BAD_REQUEST
        )
    if config.max_length <= 0:
        return error_response(
            message="Max length must be greater than 0",
            http_status=status.HTTP_400_BAD_REQUEST
        )
    
    # validation for knowledge base IDs
    if config.knowledge_base_ids:
        result = await db.execute(
            select(KnowledgeBase.id).where(KnowledgeBase.id.in_(config.knowledge_base_ids))
        )
        existing_ids = result.scalars().all()
        if len(existing_ids) != len(config.knowledge_base_ids):
            return error_response("Invalid knowledge base IDs", 400)
    
    try:
        # agent configuration
        updated_agent = await update_agent_config(
            db=db,
            agent_id=agent_id,
            config=config,
            user_id=current_user.user_id
        )

        agent_dict = updated_agent.__dict__
        agent_dict.pop('_sa_instance_state', None)  
        
        return success_response(
            "Agent configuration updated successfully",
            AgentOut(**agent_dict)
        )
    
    except HTTPException as e:
        return error_response(e.detail, e.status_code)
    except Exception:
        return error_response(
            message="An unexpected error occurred.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
@router.post("/{agent_id}/chat")
async def chat_with_agent(
    agent_id: int,
    prompt: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Fetch agent
    agent = await get_agent(db, agent_id, current_user.user_id)
    if not agent:
        return error_response("Agent not found", status.HTTP_404_NOT_FOUND)

    # load the knowledge_bases relationship
    await db.refresh(agent, ["knowledge_bases"])
    knowledge_bases = agent.knowledge_bases

    try:
        # Generating the response using the agent configuration and knowledge base
        response = await generate_llm_response(
            prompt=prompt,
            agent_config=agent.config,
            knowledge_bases=knowledge_bases  
        )
        return success_response(
            message="Chat response generated",
            data={
                "response": response["content"],
                "model": response["model"],
                "tokens_used": response.get("usage", {}).get("total_tokens", 0),
                "cost": f"${response['cost']:.5f}",
            }
        )
    except HTTPException as e:
        return error_response(e.detail, e.status_code)