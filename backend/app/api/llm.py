from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.adapter_ollama import OllamaAdapter
from app.config import settings

router = APIRouter()
adapter = OllamaAdapter(settings.OLLAMA_URL)

class GenerateRequest(BaseModel):
    model: str | None = None
    messages: list | None = None

@router.post("/generate")
async def generate(req: GenerateRequest):
    model = req.model or "llama2"
    messages = req.messages or []
    try:
        resp = await adapter.generate(model, messages)
        return resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
