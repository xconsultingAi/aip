from fastapi import WebSocket, APIRouter, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dashboard_ws import dashboard_ws_manager
from app.db.database import SessionLocal
from app.models.user import UserOut
from app.dependencies.auth import get_current_user_ws
from fastapi.exceptions import WebSocketException
import logging
from datetime import datetime
import asyncio
from app.db.repository.dashboard import get_dashboard_stats

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    user = None
    db = None
    
    try:
        #SH: Step 1: Authenticate User with Clerk token
        token = websocket.query_params.get("token")
        if not token:
            logger.error("No token provided")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        try:
            #SH: Verify user from Clerk token
            user = await get_current_user_ws(websocket)
            logger.info(f"Authenticated user: {user.user_id}")
        except WebSocketException as e:
            logger.error(f"Authentication failed: {e.reason}")
            await websocket.send_json({"error": e.reason})
            await websocket.close(code=e.code)
            return

        #SH: Step 2: Create database session
        db = SessionLocal()
        
        #SH: Step 3: Accept Connection
        await websocket.accept()
        
        #SH: Connect to manager WITHOUT accepting again
        await dashboard_ws_manager.connect(websocket, user.user_id, user.organization_id)
        
        #SH: Step 4: Send Initial Stats
        try:
            stats = await get_dashboard_stats(db, user)
            await websocket.send_json({
                "type": "init_stats",
                "data": stats,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error getting initial stats: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "content": "Failed to load initial dashboard data"
            })

        #SH: Step 5: Main Connection Loop
        while True:
            try:
                #SH: Keep connection alive with periodic pings
                await asyncio.sleep(10)
                await websocket.send_json({
                    "type": "ping",
                    "timestamp": datetime.now().isoformat()
                })
            except WebSocketDisconnect:
                logger.info(f"User {user.user_id} disconnected normally")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "content": "Connection error occurred"
                })
                break

    except Exception as e:
        logger.error(f"Connection setup error: {str(e)}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

    finally:
        # Cleanup
        try:
            if user:
                await dashboard_ws_manager.disconnect(user.user_id, user.organization_id)
            if db:
                await db.close()
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
        logger.info(f"Dashboard connection closed for user {user.user_id if user else 'unknown'}")