from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from app.services.widget_services import WidgetService
from app.db.database import SessionLocal
from app.db.repository.agent import get_public_agent
import logging
import json
import asyncio
import datetime
from typing import Dict, Any

router = APIRouter(tags=["widget"])
logger = logging.getLogger(__name__)

# Initialize the WidgetService
widget_service = WidgetService()

@router.websocket("/ws/public/{agent_id}")
async def widget_chat_endpoint(websocket: WebSocket, agent_id: int):
    logger.info(f"New WebSocket connection for agent {agent_id}")
    try:
        # 1. Accept connection and move agent check here
        async with SessionLocal() as db:
            await websocket.accept()
            logger.info(f"Fetching agent with ID {agent_id}")
            agent = await get_public_agent(db, agent_id)
            if not agent:
                logger.error(f"Agent {agent_id} not found.")
                await websocket.close(code=1008)
                return
            logger.info(f"Agent {agent_id} found: {agent.name}")

            # Send greeting message
            await websocket.send_json({
                "type": "greeting",
                "content": "Hello! How can I help?",
                "color": "#22c55e",
                "agent_id": agent_id,
                "timestamp": datetime.datetime.now().isoformat()
            })


        # 3. Message handling loop
        while True:
            try:
                # Wait for message with timeout
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=30.0  # 30 second timeout
                    )
                except asyncio.TimeoutError:
                    await websocket.send_json({
                        "type": "error",
                        "content": "Connection timeout",
                        "error_type": "timeout"
                    })
                    break

                try:
                    message: Dict[str, Any] = json.loads(data)
                    if not message.get("content", "").strip():
                        logger.warning(f"Received empty message from client: {websocket.client}")
                        raise ValueError("Empty message content")
                except (json.JSONDecodeError, ValueError) as e:
                    await websocket.send_json({
                        "type": "error",
                        "content": "Invalid message: " + str(e),
                        "error_type": "invalid_input"
                    })
                    continue

                # Process valid message
                try:
                    response = await widget_service.process_widget_message(
                        agent_id=agent_id,
                        message=message["content"].strip(),
                        db=db,
                        metadata={
                            "ip": websocket.client.host,
                            "user_agent": websocket.headers.get("user-agent"),
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                    )

                    # Send response
                    await websocket.send_json({
                        "type": response.get("type", "response"),
                        "content": response.get("content", ""),
                        "color": "#22c55e",
                        "agent_id": agent_id,
                        "metadata": response.get("metadata", {})
                    })

                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "content": "Message processing failed",
                        "error_type": "server_error"
                    })

            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {websocket.client}")
                await websocket.close()  # Ensure the WebSocket is closed on disconnect
                break
            except Exception as e:
                logger.error(f"Processing error: {str(e)}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "content": "Message processing failed",
                    "error_type": "server_error"
                })

    except Exception as e:
        logger.error(f"Endpoint error: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=1011)  # Internal error
        except Exception as inner_e:
            logger.error(f"Error closing WebSocket: {str(inner_e)}")
