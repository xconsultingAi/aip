# SH: Fixed LLMService initialization with config + added proper OpenAI integration
from langchain_openai import OpenAIEmbeddings  # SH: Updated import
from app.core.config import settings
from app.core.llm import OpenAIClient
from app.core.exceptions import LLMServiceError
# SH: Use existing OpenAIClient

async def generate_embeddings(text: str):
    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY
    )
    return await embeddings.embed_query(text)

class LLMService:
    def __init__(self, agent_config: dict):  # SH: Accept config parameter
        self.config = agent_config
        self.client = OpenAIClient()  # SH: Use pre-configured client

    async def generate_response(self, prompt: str) -> dict:
        """SH: Proper implementation using your original OpenAIClient"""
        try:
            response = await self.client.generate(
                model=self.config.get("model_name", settings.FALLBACK_MODEL),
                prompt=prompt,
                system_prompt=self.config.get("system_prompt", "You are a helpful assistant"),
                temperature=self.config.get("temperature", 0.7),
                max_tokens=self.config.get("max_length", 500)
            )
            return response
        except Exception as e:
            raise LLMServiceError(str(e))