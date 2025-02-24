from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.responses import success_response, error_response
from app.dependencies.auth import get_current_user
from app.models.agent import AgentCreate, AgentOut, AgentConfigSchema, ALLOWED_MODELS
from app.db.repository.agent import get_agents, get_agent, create_agent, update_agent_config
# from app.db.repository.knowledge import create_knowledge
from app.db.database import get_db
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models.user import UserOut as User
from app.core.exceptions import LLMServiceError
# from typing import List
from app.services.llm_services import LLMService
# from app.services.monitoring import Monitoring
# import time

# MJ: This is our Main Router for all the routes related to Agents

router = APIRouter(
    prefix="/agent",
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
    agents_out = [AgentOut.model_validate(agent) for agent in agents] 
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

    # Convert to Pydantic model and return API response
    agent_out = AgentOut.model_validate(agent)
    return success_response("Agent retrieved successfully", data=agent_out)
    
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
    # Temperature validation
    if not (0 <= agent.config.temperature <= 1):
        return error_response(
            message="Temperature must be between 0 and 1",
            http_status=status.HTTP_400_BAD_REQUEST
        )
    
    # Max length validation
    if agent.config.max_length <= 0:
        return error_response(
            message="Max length must be greater than 0",
            http_status=status.HTTP_400_BAD_REQUEST
        )

@router.post("/{agent_id}/chat")
async def chat_with_agent(
    agent_id: int,
    prompt: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    agent = await get_agent(db, agent_id, current_user.user_id)
    if not agent:
        return error_response("Agent not found", status.HTTP_404_NOT_FOUND)

    try:
        llm_service = LLMService(agent.config)
        response = await llm_service.generate_response(prompt)
        return success_response(
            "Chat response generated",
            {
                "response": response['content'],
                "tokens_used": response['tokens_used'],
                "model_used": response['model_used']
            }
        )
    except LLMServiceError as e:
        return error_response(str(e), e.status_code)

    # Check if user has an organization
    # if not current_user.organization_id:
    #     return error_response(
    #         message=f"User does not exist in any Organization",
    #         http_status=status.HTTP_403_FORBIDDEN
    #     )
    
    # try:
    #     new_agent = await create_agent(db, agent, current_user.user_id, current_user.organization_id)
    #     agent_out = AgentOut.model_validate(new_agent)
    #     return success_response("Agent created successfully", data=agent_out)
    # except IntegrityError as e:
    #     print(f"Integrity error occurred: {e}")
    #     return error_response(
    #         message=f"An agent with the same details already exists.",
    #         http_status=status.HTTP_400_BAD_REQUEST
    #     )
    # except SQLAlchemyError as e:
    #     print(f"Database error occurred: {e}")
    #     return error_response(
    #         message=f"An unexpected error occurred while creating the agent.",
    #         http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
    #     )
    # except Exception as e:
    #     print(f"Unexpected error occurred: {e}")
    #     return error_response(
    #         message=f"An unexpected error occurred.",
    #         http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
    #     )

# @router.patch("/{agent_id}/config")
# async def update_agent_config(
#     agent_id: int,
#     config: AgentConfigSchema,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     agent = await get_agent(db, agent_id, current_user.user_id)
#     updated_agent = await update_agent_config(db, agent.id, config)
#     return success_response("Config updated", AgentOut.model_validate(updated_agent))

# @router.post("/{agent_id}/knowledge")
# async def link_knowledge(
#     agent_id: int,
#     knowledge_ids: List[int],
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     await create_knowledge(db, agent_id, knowledge_ids)
#     return success_response("Knowledge bases linked")

# @router.post("/{agent_id}/generate")
# async def generate_response(
#     agent_id: int,
#     prompt: str,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     agent = await get_agent(db, agent_id, current_user.user_id)
#     if not agent:
#         return error_response("Agent not found", status.HTTP_404_NOT_FOUND)

#     llm_service = LLMService()
    
#     try:
#         start_time = time.time()
#         response = await llm_service.generate_response(agent, prompt)
#         duration = time.time() - start_time
        
#         Monitoring.response_times.labels(agent.config.model_name).observe(duration)
#         Monitoring.api_calls.labels(agent.config.model_name, 'success').inc()
        
#         return success_response("Generated successfully", {"response": response})
        
#     except NonRetryableError as e:
#         Monitoring.api_calls.labels(agent.config.model_name, 'client_error').inc()
#         return error_response(str(e), status.HTTP_400_BAD_REQUEST)
        
#     except RetryableError as e:
#         Monitoring.api_calls.labels(agent.config.model_name, 'server_error').inc()
#         return error_response(str(e), status.HTTP_503_SERVICE_UNAVAILABLE)
