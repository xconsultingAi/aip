import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import openai
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.exceptions import llm_service_error, invalid_api_key_error, openai_exception

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.REQUEST_TIMEOUT,
            max_retries=settings.MAX_RETRIES,
        )

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APITimeoutError, openai.APIConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def generate(self, model: str, prompt: str, system_prompt: str, temperature: float, max_tokens: int) -> dict:
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=min(max_tokens, settings.MAX_TOKENS_LIMIT),
            )
            
            cost = self._calculate_cost(response.usage, model)
            logger.info(f"API Call | Model: {model} | Tokens: {response.usage.total_tokens} | Cost: ${cost:.5f}")
            
            return {
                "content": response.choices[0].message.content,
                "usage": response.usage.model_dump(),
                "model": model,
                "cost": cost,
            }
        except openai.AuthenticationError:
            logger.error("Authentication error")
            raise invalid_api_key_error()
        except openai.RateLimitError:
            logger.warning("Rate limit exceeded")
            raise llm_service_error("API rate limit exceeded")
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise openai_exception("API error occurred")

    def _calculate_cost(self, usage, model):
        pricing = {
            "gpt-4": {"input": 0.03/1000, "output": 0.06/1000},
            "gpt-3.5-turbo": {"input": 0.0015/1000, "output": 0.002/1000},
        }
        model_pricing = pricing.get(model, pricing["gpt-4"])
        return (usage.prompt_tokens * model_pricing["input"]) + (usage.completion_tokens * model_pricing["output"])