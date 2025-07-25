from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from app.core.llm import OpenAIClient
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import openai
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

async def generate_embeddings(text: str):
    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY
    )
    return await embeddings.embed_query(text)

def _build_personality_prompt(agent_config: Dict) -> str:
    """Construct personality-specific prompt instructions"""
    traits = agent_config.get("personality_traits", [])
    instructions = []
    
    for trait in traits:
        if trait in settings.PERSONALITY_PROMPT_TEMPLATES:
            instructions.append(settings.PERSONALITY_PROMPT_TEMPLATES[trait])
    
    if instructions:
        return "\n".join(instructions)
    return ""

def _adjust_for_personality(agent_config: Dict, base_params: Dict) -> Dict:
    """Adjust generation parameters based on personality traits"""
    traits = agent_config.get("personality_traits", [])
    params = base_params.copy()
    
    for trait in traits:
        if trait in settings.PERSONALITY_PARAM_ADJUSTMENTS:
            adj = settings.PERSONALITY_PARAM_ADJUSTMENTS[trait]
            params["temperature"] = max(0.1, min(1.0, 
                params.get("temperature", 0.7) + adj["temperature"]))
            params["max_tokens"] = int(params.get("max_tokens", 500) * 
                adj["max_tokens_multiplier"])
    
    return params

async def generate_llm_response(
    prompt: str,
    agent_config: Dict,
    knowledge_bases: List,
    db: AsyncSession
) -> Dict:
    try:
        # Build knowledge context
        context = ""
        for kb in knowledge_bases:
            file_path = os.path.join(settings.KNOWLEDGE_DIR, kb.filename)
            loader = PyPDFLoader(file_path) if kb.content_type == "application/pdf" else TextLoader(file_path)
            documents = loader.load()
            chunks = text_splitter.split_documents(documents)
            context += "\n".join([chunk.page_content for chunk in chunks]) + "\n\n"

        # Prepare base parameters
        base_params = {
            "temperature": agent_config.get("temperature", 0.7),
            "max_tokens": agent_config.get("max_length", 500)
        }

        # Apply personality adjustments
        generation_params = _adjust_for_personality(agent_config, base_params)
        personality_prompt = _build_personality_prompt(agent_config)

        # Build final system prompt
        system_prompt = agent_config.get("system_prompt", "You are a helpful assistant")
        if personality_prompt:
            system_prompt += f"\n\nPersonality Guidelines:\n{personality_prompt}"
        if agent_config.get("custom_prompt"):
            system_prompt += f"\n\nCustom Instructions:\n{agent_config['custom_prompt']}"

        # Generate response
        client = OpenAIClient()
        response = await client.generate(
            model=agent_config.get("model_name", "gpt-4"),
            prompt=f"{context}\n\n{prompt}",
            system_prompt=system_prompt,
            **generation_params
        )

        # Add personality metadata
        response["personality_metadata"] = {
            "applied_traits": agent_config.get("personality_traits", []),
            "generation_params": generation_params,
            "prompt_template": system_prompt
        }

        return response

    except openai.RateLimitError:
        logger.error("OpenAI rate limit exceeded")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI service rate limit exceeded"
        )
    except Exception as e:
        logger.error(f"LLM generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}"
        )

async def generate_personality_preview(
    prompt: str,
    agent_config: Dict,
    db: AsyncSession
) -> Dict:
    """Generate preview with personality settings (no knowledge base)"""
    return await generate_llm_response(
        prompt=prompt,
        agent_config=agent_config,
        knowledge_bases=[],
        db=db
    )