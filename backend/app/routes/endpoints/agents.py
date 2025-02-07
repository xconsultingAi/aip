
from fastapi import APIRouter, status, Depends,  HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.responses import success_response, error_response
from app.dependencies.auth import get_current_user
from app.models.agent import AgentCreate, AgentOut
from app.db.repository.agent import get_agents, get_agent, create_agent
from app.db.database import get_db
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models.user import UserOut as User

#MJ: This is our Main Router for all the routes related to Agents

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    dependencies=[Depends(get_current_user)]  #MJ: Ensure secure routes for agents
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
    return success_response("Agents retrieved successfully", data=agent_out)
    

@router.post("/", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_new_agent(
        agent: AgentCreate, 
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
    # Check if user has an organization
    if not current_user.organization_id:
        return error_response(
            message=f"User does notexist in any Organization",
            http_status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        new_agent = await create_agent(db, agent, current_user.user_id, current_user.organization_id)
        agent_out = AgentOut.model_validate(new_agent)
        return success_response("Agent created successfully", data=agent_out)
    except IntegrityError as e:
        print(f"Integrity error occurred: {e}")
        return error_response(
            message=f"An agent with the same details already exists.",
            http_status=status.HTTP_400_BAD_REQUEST
        )
    except SQLAlchemyError as e:
        print(f"Database error occurred: {e}")
        return error_response(
            message=f"An unexpected error occurred while creating the agent.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        print(f"Unexpected error occurred: {e}")
        return error_response(
            message=f"An unexpected error occurred.",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
