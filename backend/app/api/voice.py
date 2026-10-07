from fastapi import APIRouter
from pydantic import BaseModel
from app.services.voice_adapter import VoiceAdapter

router = APIRouter()
adapter = VoiceAdapter()

class STTRequest(BaseModel):
    # base64 audio or placeholder
    audio_b64: str | None = None

class TTSRequest(BaseModel):
    text: str
    voice: str | None = None

@router.post("/stt")
async def stt(req: STTRequest):
    # Devuelve texto transcrito (placeholder)
    text = await adapter.transcribe(req.audio_b64)
    return {"text": text}

@router.post("/tts")
async def tts(req: TTSRequest):
    # Devuelve un placeholder o URL al audio generado
    audio_ref = await adapter.synthesize(req.text, req.voice)
    return {"audio": audio_ref}
