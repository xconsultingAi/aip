import datetime
import logging
import os
from typing import Dict, Any, Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.core.llm import OpenAIClient
from app.core.exceptions import openai_exception
from app.core.config import settings
from app.db.models.agent import Agent
from app.db.models.knowledge_base import KnowledgeBase
from app.core.vector_store import get_organization_vector_store
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

class WidgetService:
    def __init__(self):
        self.llm_client = OpenAIClient()

    async def process_widget_message(
        self,
        agent_id: int,
        message: str,
        db: AsyncSession,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            # 1. Get Agent Configuration with knowledge bases
            agent = await self._get_agent_with_knowledge(agent_id, db)
            if not agent:
                return self._error_response("Agent not available", "agent_not_found")

            # 2. Validate input
            validation_error = self._validate_input(message)
            if validation_error:
                return validation_error

            # 3. Prepare context with RAG if knowledge bases exist
            context = await self._prepare_context(agent, message)
            full_prompt = f"{context}\n\nVisitor: {message}"

            # 4. Generate response
            response = await self._generate_response(agent, full_prompt)

            # 5. Format and return successful response
            return self._format_success_response(agent_id, response)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing widget message: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process message"
            )

    async def _get_agent_with_knowledge(
        self, 
        agent_id: int, 
        db: AsyncSession
    ) -> Optional[Agent]:
        """Retrieve agent with loaded knowledge bases"""
        try:
            result = await db.execute(
                select(Agent)
                .where(Agent.id == agent_id)
                .options(selectinload(Agent.knowledge_bases))
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching agent: {str(e)}")
            return None

    def _validate_input(self, message: str) -> Optional[Dict[str, Any]]:
        """Validate the incoming message"""
        if not message or len(message.strip()) == 0:
            return self._error_response("Message cannot be empty", "validation_error")

        if len(message) > settings.WIDGET_MAX_MESSAGE_LENGTH:
            return self._error_response(
                f"Message exceeds {settings.WIDGET_MAX_MESSAGE_LENGTH} characters",
                "validation_error"
            )
        return None

    async def _prepare_context(self, agent: Agent, message: str) -> str:
        if not agent.knowledge_bases:
            return ""
        try:
            vector_store = get_organization_vector_store(agent.organization_id)
            docs = await vector_store.asimilarity_search(message, k=3)
            return "\n".join([doc.page_content for doc in docs])
        except Exception as e:
            logger.warning(f"Failed to prepare RAG context: {str(e)}")
            return await self._fallback_context(agent.knowledge_bases)

    async def _fallback_context(self, knowledge_bases: List[KnowledgeBase]) -> str:
        context = []
        for kb in knowledge_bases:
            try:
                file_path = os.path.join(settings.KNOWLEDGE_DIR, kb.filename)
                loader = PyPDFLoader(file_path) if kb.content_type == "application/pdf" else TextLoader(file_path)
                documents = loader.load()
                chunks = text_splitter.split_documents(documents)
                context.extend([chunk.page_content for chunk in chunks[:3]])
            except Exception as e:
                logger.warning(f"Failed to load knowledge base {kb.id}: {str(e)}")
        return "\n\n".join(context)

    async def _generate_response(
        self, 
        agent: Agent, 
        prompt: str
    ) -> Dict[str, Any]:
        try:
            return await self.llm_client.generate(
                model=agent.config.get("model_name", settings.FALLBACK_MODEL),
                prompt=prompt,
                system_prompt=agent.config.get("system_prompt", "You are a helpful assistant"),
                temperature=agent.config.get("temperature", 0.7),
                max_tokens=agent.config.get("max_length", 150)
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            raise openai_exception("Failed to generate response")

    def _format_success_response(
        self,
        agent_id: int,
        llm_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "type": "response",
            "content": llm_response["content"],
            "agent_id": agent_id,
            "metadata": {
                "model": llm_response.get("model"),
                "tokens_used": llm_response.get("usage", {}).get("total_tokens", 0),
                "cost": llm_response.get("cost", 0),
                "timestamp": datetime.datetime.now().isoformat()
            }
        }

    def _error_response(self, message: str, error_type: str) -> Dict[str, Any]:
        return {
            "type": "error",
            "error_type": error_type,
            "content": message,
            "timestamp": datetime.datetime.now().isoformat()
        }