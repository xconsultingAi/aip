from tenacity import retry, stop_after_attempt, wait_exponential
from fastapi import WebSocketException, status, HTTPException
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from app.core.llm import OpenAIClient
import openai
from app.db.repository.chat import create_chat_message, create_conversation, get_conversation_by_id
from app.db.database import AsyncSession
from app.core.vector_store import get_organization_vector_store
from app.core.config import settings
from sqlalchemy import select, func
from app.db.models.chat import ChatMessage, Conversation
from app.db.models.agent import Agent
import logging
from sqlalchemy.orm import selectinload
from app.core.exceptions import network_exception

logger = logging.getLogger(__name__)

#SH: Retry logic: This function will retry up to 3 times
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def process_agent_response(
    user_id: str,
    agent_id: int,
    message: str,
    sequence_id: int,
    db: AsyncSession,
    conversation_id: int
) -> dict:
    try:
        #SH: Step 1: Rate limit large messages
        if len(message) > 1000:
            raise WebSocketException(
                code=status.WS_1009_MESSAGE_TOO_BIG,
                reason="Message exceeds 1000 characters"
            )

        #SH: Step 2: Fetch agent and verify access
        logger.debug(f"Fetching agent {agent_id} for user {user_id} with knowledge bases")
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id, Agent.user_id == user_id).options(selectinload(Agent.knowledge_bases))
        )
        agent = result.scalar_one_or_none()
        if not agent:
            logger.error(f"Agent {agent_id} not found")
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Agent not found"
            )
        
        #SH: Step 3: Validate message sequence
        valid_sequence, last_seq = await validate_message_sequence(db, user_id, agent_id, sequence_id, conversation_id)
        if not valid_sequence:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=f"Invalid message sequence. Expected {last_seq + 1}, but received {sequence_id}."
            )

        #SH: Step 4: Create RAG context
        logger.debug(f"Initializing vector store for org {agent.organization_id}")
        vector_store = get_organization_vector_store(agent.organization_id)
        docs = await vector_store.asimilarity_search(message, k=3)
        context = "\n".join([doc.page_content for doc in docs])
        full_prompt = f"Context: {context}\n\nQuestion: {message}"

        #SH: Step 5: Save user message in database
        await create_chat_message(db, {
            "content": message,
            "sender": "user",
            "user_id": user_id,
            "agent_id": agent_id,
            "sequence_id": sequence_id,
            "conversation_id": conversation_id
        })

        #SH: merged config values from agent
        temperature = agent.config.get("temperature", 0.7)
        model_name = agent.config.get("model_name", "gpt-4")
        system_prompt = agent.config.get("system_prompt", "You are a helpful assistant")

        #SH: Step 6: Generate agent response using LLM
        llm_client = OpenAIClient()
        response = await llm_client.generate(
            model=agent.config.get("model_name", "gpt-4"),
            prompt=full_prompt,
            system_prompt=agent.config.get("system_prompt", "You are a helpful assistant"),
            temperature=agent.config.get("temperature", 0.7),
            max_tokens=agent.config.get("max_length", 500)
        )

        #SH: Step 7: Save agent's reply in chat history
        await create_chat_message(db, {
            "content": response["content"],
            "sender": "agent",
            "user_id": user_id,
            "agent_id": agent_id,
            "sequence_id": sequence_id + 1,
            "conversation_id": conversation_id
        })

        #SH: Step 8: Return response to be sent to frontend
        return {
            "content": response["content"],
            "metadata": {
                "model": agent.config.get("model_name"),
                "tokens_used": response.get("usage", {}).get("total_tokens", 0),
                "cost": response.get("cost", 0),
                "sources": await get_knowledge_sources(agent.knowledge_bases),
                "theme_color": agent.theme_color,
                "greeting": agent.greeting_message,
                "is_public": agent.is_public
            }
        }

    except openai.APIConnectionError as e:
        logger.error(f"Network error: {str(e)}")
        raise network_exception("Connection to AI service failed") from e
    except WebSocketException:
        raise
    except Exception as e:
        logger.exception(f"Error processing agent message: {str(e)}", exc_info=True)
        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR,
            reason=str(e)
        )

#SH: Validate message sequence against DB history
async def validate_message_sequence(db: AsyncSession, user_id: str, agent_id: int, received_seq: int, conversation_id: int):
    result = await db.execute(
        select(func.max(ChatMessage.sequence_id))
        .where(
            (ChatMessage.user_id == user_id) &
            (ChatMessage.agent_id == agent_id) &
            (ChatMessage.conversation_id == conversation_id)
        )
    )
    last_seq = result.scalar() or 0
    logger.debug(f"Validating sequence: user_id={user_id}, agent_id={agent_id}, conversation_id={conversation_id}, last_seq={last_seq}, received_seq={received_seq}")
    if received_seq <= last_seq:
        logger.warning(f"Sequence ID {received_seq} is not greater than last sequence {last_seq}")
        return False, last_seq
    return True, last_seq

#SH: Function to extract metadata from knowledge bases
async def get_knowledge_sources(knowledge_bases):
    return [{
        "filename": kb.filename,
        "uploaded_at": kb.uploaded_at.isoformat(),
        "chunk_count": kb.chunk_count
    } for kb in knowledge_bases]

#SH: Fallback function to build RAG context by loading full files
async def get_rag_context(knowledge_bases):
    context = []
    for kb in knowledge_bases:
        loader = PyPDFLoader(kb.file_path) if kb.content_type == "application/pdf" else TextLoader(kb.file_path)
        documents = loader.load()
        context.extend([doc.page_content for doc in documents])
    return "\n\n".join(context[:5])

#SH: Utility to verify agent access
async def verify_agent_access(db: AsyncSession, agent_id: int, user_id: str):
    logger.info(f"Verifying access to agent {agent_id}")
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        logger.error(f"Agent {agent_id} not found or access denied")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Agent not found or access denied"
        )
    logger.info(f"Access granted to agent {agent_id}")
    return agent

#SH: Validate message ownership
async def validate_message_ownership(db: AsyncSession, message_id: int, user_id: str):
    result = await db.execute(
        select(ChatMessage)
        .where(
            (ChatMessage.id == message_id) & 
            (ChatMessage.user_id == user_id)
        )
    )
    message = result.scalar_one_or_none()
    if not message:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Message not found or access denied"
        )
    return message

#SH: Start a new conversation
async def start_new_conversation(
    db: AsyncSession, 
    user_id: str, 
    agent_id: int, 
    initial_message: str
) -> Conversation:
    try:
        title = initial_message[:50].strip() or "New Chat"
        conv_data = {
            "title": title,
            "user_id": user_id,
            "agent_id": agent_id
        }
        
        conversation = await create_conversation(db, conv_data)
        
        await create_chat_message(db, {
            "conversation_id": conversation.id,
            "content": initial_message,
            "sender": "user",
            "user_id": user_id,
            "agent_id": agent_id,
            "sequence_id": 1
        })
        
        return conversation

    except Exception as e:
        await db.rollback()
        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR,
            reason=f"Failed to start conversation: {str(e)}"
        )

#SH: Get conversation with messages
async def get_conversation_with_messages(
    db: AsyncSession,
    conversation_id: int,
    user_id: str
) -> dict:
    conversation = await get_conversation_by_id(db, conversation_id, user_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )
    
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "messages": [
            {
                "id": msg.id,
                "content": msg.content,
                "sender": msg.sender,
                "timestamp": msg.timestamp
            }
            for msg in conversation.messages
        ]
    }

#SH: Fetch all messages for a conversation
async def get_conversation_messages(db: AsyncSession, conversation_id: int):
    try:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.timestamp.asc())
        )
        return result.scalars().all()

    except Exception as e:
        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR,
            reason=f"Error fetching conversation messages: {str(e)}"
        )