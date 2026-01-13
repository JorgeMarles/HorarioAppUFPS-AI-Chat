from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str
    model_name: str = "gemini-1.5-flash"
    redis_url: str = "redis://localhost:6379/0"
    backend_url: str = "http://localhost:8081/"
    chat_active: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

@lru_cache()
def get_settings() -> Settings:
    return Settings()
