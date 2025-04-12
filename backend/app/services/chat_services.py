from tenacity import retry, stop_after_attempt, wait_exponential
from fastapi import WebSocketException, status
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from app.core.llm import OpenAIClient
from app.db.repository.agent import get_agent
from app.db.repository.chat import create_chat_message
from app.db.database import AsyncSession
from app.core.vector_store import get_organization_vector_store
import logging

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
    db: AsyncSession
) -> dict:
    #SH: Process user message and generate agent response
    try:
        #SH: Step 1: Rate limit large messages
        if len(message) > 1000:
            raise WebSocketException(
                code=status.WS_1009_MESSAGE_TOO_BIG,
                reason="Message exceeds 1000 characters"
            )

        #SH: Step 2: Fetch agent and verify access
        agent = await get_agent(db, agent_id, user_id)
        if not agent:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Agent not found"
            )
        await db.refresh(agent, ["knowledge_bases"])  # Load related knowledge bases

        #SH: Step 3: Create RAG
        vector_store = get_organization_vector_store(agent.organization_id)
        docs = await vector_store.asimilarity_search(message, k=3)
        context = "\n".join([doc.page_content for doc in docs])
        full_prompt = f"Context: {context}\n\nQuestion: {message}"

        #SH: Step 4: Save user message in database
        await create_chat_message(db, {
            "content": message,
            "sender": "user",
            "user_id": user_id,
            "agent_id": agent_id
        })

        #SH: Step 5: Generate agent response using LLM
        llm_client = OpenAIClient()
        response = await llm_client.generate(
            model=agent.config.get("model_name", "gpt-4"),
            prompt=full_prompt,
            system_prompt=agent.config.get("system_prompt", "You are a helpful assistant"),
            temperature=agent.config.get("temperature", 0.7),
            max_tokens=agent.config.get("max_length", 500)
        )

        #SH: Step 6: Save agent's reply in chat history
        await create_chat_message(db, {
            "content": response["content"],
            "sender": "agent",
            "user_id": user_id,
            "agent_id": agent_id
        })

        #SH: Step 7: Return response to be sent to frontend
        return {
            "content": response["content"],
            "metadata": {
                "model": agent.config.get("model_name"),
                "tokens_used": response.get("usage", {}).get("total_tokens", 0),
                "cost": response.get("cost", 0),
                "sources": await get_knowledge_sources(agent.knowledge_bases)
            }
        }

    except WebSocketException as e:
        #SH: Raise WebSocket errors
        raise e
    except Exception as e:
        #SH: server-side error
        logger.exception(f"Error processing agent message: {str(e)}", exc_info=True)
        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR,
            reason=str(e)
        )

#SH: function to extract metadata from knowledge bases
async def get_knowledge_sources(knowledge_bases):
    #SH: Extract metadata from knowledge base
    return [{
        "filename": kb.filename,
        "uploaded_at": kb.uploaded_at.isoformat(),
        "chunk_count": kb.chunk_count
    } for kb in knowledge_bases]


#SH: Fallback function to build RAG context by loading full files
async def get_rag_context(knowledge_bases):
    #SH: Generate RAG context from knowledge bases
    context = []
    for kb in knowledge_bases:
        #SH: Load PDFs or plain text depending on content type
        loader = PyPDFLoader(kb.file_path) if kb.content_type == "application/pdf" else TextLoader(kb.file_path)
        documents = loader.load()
        context.extend([doc.page_content for doc in documents])
    return "\n\n".join(context[:5])  # Return top 5 chunks of content

#SH: Utility to verify agent access
async def verify_agent_access(db: AsyncSession, agent_id: int, user_id: str):
    logger.info(f"Verifying access to agent {agent_id}")
    agent = await get_agent(db, agent_id, user_id)

    if not agent:
        logger.error(f"Agent {agent_id} not found or access denied")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Agent not found or access denied"
        )

    logger.info(f"Access granted to agent {agent_id}")
    return agent
