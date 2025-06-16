from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Telegram settings
    TELEGRAM_BOT_TOKEN: str
    ALLOWED_TG_IDS: List[int]
    
    # HTTP Server settings
    SECRET_KEY: str
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # WhatsApp settings
    WHATSAPP_API_URL: str = "https://api.whatsapp.com/v1"
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./app.db"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings() 