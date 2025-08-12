import logging
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class SpeechToText:
    def __init__(self):
        self.api_key = settings.SPEECH_TO_TEXT_API_KEY
        self.api_url = settings.SPEECH_TO_TEXT_API_URL

    async def transcribe(self, audio_url: str) -> Optional[str]:
        """
        Convert speech from audio URL to text using a speech-to-text API
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json={"audio_url": audio_url},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30
                )
                response.raise_for_status()
                return response.json().get("text")
        
        except Exception as e:
            logger.error(f"Speech-to-text failed for {audio_url}: {str(e)}")
            return None