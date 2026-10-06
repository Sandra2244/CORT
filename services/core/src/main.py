#!/usr/bin/env python3
"""
CORT Core Service
Real local LLM integration via Ollama with memory and personality control.
"""

import os
import json
from datetime import datetime
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title='CORT Core',
    description='Cognitive Operating Reactive Technology - local LLM core',
    version='0.1.0',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class Message(BaseModel):
    content: str
    author: str = 'user'
    timestamp: Optional[str] = None
    context: Optional[dict] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class ResponseMessage(BaseModel):
    content: str
    author: str = 'cort'
    timestamp: str
    emotion: str = 'neutral'
    status: str = 'success'


class PersonalityConfig(BaseModel):
    tone: str = 'friendly'
    verbose: bool = True
    language: str = 'en'


class OllamaConfig(BaseModel):
    base_url: str = 'http://localhost:11434'
    model: str = 'mistral'
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40


class CORTMemory:
    def __init__(self):
        self.conversation_history: list[dict] = []
        self.short_term_memory: list[dict] = []
        self.user_context: dict = {'name': 'User', 'location': 'Unknown'}
        self.personality = PersonalityConfig()
        self.ollama_config = OllamaConfig()
        self.mood = 'neutral'
        self.active_skills: list[str] = []

    def add_message(self, role: str, content: str, emotion: str = 'neutral') -> None:
        entry = {
            'role': role,
            'content': content,
            'emotion': emotion,
            'timestamp': datetime.now().isoformat(),
        }
        self.conversation_history.append(entry)
        self.short_term_memory.append(entry)
        if len(self.short_term_memory) > 8:
            self.short_term_memory.pop(0)

    def build_system_prompt(self) -> str:
        tone_map = {
            'friendly': 'You are CORT, a warm and engaging personal AI companion. Be helpful, friendly, and concise.',
            'professional': 'You are CORT, a professional AI assistant. Be clear, precise, and useful.',
            'technical': 'You are CORT, a technical expert. Give practical, structured technical answers with useful details.',
            'creative': 'You are CORT, a creative AI assistant. Be imaginative, vivid, and thoughtful.',
        }
        base = tone_map.get(self.personality.tone, tone_map['friendly'])
        ctx = (
            f"Current context: user={self.user_context.get('name', 'User')}, mood={self.mood}, "
            f"active_skills={self.active_skills}"
        )
        return f"{base}\n{ctx}"


memory = CORTMemory()

PERSONALITY_PRESETS = {
    'friendly': {'description': 'warm and conversational'},
    'professional': {'description': 'clear and structured'},
    'technical': {'description': 'deep technical detail'},
    'creative': {'description': 'imaginative and expressive'},
}


def detect_emotion_from_text(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ['wow', 'amazing', 'great', 'love', 'excited']):
        return 'excited'
    if any(word in lower for word in ['think', 'analyze', 'hmm', 'consider']):
        return 'thoughtful'
    if any(word in lower for word in ['sad', 'sorry', 'upset', 'bad']):
        return 'sad'
    if any(word in lower for word in ['haha', 'funny', 'joke', 'laugh']):
        return 'happy'
    if any(word in lower for word in ['why', 'how', 'what', 'can you']):
        return 'curious'
    return 'neutral'


class OllamaEngine:
    def __init__(self, config: OllamaConfig):
        self.config = config
        self.client = httpx.Client(timeout=120.0)

    def is_available(self) -> bool:
        try:
            response = self.client.get(f"{self.config.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            response = self.client.get(f"{self.config.base_url}/api/tags")
            if response.status_code == 200:
                payload = response.json()
                return [m['name'] for m in payload.get('models', [])]
        except Exception:
            pass
        return []

    def generate(self, prompt: str, system: Optional[str] = None) -> Optional[str]:
        try:
            payload = {
                'model': self.config.model,
                'prompt': prompt,
                'system': system or memory.build_system_prompt(),
                'stream': False,
                'temperature': self.config.temperature,
                'top_p': self.config.top_p,
                'top_k': self.config.top_k,
            }
            response = self.client.post(f"{self.config.base_url}/api/generate", json=payload)
            if response.status_code == 200:
                data = response.json()
                return (data.get('response') or '').strip()
        except Exception as e:
            print(f'Ollama error: {e}')
        return None


ollama = OllamaEngine(memory.ollama_config)


@app.get('/health')
async def health():
    available = ollama.is_available()
    return {
        'status': 'ok',
        'service': 'cort-core',
        'version': '0.1.0',
        'timestamp': datetime.now().isoformat(),
        'ollama': {
            'available': available,
            'base_url': memory.ollama_config.base_url,
            'current_model': memory.ollama_config.model,
            'available_models': ollama.list_models() if available else [],
        },
        'memory_state': {
            'history_length': len(memory.conversation_history),
            'mood': memory.mood,
            'personality': memory.personality.dict(),
        },
    }


@app.post('/chat')
async def chat(message: Message):
    memory.add_message(message.author, message.content)

    if not ollama.is_available():
        fallback = (
            'Ollama is not running right now. Start it with: ollama serve. '
            'I can still answer in fallback mode, but the local LLM is offline.'
        )
        return ResponseMessage(
            content=fallback,
            emotion='neutral',
            timestamp=datetime.now().isoformat(),
            status='warning',
        )

    answer = ollama.generate(message.content)
    if answer is None:
        answer = f"I understood your message: '{message.content}'. I am trying to generate a response locally, but the model is not responding right now."

    emotion = detect_emotion_from_text(answer)
    memory.mood = emotion
    memory.add_message('cort', answer, emotion)

    return ResponseMessage(
        content=answer,
        emotion=emotion,
        timestamp=datetime.now().isoformat(),
        status='success',
    )


@app.get('/memory')
async def memory_state():
    return {
        'conversation_history': memory.conversation_history[-20:],
        'short_term_memory': memory.short_term_memory,
        'user_context': memory.user_context,
        'mood': memory.mood,
        'personality': memory.personality.dict(),
    }


@app.post('/context')
async def update_context(data: dict):
    memory.user_context.update(data)
    return {'status': 'updated', 'context': memory.user_context}


@app.get('/personalities')
async def personalities():
    return {'available': list(PERSONALITY_PRESETS.keys()), 'current': memory.personality.tone}


@app.post('/personality/{preset}')
async def set_personality(preset: str):
    if preset not in PERSONALITY_PRESETS:
        raise HTTPException(status_code=404, detail='Unknown personality preset')
    memory.personality.tone = preset
    return {
        'status': 'updated',
        'preset': preset,
        'description': PERSONALITY_PRESETS[preset]['description'],
    }


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            if message.get('type') == 'message':
                answer = ollama.generate(message.get('content', '')) if ollama.is_available() else 'Ollama is offline. Start it with: ollama serve.'
                emotion = detect_emotion_from_text(answer)
                await websocket.send_text(json.dumps({
                    'type': 'response',
                    'content': answer,
                    'emotion': emotion,
                    'timestamp': datetime.now().isoformat(),
                }))
            elif message.get('type') == 'ping':
                await websocket.send_text(json.dumps({'type': 'pong', 'timestamp': datetime.now().isoformat()}))
    except WebSocketDisconnect:
        print('Client disconnected')
    except Exception as exc:
        print(f'WebSocket error: {exc}')


if __name__ == '__main__':
    host = os.getenv('CORE_HOST', '0.0.0.0')
    port = int(os.getenv('CORE_PORT', '8000'))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    print('\n🧠 CORT Core starting')
    print(f'   Host: {host}:{port}')
    print(f'   Ollama: {memory.ollama_config.base_url}')
    print('   Endpoints: /health, /chat, /ws, /personality')
    uvicorn.run(app, host=host, port=port, reload=debug)
