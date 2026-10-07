## Voice & Embeddings (added)

This branch adds optional local STT (Whisper) and TTS (Coqui/TTS) integrations and a basic embeddings+FAISS memory pipeline.

Quick setup for voice & embeddings:

1) Install additional Python deps (if not using docker):
   cd backend
   source .venv/bin/activate
   pip install -r requirements.txt

2) To enable Whisper STT at runtime, set environment variable ENABLE_WHISPER=1 and have the `whisper` CLI available (openai-whisper package provides it). Example:
   ENABLE_WHISPER=1 .venv/bin/python -m uvicorn app.main:app --reload

3) To enable TTS with Coqui, set ENABLE_TTS=1 and ensure `tts` CLI is installed (Coqui TTS). Example:
   ENABLE_TTS=1 .venv/bin/python -m uvicorn app.main:app --reload

4) Embeddings: sentence-transformers + faiss are used. Memory add will create embeddings when using the embeddings service endpoints. Example add/query:
   curl -X POST http://localhost:8000/api/memory/add -H "Content-Type: application/json" -d '{"user":"sandra","content":"Mi primer recuerdo"}'
   curl 'http://localhost:8000/api/memory/query?q=primer&user=sandra&k=5'

Docker compose for dev:
   docker-compose -f docker-compose.dev.yml up --build

Notes:
- These are optional integrations. If you don't enable them, placeholders will be used (non-invasive defaults).
- Whisper/Coqui can be heavy; use small models for testing.
