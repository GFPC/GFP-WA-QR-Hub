from pydantic_settings import BaseSettings
from pydantic import SecretStr
from typing import Optional


class Settings(BaseSettings):
    # Telegram Bot
    BOT_TOKEN: SecretStr
    
    # FastAPI
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_SECRET: SecretStr
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./gfp_watcher.db"
    
    # Redis
    REDIS_URL: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "DEBUG"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings() 