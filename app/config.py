from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# Cargar .env manualmente
load_dotenv()

class Settings(BaseSettings):
    gemini_api_key: str
    model_name: str = "gemini-1.5-flash"

    class Config:
        env_prefix = ""  # direct names
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        env_file_encoding = 'utf-8'

@lru_cache()
def get_settings() -> Settings:
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        model_name=os.getenv("MODEL_NAME", "gemini-1.5-flash")
    )
