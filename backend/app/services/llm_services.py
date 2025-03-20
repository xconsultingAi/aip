from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.core.llm import OpenAIClient
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.knowledge_base import agent_knowledge
import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

async def generate_embeddings(text: str):
    """
    Generate embeddings for the given text using OpenAI's embeddings model.
    """
    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY
    )
    return await embeddings.embed_query(text)

async def generate_llm_response(
    prompt: str,
    agent_config: dict,
    knowledge_bases: list,
    db: AsyncSession
) -> dict:
    """
    Generate a response using the agent's configuration and knowledge base.
    """
    try:
        # Combine content from all linked knowledge bases
        context = ""
        for kb in knowledge_bases:
            file_path = os.path.join(settings.KNOWLEDGE_DIR, kb.filename)
            if kb.content_type == "application/pdf":
                loader = PyPDFLoader(file_path)
            else:
                loader = TextLoader(file_path)
            documents = loader.load()
            chunks = text_splitter.split_documents(documents)
            context += "\n".join([chunk.page_content for chunk in chunks]) + "\n\n"

        # Combine context with the prompt
        full_prompt = f"{context}\n\n{prompt}"

        # Call the LLM API
        client = OpenAIClient()
        response = await client.generate(
            model=agent_config.get("model_name", "gpt-4"),
            prompt=full_prompt,
            system_prompt=agent_config.get("system_prompt", "You are a helpful assistant"),
            temperature=agent_config.get("temperature", 0.7),
            max_tokens=agent_config.get("max_length", 500)
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}"
        )