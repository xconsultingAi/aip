import logging
from typing import Dict
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import openai
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.exceptions import OpenAIException

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout=settings.OPENAI_TIMEOUT
        )

    @retry(
        stop=stop_after_attempt(settings.OPENAI_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APITimeoutError, openai.APIConnectionError)),
    )
    async def generate(self, model: str, prompt: str, system_prompt: str, temperature: float, max_tokens: int) -> Dict:
        """Generate Response with OpenaAI API key"""
        try:
            logger.info(f"OpenAI request - Model: {model}, Tokens: {max_tokens}")
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=min(max_tokens, settings.MAX_ALLOWED_TOKENS),
            )

            logger.info(f"Response received - Tokens used: {response.usage}")
            return {
                "content": response.choices[0].message.content,
                "usage": response.usage.model_dump(),
                "model": model
            }
        except openai.AuthenticationError:
            logger.error("Authentication error")
            raise OpenAIException("Invalid API credentials")
        except openai.RateLimitError:
            logger.warning("Rate limit exceeded")
            raise OpenAIException("API rate limit exceeded")
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise OpenAIException("API error occurred")
