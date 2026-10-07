import os

class Settings:
    """Simple settings holder that reads from environment variables.
    Using a plain class avoids dependency on pydantic/pydantic-settings so the
    backend runs reliably on systems with different pydantic versions.
    """
    OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://localhost:11434")

settings = Settings()
