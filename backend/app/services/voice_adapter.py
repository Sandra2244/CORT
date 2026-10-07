class VoiceAdapter:
    """Adaptador placeholder para STT/TTS. En próximas iteraciones se integrará Whisper/Coqui/Coqui TTS u OpenTTS."""
    async def transcribe(self, audio_b64: str | None):
        # Placeholder: en lugar de audio, devolvemos texto fijo
        return "[transcripción placeholder]"

    async def synthesize(self, text: str, voice: str | None = None):
        # Placeholder: devolvemos un pequeño descriptor que el frontend puede usar
        return {"type":"placeholder","text_length": len(text), "voice": voice}
