from pydantic_settings import BaseSettings
from typing import List, Dict, Any

class Settings(BaseSettings):
    #MJ: Added these in .env
    ###### START ####
    APP_NAME: str = "My FastAPI App"
    DEBUG: bool = False
    CLERK_JWKS_URL: str
    CLERK_ISSUER: str 
    CLERK_SECRET_KEY: str
    CLERK_PUBLISHABLE_KEY: str
    ALLOWED_ORIGINS: str = "*"  # CORS
    DATABASE_URL: str = "DATABASE_URL"  # a default if not in .env
    PRODUCTION: bool = False

    #SH: for API key
    OPENAI_API_KEY: str 
    OPENAI_API_URL: str = "https://api.openai.com/v1/chat/completions"
    FALLBACK_MODEL: str = "gpt-3.5-turbo"
    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 30
    MAX_TOKENS_LIMIT: int = 4000

    #SH: for Knowledge base
    MAX_FILE_SIZE: int = 10_485_760
    ALLOWED_CONTENT_TYPES: List[str] = ["application/pdf", "text/plain"]
    CHUNK_SIZE: int = 1000
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    KNOWLEDGE_DIR: str = "data"
    CHROMA_DIR: str = "chroma"
  
    #Sh: For Websockets
    WEBSOCKET_TIMEOUT: int = 300  # 5 minutes
    MAX_CONNECTIONS: int = 1000
    MESSAGE_RETRY_LIMIT: int = 3
    WEBSOCKET_MAX_MESSAGE_SIZE: int = 1024 * 1024  # 1MB
    WEBSOCKET_RATE_LIMIT: int = 10  # Messages per second
    WEBSOCKET_OPTIMIZATION: Dict[str, Any] = {
        'message_cache_size': 250,
        'max_pending_messages': 50,
        'priority_queues': True
    }
    WEBSOCKET_BATCH_SIZE: int = 10
    MESSAGE_COMPRESSION: bool = True
    PRIORITY_THRESHOLD: int = 5 
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    EMAIL_SENDER: str = "no-reply@example.com" 
    ###### END ####

    # JWT_SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e"
    # JWT_ALGORITHM: str = "HS256"


    class Config:
        env_file = ".env"

settings = Settings()  