from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    #MJ: Added these in .env
    ###### START ####
    APP_NAME: str = "My FastAPI App"
    DEBUG: bool = False
    CLERK_JWKS_URL: str
    CLERK_SECRET_KEY: str
    ALLOWED_ORIGINS: str = "*"  # CORS
    DATABASE_URL: str = "DATABASE_URL"  # a default if not in .env
    PRODUCTION: bool = False
    

    OPENAI_API_KEY: str
    OPENAI_API_URL: str = "https://api.openai.com/v1/chat/completions"
    FALLBACK_MODEL: str = "gpt-3.5-turbo"
    MAX_RETRIES: int = 3
    OPENAI_TIMEOUT: int = 30
    MAX_TOKENS_LIMIT: int = 2000
    
    ###### END ####

    # JWT_SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e"
    # JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    EMAIL_SENDER: str = "no-reply@example.com"

    class Config:
        env_file = ".env"

settings = Settings()
