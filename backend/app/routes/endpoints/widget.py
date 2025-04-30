from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from app.services.widget_services import WidgetService
from app.core.websocket_manager import websocket_manager
from app.db.database import SessionLocal
from app.db.repository.agent import get_public_agent
import logging
import json
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["widget"])
logger = logging.getLogger(__name__)

# Initialize the WidgetService
widget_service = WidgetService()

@router.websocket("/ws/public/{agent_id}")
async def widget_chat_endpoint(websocket: WebSocket, agent_id: int):
    async with SessionLocal() as db:  # Use async context manager
        try:
            # 1. Verify public agent exists
            agent = await get_public_agent(db, agent_id)
            if not agent:
                await websocket.close(code=1008)  # Policy violation
                return

            # 2. Accept connection
            await websocket.accept()
            
            # 3. Send greeting message
            await websocket.send_json({
                "type": "greeting",
                "content": "Hello! How can I help?",
                "color": "#22c55e",
                "agent_id": agent_id
            })

            # 4. Message handling loop
            while True:
                try:
                    # Wait for message with timeout
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Process message through agent
                    response = await widget_service.process_widget_message(
                        agent_id=agent_id,
                        message=message.get("content", ""),
                        db=db,
                        metadata={
                            "ip": websocket.client.host,
                            "user_agent": websocket.headers.get("user-agent"),
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                    )
                    
                    # Send response back to client
                    await websocket.send_json({
                        "type": response.get("type", "response"),
                        "content": response.get("content", ""),
                        "color": "#22c55e",
                        "agent_id": agent_id,
                        "metadata": response.get("metadata", {})
                    })

                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "content": "Invalid message format",
                        "error_type": "invalid_format"
                    })
                except asyncio.TimeoutError:
                    await websocket.send_json({
                        "type": "error",
                        "content": "Connection timeout",
                        "error_type": "timeout"
                    })
                except WebSocketDisconnect:
                    logger.info("Client disconnected")
                    break
                except Exception as e:
                    logger.error(f"Widget processing error: {str(e)}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "content": "Message processing failed",
                        "error_type": "processing_error"
                    })

        except Exception as e:
            logger.error(f"WebSocket endpoint error: {str(e)}", exc_info=True)
            try:
                await websocket.close(code=1011)  # Internal error
            except:
                pass  # Already closed