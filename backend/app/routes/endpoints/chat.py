import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, WebSocketException, Depends, HTTPException
from app.core.websocket_manager import websocket_manager
from app.dependencies.auth import get_current_user_ws, get_current_user
from app.db.repository.agent import get_agent
from app.services.chat_services import  process_agent_response as service_process_agent_message, start_new_conversation
from app.db.database import SessionLocal, get_db
from app.core.config import settings
from sqlalchemy.exc import SQLAlchemyError
import datetime
from sqlalchemy import select, func
from app.db.models.chat import ChatMessage, Conversation
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import ConversationOut, ConversationWithMessages, UserConversationCount
from app.db.repository.chat import delete_conversation, fetch_chat_history,get_conversation, get_conversation_by_id, create_chat_message, update_conversation_title
from app.db.models.user import User 
from app.db.repository.chat import get_user_conversation_count as repo_count

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)

#SH: WebSocket endpoint for chat
@router.websocket("/ws/chat/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: int):
    user = None
    db = None
    conversation_id = None  # Added conversation_id
    is_new_conversation = False  # Initialize the flag

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

            #SH: Add conversation handling
            if "conversation_id" in websocket.query_params:
                try:
                    conversation_id = int(websocket.query_params["conversation_id"])
                    result = await db.execute(
                        select(Conversation)
                        .where(
                            (Conversation.id == conversation_id) &
                            (Conversation.user_id == user.user_id)
                        )
                    )
                    if not result.scalar():
                        await websocket.send_json({
                            "type": "error",
                            "content": "Invalid conversation ID or access denied."
                        })
                        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                        return
                    logger.info(f"Using existing conversation_id: {conversation_id}")
                    is_new_conversation = False  # Existing conversation
                except Exception as e:
                    logger.error(f"Invalid conversation_id provided: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "content": "Invalid conversation_id format."
                    })
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return
            else:
                #SH: Start new conversation 
                conversation = await start_new_conversation(db, user.user_id, agent_id, "New Chat")
                conversation_id = conversation.id
                logger.info(f"Started new conversation: {conversation_id}")
                is_new_conversation = True

            #SH: Step 3: Accept Connection and Register
            await websocket.accept()
            websocket.max_message_size = settings.WEBSOCKET_MAX_MESSAGE_SIZE
            logger.info(f"Set max message size to {settings.WEBSOCKET_MAX_MESSAGE_SIZE} bytes")

            await websocket_manager.connect(websocket, user.user_id, agent_id)
            #SH: Notify client that connection is established
            await websocket.send_json({
                "type": "system",
                "content": f"Connected to Agent {agent.name}",
                "timestamp": datetime.datetime.now().isoformat()
            })

            #SH: Step 4: Main Chat Loop
            system_status = await websocket_manager.check_system_status()
            if system_status["status"] != "ok":
                await websocket.send_json({
                    "type": "system",
                    "content": system_status["message"]
                })
                await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
                return

            last_status_check = datetime.datetime.now()

            #SH: Modified message handling loop
            while True:
                try:
                    message = await websocket.receive()
                    if "text" not in message:
                        continue

                    try:
                        data = json.loads(message["text"])
                        logger.debug(f"Received raw data: {data}")
                    except json.JSONDecodeError:
                        data = {"content": message["text"], "sequence_id": None}
                    #SH: Don't process empty messages
                    if "content" not in data:
                        await websocket.send_json({
                            "type": "error",
                            "content": "Missing required field: content"
                        })
                        continue
                    #SH: Process the message with agent logic
                    message_content = data['content']
                    seq_id = data.get('sequence_id')

                    if not seq_id:
                        result = await db.execute(
                            select(func.max(ChatMessage.sequence_id))
                            .where(
                                (ChatMessage.user_id == user.user_id) & 
                                (ChatMessage.agent_id == agent_id)&
                                (ChatMessage.conversation_id == conversation_id)
                            )
                        )
                        last_seq = result.scalar() or 0
                        seq_id = last_seq + 1

                    logger.info(f"Processing message seq {seq_id}: {message_content[:50]}...")

                    #SH: First message title update for new conversation
                    if is_new_conversation:
                        new_title = message_content[:50].strip()
                        if not new_title:
                            new_title = "New Chat"
                        await update_conversation_title(db, conversation_id, new_title)
                        is_new_conversation = False  # Only update once

                    response = await service_process_agent_message(
                        user_id=user.user_id,
                        agent_id=agent_id,
                        message=message_content,
                        sequence_id=seq_id,
                        db=db,
                        conversation_id=conversation_id
                    )
                    await websocket.send_json({
                        "type": "message",
                        "sequence_id": seq_id,
                        "content": response["content"],
                        "sender": "agent",
                        "timestamp": datetime.datetime.now().isoformat(),
                        "metadata": response.get("metadata", {})
                    })

                    #SH: Periodic system status check
                    if datetime.datetime.now() - last_status_check > datetime.timedelta(minutes=5):
                        system_status = await websocket_manager.check_system_status()
                        last_status_check = datetime.datetime.now()
                        if system_status["status"] != "ok":
                            await websocket.send_json({
                                "type": "system",
                                "content": system_status["message"]
                            })

                except WebSocketDisconnect:
                    #SH: Client disconnected
                    logger.info(f"User {user.user_id} disconnected normally")
                    break
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "code": "INTERNAL_ERROR",
                        "message": "Something went wrong. Our team has been notified."
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
        
# SH: Route for Continue Previous chat
@router.websocket("/ws/conversation/{conversation_id}")
async def continue_conversation_endpoint(websocket: WebSocket, conversation_id: int):
    user = None
    db = None
    agent_id = None

    try:
        #SH: Step 1: Authenticate User
        token = websocket.query_params.get("token")
        if not token:
            logger.error("No token provided")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        try:
            user = await get_current_user_ws(websocket)
            logger.info(f"Authenticated user: {user.user_id}")
        except WebSocketException as e:
            logger.error(f"Authentication failed: {e.reason}")
            await websocket.send_json({"error": e.reason})
            await websocket.close(code=e.code)
            return

        #SH: Step 2: Fetch and Validate Conversation
        db = SessionLocal()
        conversation = await get_conversation_by_id(db, conversation_id, user.user_id)
        if not conversation:
            logger.error(f"Conversation {conversation_id} not found or access denied")
            await websocket.send_json({
                "type": "error",
                "content": "Conversation not found or access denied"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        agent_id = conversation.agent_id
        logger.info(f"Verified conversation: {conversation_id} for user: {user.user_id}")

        #SH: Step 3: Verify Agent Access
        agent = await get_agent(db, agent_id, user.user_id)
        if not agent:
            error_msg = f"Agent {agent_id} not found or access denied"
            logger.error(error_msg)
            await websocket.send_json({
                "type": "error",
                "content": error_msg
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        logger.info(f"Verified agent: {agent_id} for conversation: {conversation_id}")

        #SH: Step 4: Accept Connection and Register
        await websocket.accept()
        websocket.max_message_size = settings.WEBSOCKET_MAX_MESSAGE_SIZE
        logger.info(f"Set max message size to {settings.WEBSOCKET_MAX_MESSAGE_SIZE} bytes")

        await websocket_manager.connect(websocket, user.user_id, agent_id)
        await websocket.send_json({
            "type": "system",
            "content": f"Connected to conversation {conversation.title} with Agent {agent.name}",
            "timestamp": datetime.datetime.now().isoformat()
        })

        #SH: Step 5: Send Conversation History
        messages = await fetch_chat_history(db, user.user_id, agent_id, conversation_id)
        history = [
            {
                "type": "message",
                "sequence_id": msg.sequence_id,
                "content": msg.content,
                "sender": msg.sender,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ]
        await websocket.send_json({
            "type": "history",
            "content": history,
            "timestamp": datetime.datetime.now().isoformat()
        })

        #SH: Step 6: Main Chat Loop
        system_status = await websocket_manager.check_system_status()
        if system_status["status"] != "ok":
            await websocket.send_json({
                "type": "system",
                "content": system_status["message"]
            })
            await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
            return

        last_status_check = datetime.datetime.now()

        while True:
            try:
                message = await websocket.receive()
                if "text" not in message:
                    continue

                try:
                    data = json.loads(message["text"])
                    logger.debug(f"Received raw data: {data}")
                except json.JSONDecodeError:
                    data = {"content": message["text"], "sequence_id": None}

                if "content" not in data:
                    await websocket.send_json({
                        "type": "error",
                        "content": "Missing required field: content"
                    })
                    continue
                #SH: Process the message with agent logic
                message_content = data['content']
                seq_id = data.get('sequence_id')

                if not seq_id:
                    result = await db.execute(
                        select(func.max(ChatMessage.sequence_id))
                        .where(
                            (ChatMessage.user_id == user.user_id) & 
                            (ChatMessage.agent_id == agent_id) &
                            (ChatMessage.conversation_id == conversation_id)
                        )
                    )
                    last_seq = result.scalar() or 0
                    seq_id = last_seq + 1

                logger.info(f"Processing message seq {seq_id}: {message_content[:50]}...")

                response = await service_process_agent_message(
                    user_id=user.user_id,
                    agent_id=agent_id,
                    message=message_content,
                    sequence_id=seq_id,
                    db=db,
                    conversation_id=conversation_id
                )
                await websocket.send_json({
                    "type": "message",
                    "sequence_id": seq_id,
                    "content": response["content"],
                    "sender": "agent",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "metadata": response.get("metadata", {})
                })

                #SH: Periodic system status check
                if datetime.datetime.now() - last_status_check > datetime.timedelta(minutes=5):
                    system_status = await websocket_manager.check_system_status()
                    last_status_check = datetime.datetime.now()
                    if system_status["status"] != "ok":
                        await websocket.send_json({
                            "type": "system",
                            "content": system_status["message"]
                        })

            except WebSocketDisconnect:
                logger.info(f"User {user.user_id} disconnected normally from conversation {conversation_id}")
                break
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "code": "INTERNAL_ERROR",
                    "message": "Something went wrong. Our team has been notified."
                })

    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "content": "Database operation failed"
        })
    except Exception as e:
        logger.error(f"Unexpected error in continue_conversation_endpoint: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "content": "Unexpected error occurred"
        })

    finally:
        try:
            if user:
                await websocket_manager.disconnect(user.user_id, agent_id)
            if db:
                await db.close()
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
        logger.info(f"Connection closed for user {user.user_id if user else 'unknown'} in conversation {conversation_id}")

# SH: Route for get all conversation
@router.get("/conversations", response_model=list[ConversationOut])
async def get_all_conversations(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversations = await get_conversation(db, current_user.user_id, agent_id)
    return [ConversationOut.model_validate(c) for c in conversations]

# SH: route for count of conversation
@router.get("/conversations/count", response_model=UserConversationCount)
async def get_user_conversation_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Get User object
):
    #SH: Get total count of conversations for the current user
    try:
        #SH: Use the repository function with user_id string
        count = await repo_count(db, current_user.user_id)
        
        return {
            "user_id": current_user.user_id,
            "total_conversations": count
        }
    except Exception as e:
        logger.error(f"Error getting conversation count: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve conversation count"
        )

# SH: Update name on the base of conversation_id
@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: int,
    new_title: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updated = await update_conversation_title(db, conversation_id, new_title)
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation updated"}

# Delete conversation on the base of conversation_id
@router.delete("/conversations/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    deleted = await delete_conversation(db, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted"}

# SH: Get conversation on the base of conversation_id
@router.get("/conversations/{conversation_id}", response_model=ConversationWithMessages)
async def get_single_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conversation = await get_conversation_by_id(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.user_id
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation

# SH: Route for get all conversations for the user
@router.get("/user/conversations", response_model=list[ConversationOut])
async def get_all_user_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    #SH: Get all conversations for the current user
    try:
        from app.db.repository.chat import get_all_user_conversations
        conversations = await get_all_user_conversations(db, current_user.user_id)
        return [ConversationOut.model_validate(c) for c in conversations]
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        raise HTTPException(500, "Could not retrieve conversations")