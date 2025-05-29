import os
import logging
import datetime
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, status, WebSocketException
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.llm import OpenAIClient
from app.core.config import settings
from app.core.vector_store import get_organization_vector_store
from app.db.models.agent import Agent
from app.db.models.chat import ChatMessage, Conversation
from app.db.models.knowledge_base import KnowledgeBase
from app.db.repository.chat import create_chat_message, create_conversation
from app.db.repository.agent import get_agent, get_public_agent
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

#SH: Text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

#SH: Verify agent access
async def verify_agent_access(db: AsyncSession, agent_id: int, user_id: Optional[str]):
    if user_id:
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id, Agent.user_id == user_id)
        )
    else:
        result = await db.execute(
            select(Agent).where(Agent.id == agent_id, Agent.is_public == True)
        )
    agent = result.scalar_one_or_none()
    if not agent:
        logger.error(f"Access denied or agent not found: {agent_id}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Agent not found or access denied"
        )
    return agent

#SH: Validate message sequence
async def validate_message_sequence(
    db: AsyncSession,
    user_id: Optional[str],
    agent_id: int,
    received_seq: int,
    conversation_id: int
):
    result = await db.execute(
        select(func.max(ChatMessage.sequence_id))
        .where(
            (ChatMessage.user_id == user_id) &
            (ChatMessage.agent_id == agent_id) &
            (ChatMessage.conversation_id == conversation_id)
        )
    )
    last_seq = result.scalar() or 0
    if received_seq <= last_seq:
        logger.warning(f"Invalid sequence {received_seq}, last was {last_seq}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=f"Invalid message sequence. Expected > {last_seq}, got {received_seq}."
        )
    return last_seq

#SH: Get knowledge sources
async def get_knowledge_sources(knowledge_bases: List[KnowledgeBase]) -> List[Dict[str, Any]]:
    return [
        {
            "filename": kb.filename,
            "uploaded_at": kb.uploaded_at.isoformat(),
            "chunk_count": kb.chunk_count
        }
        for kb in knowledge_bases
    ]

#SH: Widget service
class WidgetService:
    def __init__(self):
        self.llm_client = OpenAIClient()

    #SH: Verify public agent
    async def verify_public_agent(self, db: AsyncSession, agent_id: int):
        """Verify agent exists and is marked as public"""
        result = await db.execute(
            select(Agent)
            .where(Agent.id == agent_id, Agent.is_public == True)
        )
        return result.scalar_one_or_none()

    #SH: Process widget message 
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def process_widget_message(
        self,
        agent_id: int,
        message: str,
        db: AsyncSession,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        sequence_id: Optional[int] = None,
        conversation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        if not message.strip():
            return {"type": "error", "error_type": "validation_error", "content": "Message cannot be empty"}
        if len(message) > settings.WIDGET_MAX_MESSAGE_LENGTH:
            return {"type": "error", "error_type": "validation_error", "content": f"Message exceeds {settings.WIDGET_MAX_MESSAGE_LENGTH} characters"}

        agent = await verify_agent_access(db, agent_id, user_id)

        if sequence_id and conversation_id:
            await validate_message_sequence(db, user_id, agent_id, sequence_id, conversation_id)

        try:
            vector_store = get_organization_vector_store(agent.organization_id)
            docs = await vector_store.asimilarity_search(message, k=settings.RAG_K)
            context = "\n".join([doc.page_content for doc in docs])
        except Exception as e:
            logger.warning(f"RAG context failed: {e}")
            context = await self._fallback_context(agent.knowledge_bases)

        full_prompt = f"Context:\n{context}\n\nVisitor: {message}"

        if conversation_id:
            await create_chat_message(db, {
                "conversation_id": conversation_id,
                "content": message,
                "sender": "user",
                "user_id": user_id,
                "agent_id": agent_id,
                "sequence_id": sequence_id
            })
        else:
            conversation = await create_conversation(db, {
                "title": message[:50].strip() or "New Chat",
                "user_id": user_id,
                "agent_id": agent_id
            })
            conversation_id = conversation.id
            sequence_id = 1
            await create_chat_message(db, {
                "conversation_id": conversation_id,
                "content": message,
                "sender": "user",
                "user_id": user_id,
                "agent_id": agent_id,
                "sequence_id": sequence_id
            })

        try:
            llm_response = await self.llm_client.generate(
                model=agent.config.get("model_name", settings.FALLBACK_MODEL),
                prompt=full_prompt,
                system_prompt=agent.config.get("system_prompt", "You are a helpful assistant"),
                temperature=agent.config.get("temperature", 0.7),
                max_tokens=agent.config.get("max_length", settings.MAX_TOKENS)
            )
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return {"type": "error", "error_type": "generation_error", "content": "Failed to generate response"}

        await create_chat_message(db, {
            "conversation_id": conversation_id,
            "content": llm_response.get("content", ""),
            "sender": "agent",
            "user_id": user_id,
            "agent_id": agent_id,
            "sequence_id": sequence_id + 1
        })

        return {
            "type": "response",
            "content": llm_response.get("content", ""),
            "agent_id": agent_id,
            "metadata": {
                "model": llm_response.get("model"),
                "tokens_used": llm_response.get("usage", {}).get("total_tokens", 0),
                "cost": llm_response.get("cost", 0),
                "timestamp": datetime.datetime.now().isoformat(),
                "sources": await get_knowledge_sources(agent.knowledge_bases)
            }
        }

    #SH: Fallback context
    async def _fallback_context(self, knowledge_bases: List[KnowledgeBase]) -> str:
        texts = []
        for kb in knowledge_bases:
            try:
                file_path = os.path.join(settings.KNOWLEDGE_DIR, kb.filename)
                loader = PyPDFLoader(file_path) if kb.content_type == "application/pdf" else TextLoader(file_path)
                docs = loader.load()
                chunks = text_splitter.split_documents(docs)
                texts.extend([chunk.page_content for chunk in chunks[:settings.FALLBACK_CHUNKS]])
            except Exception as e:
                logger.warning(f"Loading KB failed {kb.id}: {e}")
        return "\n\n".join(texts)

    #SH: Process public widget message
    async def process_public_widget_message(
        self,
        db: AsyncSession,
        agent_id: int,
        message: str
    ) -> Dict[str, Any]:
        try:
            if len(message) > settings.WIDGET_MAX_MESSAGE_LENGTH:
                return {
                    "content": f"Message exceeds maximum length of "
                               f"{settings.WIDGET_MAX_MESSAGE_LENGTH} characters",
                    "error": "message_too_long"
                }

            agent = await self.verify_public_agent(db, agent_id)
            if not agent:
                return {
                    "content": "Agent not found or not publicly accessible",
                    "error": "agent_not_found"
                }

            theme_color = agent.theme_color
            greeting    = agent.greeting_message
            is_public   = agent.is_public

            try:
                vector_store = get_organization_vector_store(agent.organization_id)
                docs = await vector_store.asimilarity_search(message, k=3)
                context = "\n".join(doc.page_content for doc in docs)
            except Exception as e:
                logger.warning(f"RAG context failed: {e}")
                context = await self._fallback_context(agent.knowledge_bases)

            llm_resp = await self.llm_client.generate(
                model=agent.config.get("model_name", settings.WIDGET_DEFAULT_MODEL),
                prompt=f"Context: {context}\n\nQuestion: {message}",
                system_prompt=agent.config.get("system_prompt", "You are a helpful assistant"),
                temperature=agent.config.get("temperature", 0.7),
                max_tokens=agent.config.get("max_length", 500)
            )

            return {
                "content": llm_resp["content"],
                "metadata": {
                    "model":          llm_resp.get("model"),
                    "tokens_used":    llm_resp.get("usage", {}).get("total_tokens", 0),
                    "sources":        [d.metadata.get("source", "") for d in docs],
                    "theme_color":    theme_color,
                    "greeting_message": greeting,
                    "is_public":      is_public
                }
            }

        except Exception as e:
            logger.error(f"Error processing public widget message: {e}", exc_info=True)
            return {
                "content": "Sorry, I encountered an error processing your message",
                "error": str(e)
            }