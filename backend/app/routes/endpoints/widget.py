from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, logger
from app.core.websocket_manager import widget_manager
from app.services.widget_services import WidgetService
from app.db.database import get_db
from app.core.config import settings
import uuid
from datetime import datetime
import logging

router = APIRouter(tags=["widget"])
widget_service = WidgetService()

logger = logging.getLogger(__name__)

@router.websocket("/ws/public/{agent_id}")
async def public_widget_websocket(
    websocket: WebSocket,
    agent_id: int
):
    await websocket.accept()
    
    # Get async database session
    db_gen = get_db()
    db = await anext(db_gen)  # Use await with async next
    
    visitor_id = f"{settings.WIDGET_ANONYMOUS_PREFIX}{uuid.uuid4()}"
    
    try:
        # Verify agent exists and is public
        agent = await widget_service.verify_public_agent(db, agent_id)
        if not agent:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Register visitor session
        await widget_manager.connect_visitor(agent_id, visitor_id, websocket)
        
        await websocket.send_json({
            "type": "session_start",
            "visitor_id": visitor_id,
            "agent": agent.name,
            "timestamp": datetime.now().isoformat()
        })

        while True:
            try:
                data = await websocket.receive_json()
                
                if "content" not in data:
                    await websocket.send_json({
                        "type": "error",
                        "content": "Invalid message format"
                    })
                    continue

                response = await widget_service.process_public_widget_message(
                    db=db,
                    agent_id=agent_id,
                    message=data["content"]
                )
                await websocket.send_json({
                    "type": "message",
                    "content": response["content"],
                    "sender": "agent",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": response.get("metadata", {})
                })

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in public widget: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "content": str(e)
                })

    finally:
        await widget_manager.disconnect_visitor(visitor_id)
        try:
            await anext(db_gen)
        except StopAsyncIteration:
            pass