import logging
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.core.exceptions import LLMServiceError
from app.models.agent import AgentConfigSchema

logger = logging.getLogger("llm_service")

class LLMService:
    def __init__(self, agent_config: AgentConfigSchema):
        self.agent_config = agent_config
        self.headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def generate_response(self, prompt: str) -> dict:
    # Generate response with gpt-4 with automatic fallback
        payload = {
            "model": self.agent_config.model_name,
            "messages": [
                {"role": "system", "content": self.agent_config.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.agent_config.temperature,
            "max_tokens": min(
                self.agent_config.max_length, 
                settings.MAX_TOKENS_LIMIT - len(prompt) // 4  # Approx token count
            )
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.OPENAI_API_URL,
                    headers=self.headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Logging for monitoring
                    self._log_interaction(prompt, data)
                    
                    return {
                        "content": data['choices'][0]['message']['content'],
                        "tokens_used": data['usage']['total_tokens'],
                        "model_used": self.agent_config.model_name
                    }

        except aiohttp.ClientError as e:
            logger.error(f"API Connection Error: {str(e)}")
            if self.agent_config.model_name != settings.FALLBACK_MODEL:
                logger.info("Trying fallback model...")
                self.agent_config.model_name = settings.FALLBACK_MODEL
                return await self.generate_response(prompt)
            raise LLMServiceError("LLM service unavailable")

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise LLMServiceError("Error in LLM response generation")

    def _log_interaction(self, prompt: str, response: dict):
        """API interactions ko detail mein log karein"""
        logger.info(
            f"LLM Interaction | Model: {self.agent_config.model_name} | "
            f"Prompt: {prompt[:50]}... | "
            f"Tokens Used: {response['usage']['total_tokens']} | "
            f"Cost Estimate: ${self._calculate_cost(response['usage']):.4f}"
        )

    def _calculate_cost(self, usage: dict) -> float:
        """Usage data se cost estimate karein"""
        model_pricing = {
            "gpt-4": 0.03/1000,
            "gpt-3.5-turbo": 0.002/1000
        }
        model = self.agent_config.model_name
        return usage['total_tokens'] * model_pricing.get(model, 0.03/1000)