from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.core.llm import OpenAIClient
from app.core.exceptions import llm_service_error, invalid_api_key_error
from app.db.models.knowledge_base import KnowledgeBase
from app.core.vector_store import get_vector_store
from fastapi import HTTPException, status
import openai
import os
from langchain.document_loaders import PyPDFLoader, TextLoader
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
    knowledge_bases: list
):
    all_chunks = []
    for kb in knowledge_bases:
        file_path = os.path.join(settings.KNOWLEDGE_DIR, kb.filename)
        if kb.content_type == "application/pdf":
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path)
        documents = loader.load()
        chunks = text_splitter.split_documents(documents)
        all_chunks.extend(chunks)
    
    # Select relevant chunks based on similarity
    vector_store = get_vector_store()
    docs = await vector_store.asimilarity_search(prompt, k=5)
    context = "\n".join([doc.page_content for doc in docs])
    
    full_prompt = f"{context}\n\n{prompt}"
    
    # Call the LLM API
    try:
        client = OpenAIClient()
        response = await client.generate(
            model=agent_config.get("model_name", "gpt-4"),
            prompt=full_prompt,
            system_prompt=agent_config.get("system_prompt", "You are a helpful assistant"),
            temperature=agent_config.get("temperature", 0.7),
            max_tokens=agent_config.get("max_length", 500)
        )
        return response
    except openai.AuthenticationError:
        raise invalid_api_key_error()
    except (openai.APIError, openai.APITimeoutError, openai.APIConnectionError) as e:
        raise llm_service_error(str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}"
        )

async def generate_llm_response_with_knowledge(
    prompt: str,
    config: dict,
    knowledge_base: KnowledgeBase
) -> dict:
    """
    Generate a response using the agent's configuration and knowledge base.
    """
    try:
        # Combine the prompt with the knowledge base content
        context = knowledge_base.content  
        full_prompt = f"{context}\n\n{prompt}"

        # Call the LLM API
        client = OpenAIClient()
        response = await client.generate(
            model=config.get("model_name", "gpt-4"),
            prompt=full_prompt,
            system_prompt=config.get("system_prompt", "You are a helpful assistant"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_length", 500)
        )
        return response
    except openai.AuthenticationError:
        raise invalid_api_key_error()
    except (openai.APIError, openai.APITimeoutError, openai.APIConnectionError) as e:
        raise llm_service_error(str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}"
        )