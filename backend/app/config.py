import os
import json

def _modelo_por_defecto() -> str:
    """Orden de prioridad del modelo local de CORT.

    1. variable de entorno CORT_MODEL
    2. ~/.cort/cort_config.json  -> clave "ollama_model"  (la que ya usa tu app)
    3. "qwen3:0.6b"
    """
    env = os.environ.get("CORT_MODEL")
    if env:
        return env
    ruta = os.path.expanduser("~/.cort/cort_config.json")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if cfg.get("ollama_model"):
            return str(cfg["ollama_model"])
    except (OSError, ValueError):
        pass
    return "qwen3:0.6b"

class Settings:
    """Simple settings holder that reads from environment variables.
    Using a plain class avoids dependency on pydantic/pydantic-settings so the
    backend runs reliably on systems with different pydantic versions.
    """
    OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = _modelo_por_defecto()
    # Protege la laptop: libera el modelo de RAM si nadie lo usa en 2 minutos.
    OLLAMA_KEEP_ALIVE: str = os.environ.get("CORT_KEEP_ALIVE", "2m")

settings = Settings()
