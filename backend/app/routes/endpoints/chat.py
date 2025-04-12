import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, WebSocketException
from app.core.websocket_manager import websocket_manager
from app.dependencies.auth import get_current_user_ws
from app.db.repository.agent import get_agent
from app.services.chat_services import process_agent_response as service_process_agent_message
from app.db.database import SessionLocal
from sqlalchemy.exc import SQLAlchemyError
import datetime
from starlette.websockets import WebSocketState

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)

# TODO: Add message history.
@router.websocket("/ws/chat/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: int):
    user = None
    db = None

    try:
        #SH: Step 1: Authenticate User
        token = websocket.query_params.get("token")
        if not token:
            logger.error("No token provided")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        try:
            #SH: Extract and verify user from token
            user = await get_current_user_ws(websocket)
            logger.info(f"Authenticated user: {user.user_id}")
        except WebSocketException as e:
            #SH: Authentication failed
            logger.error(f"Authentication failed: {e.reason}")
            await websocket.send_json({"error": e.reason})
            await websocket.close(code=e.code)
            return

        #SH: Step 2: Verify Agent Access
        db = SessionLocal()
        try:
            agent = await get_agent(db, agent_id, user.user_id)
            if not agent:
                #SH: Agent doesn't exist or user has no access
                error_msg = f"Agent {agent_id} not found or access denied"
                logger.error(error_msg)
                await websocket.send_json({
                    "type": "error",
                    "content": error_msg
                })
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

            logger.info(f"Verified agent: {agent_id} for user: {user.user_id}")

            #SH: Step 3: Accept Connection and Register
            await websocket.accept()
            await websocket_manager.connect(websocket, user.user_id, agent_id)

            #SH: Notify client that connection is established
            await websocket.send_json({
                "type": "system",
                "content": f"Connected to Agent {agent.name}",
                "timestamp": datetime.datetime.now().isoformat()
            })

            #SH: Step 4: Main Chat Loop
            while True:
                try:
                    data = await websocket.receive_text()
                    #SH: Check if connection is still active
                    if websocket.client_state == WebSocketState.DISCONNECTED:
                        logger.warning("Message received on closed connection")
                        break

                    logger.debug(f"Message from {user.user_id}: {data[:200]}...")

                    #SH: Don't process empty messages
                    if not data.strip():
                        await websocket.send_json({
                            "type": "error",
                            "content": "Empty message received"
                        })
                        continue

                    #SH: Process the message with agent logic
                    response = await service_process_agent_message(
                        user_id=user.user_id,
                        agent_id=agent_id,
                        message=data,
                        db=db
                    )

                    #SH: Send agent's reply back to the client
                    await websocket.send_json({
                        "type": "message",
                        "content": response["content"],
                        "sender": "agent",
                        "timestamp": datetime.datetime.now().isoformat(),
                        "metadata": response.get("metadata", {})
                    })

                except WebSocketDisconnect:
                    #SH: Client disconnected
                    logger.info(f"User {user.user_id} disconnected normally")
                    break
                except Exception as e:
                    #SH: Unexpected error while handling message
                    logger.error(f"Message processing error: {str(e)}")
                    await websocket.send_json({
                        "type": "error",
                        "content": "Message processing failed",
                        "details": str(e),
                        "timestamp": datetime.datetime.now().isoformat()
                    })

        #SH: Error handling for DB or other logic
        except SQLAlchemyError as e:
            logger.error(f"Database error: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "content": "Database operation failed"
            })
        except Exception as e:
            logger.error(f"Unexpected error in main handler: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "content": "Unexpected error occurred"
            })

    except Exception as e:
        logger.error(f"Outer connection error: {str(e)}")

    finally:
        #SH: Cleanup connection and DB
        try:
            if user:
                await websocket_manager.disconnect(user.user_id, agent_id)
            if db:
                await db.close()
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
        logger.info(f"Connection closed for user {user.user_id if user else 'unknown'}")


#SH: function to process a message with agent logic
async def process_agent_message(user_id: str, agent_id: int, message: str, db) -> dict:
    # Process message through agent and return response
    try:
        logger.info(f"Fetching agent {agent_id} configuration for user {user_id}...")
        agent = await get_agent(db, agent_id, user_id)
        if not agent:
            logger.warning(f"Agent {agent_id} not found for user {user_id}")
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Agent not found"
            )

        logger.info(f"Agent found: {agent_id}, processing message...")

        #SH: Call actual chat logic from services
        response = await service_process_agent_message(message, agent.config, db)
        logger.info(f"Agent response generated: {response['content']}")

        return {
            "content": response["content"],
            "metadata": {
                "model": agent.model_name,
                "tokens_used": response.get("usage", {}).get("total_tokens", 0),
                "cost": response.get("cost", 0)
            }
        }

    except Exception as e:
        logger.exception(f"Error processing agent message: {str(e)}", exc_info=True)
        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR,
            reason=str(e)
        )
