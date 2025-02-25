from fastapi import APIRouter, status, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.responses import success_response, error_response
from app.dependencies.auth import get_current_user
from app.models.agent import AgentCreate, AgentOut, ALLOWED_MODELS
from app.models.knowledge_base import KnowledgeBaseCreate, KnowledgeLinkRequest
from app.db.repository.agent import get_agents, get_agent, create_agent, update_agent_config
from app.db.repository.knowledge_base import create_knowledge_entry
from app.db.database import get_db
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models.user import UserOut as User
from app.core.exceptions import LLMServiceError, InvalidAPIKeyError
from typing import List
from app.services.llm_services import LLMService
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
    # Convert SQLAlchemy object to Pydantic model properly
    return AgentOut.model_validate(agent, from_attributes=True)
       
@router.post("/", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_new_agent(
        agent: AgentCreate, 
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
    # Model validation check
    if agent.config.model_name not in ALLOWED_MODELS:
        return error_response(
            message=f"Invalid model selected. Allowed models: {ALLOWED_MODELS}",
            http_status=status.HTTP_400_BAD_REQUEST
        )
    if not (0 <= agent.config.temperature <= 1):
        return error_response(
            message="Temperature must be between 0 and 1",
            http_status=status.HTTP_400_BAD_REQUEST
        )
    if agent.config.max_length <= 0:
        return error_response(
            message="Max length must be greater than 0",
            http_status=status.HTTP_400_BAD_REQUEST
        )
        
    try:
        new_agent = await create_agent(db, agent, current_user.user_id, current_user.organization_id)
        agent_dict = new_agent.__dict__
        agent_dict.pop('_sa_instance_state', None)  #SH: SQLAlchemy internal state
        
        return success_response(
            "Agent created successfully",
            AgentOut(**agent_dict)
        )
        
    except IntegrityError as e:
        return error_response(
            message="An agent with the same details already exists.",
            http_status=status.HTTP_400_BAD_REQUEST
        )
    except SQLAlchemyError as e:
        return error_response(
            message="An unexpected error occurred while creating the agent.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
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
    """Secure endpoint for agent interactions"""
    agent = await get_agent(db, agent_id, current_user.user_id)
    
    if not agent:
        return error_response("Agent not found", status.HTTP_404_NOT_FOUND)

    try:
        llm_service = LLMService(agent.config)
        response = await llm_service.generate_response(prompt)
        
        return success_response(
            message="Chat response generated",
            data={
                "response": response["content"],
                "model": response["model"],
                # "tokens_used": response["tokens"],
                "tokens_used": response.get("usage", {}).get("total_tokens", 0),

                "cost": f"${response['cost']:.5f}",
            }
        )
        
    except LLMServiceError as e:
        return error_response(str(e), e.status_code)
        
    except InvalidAPIKeyError:
        return error_response("Invalid OpenAI configuration", status.HTTP_401_UNAUTHORIZED)

@router.post("/{agent_id}/knowledge")
async def link_knowledge(
    agent_id: int,
    request_data: KnowledgeLinkRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    print(f"Agent ID: {agent_id}")
    print(f"Knowledge IDs: {request_data.knowledge_ids}")
    print(f"Chunk Count: {request_data.chunk_count}")

    # Ensure knowledge_ids is a valid list
    if not request_data.knowledge_ids or not isinstance(request_data.knowledge_ids, list):
        raise HTTPException(status_code=400, detail="Knowledge IDs must be a non-empty list")

    try:
        # Ensure agent exists
        agent_exists = await db.execute(select(Agent).where(Agent.id == agent_id))
        if not agent_exists.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found"
            )

        #  Process knowledge links
        for knowledge_id in request_data.knowledge_ids:
            knowledge_data = KnowledgeBaseCreate(
                filename=f"knowledge_{knowledge_id}.txt",
                content_type="text/plain",
                organization_id=current_user.organization_id
            )

            await create_knowledge_entry(
                db=db,
                knowledge_data=knowledge_data,
                file_size=0,
                chunk_count=request_data.chunk_count or 0,  # Ensure valid chunk count
                agent_id=agent_id,
                knowledge_ids=request_data.knowledge_ids or []  # Ensure valid list
            )

        return success_response("Knowledge bases linked", data={"agent_id": agent_id, "knowledge_ids": request_data.knowledge_ids})

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )