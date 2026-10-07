import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://localhost:11434")

settings = Settings()
