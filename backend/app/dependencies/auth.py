import logging
from fastapi import Depends, HTTPException, status, WebSocket, WebSocketException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import verify_clerk_token
from app.db.repository.user import get_user, create_user
from app.db.models.knowledge_base import KnowledgeBase
from app.db.database import get_db, SessionLocal
from app.core.security import verify_websocket_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User
from typing import List
from app.core.config import settings
from jwt import PyJWTError as JWTError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

http_bearer = HTTPBearer()

#MJ: This is our Main Dependecy for all the routes that require Authentication. 
#MJ: It will return the current user based on the token provided in the request.
#MJ: It will also create a new user if the user is not found in the database
#MJ: This is a very basic implementation. We need to add more security checks
#MJ: (e.g. Roles and Permissions) in the future

async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
        db: AsyncSession = Depends(get_db)
) -> User:
    try:
        payload = verify_clerk_token(credentials)
        user_id = payload.get("sub")

        #TODO: MJ: Add additional security checks (e.g. Roles and Permissions)
        print(f"User ID: {user_id}")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'sub' claim",
                headers={"WWW-Authenticate": "Bearer"},
        )
        #TODO:MJ: This needs to be optimized. We should not be hitting the database for every request
        user = await get_user(db, user_id)
    
        if not user:
            user = await create_user(
                db, 
                user_id=user_id,
                name=payload.get("username"),
                email=payload.get("email"), 
                organization_id=None 
            )  
            await db.refresh(user)
            
        return user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )
# SH: Validate if the current user has access to the provided knowledge base IDs
async def validate_kb_access(
    knowledge_ids: List[int],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # SH: Select all knowledge base Ids that belong to the user's organization
    result = await db.execute(
        select(KnowledgeBase.id)
        .where(KnowledgeBase.id.in_(knowledge_ids))
        .where(KnowledgeBase.organization_id == user.organization_id)
    )
    valid_ids = result.scalars().all()
    
    # SH: If the number of valid IDs doesn't match the provided list, raise an error
    if len(valid_ids) != len(knowledge_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized Knowledge Base access"
        )
        
# SH: WebSocket authentication handler to fetch the current user from token
async def get_current_user_ws(websocket: WebSocket) -> User:
    try:
        logger.debug("WebSocket handshake initiated.")
        
        # SH: Extract the token from WebSocket query parameters
        token = websocket.query_params.get("token")
        if not token:
            logger.error("Token missing in WebSocket connection.")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")

        logger.debug(f"Token received: {token[:20]}...")  #log first few characters

        try:
            # SH: Verify the token and extract the payload
            payload = verify_websocket_token(token)
            logger.debug(f"Token payload: {payload}")
        except JWTError as jwt_error:
            logger.error(f"JWT verification failed: {jwt_error}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")

        # SH: Get user ID (sub) from token payload
        user_id = payload.get("sub")
        if not user_id:
            logger.error("Token does not contain 'sub' (user ID).")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token payload")

        logger.debug(f"User ID from token: {user_id}")

        async with SessionLocal() as db:
            logger.debug("Database session started.")
            
            # SH: Try to get user from DB
            user = await get_user(db, user_id)
            if user:
                logger.debug(f"User found in DB: {user_id}")
            else:
                # SH: Create a new user if not found
                logger.info(f"User not found, creating new user: {user_id}")
                user = await create_user(
                    db,
                    user_id=user_id,
                    name=payload.get("username"),
                    email=payload.get("email")
                )
                await db.commit()
                logger.debug(f"New user created: {user_id}")

            # SH: Check if user belongs to an organization
            if not user.organization_id:
                logger.warning(f"User {user_id} does not belong to any organization.")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="User must belong to an organization"
                )

            logger.info(f"User authenticated successfully: {user_id}")
            return user

    except Exception as e:
        # SH: Catch any unexpected error and close WebSocket gracefully
        logger.exception(f"Unhandled exception in WebSocket auth: {str(e)}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
