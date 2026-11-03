from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.adapter_ollama import OllamaAdapter
from app.config import settings

router = APIRouter()
adapter = OllamaAdapter(settings.OLLAMA_URL, settings.OLLAMA_KEEP_ALIVE)

class GenerateRequest(BaseModel):
    model: str | None = None
    messages: list | None = None

@router.post("/generate")
async def generate(req: GenerateRequest):
    # Antes venia "llama2" fijado: un modelo que no está descargado en tu máquina.
    model = req.model or settings.OLLAMA_MODEL
    messages = req.messages or [
        {"role": "user", "content": "Hola CORT, preséntate en una línea."}
    ]
    try:
        resp = await adapter.generate(model, messages)
        return resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
