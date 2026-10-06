#!/usr/bin/env python3
"""
CORT Core Service - Enhanced with Ollama Integration
Combines OpenJarvis agents, adewaskar voice pipeline, and OpenClaw gesture foundation
"""

import os
import json
from datetime import datetime
from typing import Optional
import asyncio
import httpx

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(
    title="CORT Core",
    description="Cognitive Operating Reactive Technology - Integrated Intelligence Engine",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== MODELS ====================

class Message(BaseModel):
    content: str
    author: str = "user"
    timestamp: Optional[str] = None
    context: Optional[dict] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

class ResponseMessage(BaseModel):
    content: str
    author: str = "cort"
    timestamp: str
    emotion: str = "neutral"
    status: str = "success"
    thinking: Optional[str] = None

class PersonalityConfig(BaseModel):
    name: str = "CORT"
    tone: str = "professional_friendly"
    verbose: bool = True
    language: str = "en"

class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    model: str = "mistral"
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40

class GestureData(BaseModel):
    type: str  # "hand", "face", "pose"
    landmarks: list
    confidence: float

# ==================== MEMORY & CONTEXT ====================

class CORTMemory:
    """Enhanced memory system inspired by OpenJarvis"""
    
    def __init__(self):
        self.conversation_history = []
        self.user_context = {
            "name": "User",
            "location": "Unknown",
            "time_zone": "UTC",
            "current_task": None
        }
        self.personality = PersonalityConfig()
        self.ollama_config = OllamaConfig()
        self.mood = "neutral"
        self.active_skills = []
        self.gesture_buffer = []
        self.short_term_memory = []  # Last 5 interactions
        self.long_term_memory = {}  # Persistent knowledge
    
    def add_message(self, role: str, content: str, emotion: str = "neutral"):
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "emotion": emotion
        }
        self.conversation_history.append(msg)
        self.short_term_memory.append(msg)
        
        # Keep only last 5 in short-term
        if len(self.short_term_memory) > 5:
            self.short_term_memory.pop(0)
        
        return msg
    
    def get_context(self):
        return {
            "history_length": len(self.conversation_history),
            "mood": self.mood,
            "personality": self.personality.dict(),
            "user_context": self.user_context,
            "active_skills": self.active_skills,
            "short_term_memory": self.short_term_memory[-3:]
        }
    
    def build_system_prompt(self) -> str:
        """Build system prompt with personality and context"""
        tone_map = {
            "professional": "You are CORT, a professional AI assistant. Be precise, helpful, and concise.",
            "friendly": "You are CORT, a warm AI companion. Be engaging, conversational, and personable.",
            "technical": "You are CORT, a technical expert. Provide detailed, accurate technical information.",
            "creative": "You are CORT, a creative AI. Be imaginative, poetic, and inspiring."
        }
        
        base_prompt = tone_map.get(self.personality.tone, tone_map["friendly"])
        
        context_info = f"""
Current context:
- User: {self.user_context.get('name', 'User')}
- Time: {datetime.now().strftime('%H:%M:%S')}
- Current mood: {self.mood}
- Previous interactions: {len(self.short_term_memory)}
"""
        
        return f"{base_prompt}\n{context_info}"

memory = CORTMemory()

# ==================== PERSONALITY PRESETS ====================

PERSONALITY_PRESETS = {
    "professional": {
        "system_prompt": "You are CORT, a professional AI assistant. Be precise, helpful, and concise.",
        "response_style": "formal",
        "emoji_style": "minimal"
    },
    "friendly": {
        "system_prompt": "You are CORT, a warm AI companion. Be engaging, conversational, and personable.",
        "response_style": "casual",
        "emoji_style": "moderate"
    },
    "technical": {
        "system_prompt": "You are CORT, a technical expert. Provide detailed, accurate technical information with code examples when relevant.",
        "response_style": "technical",
        "emoji_style": "minimal"
    },
    "creative": {
        "system_prompt": "You are CORT, a creative AI. Be imaginative, poetic, and inspiring. Use metaphors and creative language.",
        "response_style": "artistic",
        "emoji_style": "abundant"
    }
}

# ==================== OLLAMA INTEGRATION ====================

class OllamaEngine:
    """Interface to Ollama for local LLM inference"""
    
    def __init__(self, config: OllamaConfig):
        self.config = config
        self.client = httpx.Client(timeout=120.0)
    
    def is_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = self.client.get(f"{self.config.base_url}/api/tags")
            return response.status_code == 200
        except:
            return False
    
    def list_models(self) -> list:
        """Get available models from Ollama"""
        try:
            response = self.client.get(f"{self.config.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except:
            pass
        return []
    
    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate response from Ollama"""
        try:
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "system": system or memory.build_system_prompt(),
                "stream": False,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "top_k": self.config.top_k
            }
            
            response = self.client.post(
                f"{self.config.base_url}/api/generate",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
        except Exception as e:
            print(f"Ollama error: {e}")
        
        return None

ollama = OllamaEngine(memory.ollama_config)

# ==================== EMOTION DETECTION ====================

def detect_emotion_from_text(text: str) -> str:
    """Simple emotion detection from text content"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["sad", "sorry", "bad", "wrong"]):
        return "sad"
    elif any(word in text_lower for word in ["excited", "wow", "amazing", "great", "love"]):
        return "excited"
    elif any(word in text_lower for word in ["hmm", "think", "consider", "analyze"]):
        return "thoughtful"
    elif any(word in text_lower for word in ["laugh", "haha", "funny", "joke"]):
        return "happy"
    elif any(word in text_lower for word in ["what", "how", "why", "question"]):
        return "curious"
    
    return "neutral"

# ==================== API ROUTES ====================

@app.get("/health")
async def health():
    """Health check endpoint"""
    ollama_status = ollama.is_available()
    available_models = ollama.list_models() if ollama_status else []
    
    return {
        "status": "ok",
        "service": "cort-core",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
        "ollama": {
            "available": ollama_status,
            "base_url": memory.ollama_config.base_url,
            "current_model": memory.ollama_config.model,
            "available_models": available_models
        },
        "memory_state": memory.get_context()
    }

@app.post("/chat")
async def chat(message: Message):
    """
    Process a message and return a response using Ollama
    Combines OpenJarvis memory + adewaskar personality + local LLM
    """
    memory.add_message(message.author, message.content)
    
    # Check if Ollama is available
    if not ollama.is_available():
        return ResponseMessage(
            content="I notice Ollama isn't running. Please start it with: ollama serve\n\nFor now, I can chat without it, but responses will be limited.",
            emotion="neutral",
            timestamp=datetime.now().isoformat(),
            status="warning"
        )
    
    # Generate response using Ollama
    response_text = ollama.generate(message.content)
    
    if not response_text:
        response_text = f"I understood your message: '{message.content}'. However, I'm having trouble generating a response right now. Please try again."
    
    # Detect emotion from response
    emotion = detect_emotion_from_text(response_text)
    memory.mood = emotion
    
    # Store in memory
    memory.add_message("cort", response_text, emotion)
    
    return ResponseMessage(
        content=response_text,
        emotion=emotion,
        timestamp=datetime.now().isoformat(),
        status="success"
    )

@app.get("/memory")
async def get_memory():
    """Retrieve current memory state"""
    return {
        "conversation_history": memory.conversation_history[-20:],
        "total_messages": len(memory.conversation_history),
        "context": memory.user_context,
        "mood": memory.mood,
        "personality": memory.personality.dict(),
        "short_term_memory": memory.short_term_memory
    }

@app.post("/memory/clear")
async def clear_memory():
    """Clear conversation history"""
    memory.conversation_history = []
    memory.short_term_memory = []
    return {"status": "memory cleared", "timestamp": datetime.now().isoformat()}

@app.post("/personality/{preset}")
async def set_personality(preset: str):
    """Set personality from preset (inspired by OpenJarvis skills)"""
    if preset not in PERSONALITY_PRESETS:
        raise HTTPException(status_code=404, detail=f"Unknown preset: {preset}")
    
    memory.personality.tone = preset
    return {
        "status": "personality updated",
        "preset": preset,
        "config": PERSONALITY_PRESETS[preset],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/personalities")
async def list_personalities():
    """List available personality presets"""
    return {
        "available": list(PERSONALITY_PRESETS.keys()),
        "current": memory.personality.tone,
        "presets": PERSONALITY_PRESETS
    }

@app.post("/context")
async def update_context(data: dict):
    """Update user context (time, location, mood, task)"""
    memory.user_context.update(data)
    return {
        "status": "context updated",
        "context": memory.user_context,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/gesture")
async def process_gesture(gesture: GestureData):
    """Process gesture data (OpenClaw integration)"""
    memory.gesture_buffer.append(gesture.dict())
    
    # Simple gesture recognition
    if gesture.type == "hand" and gesture.confidence > 0.7:
        gesture_type = "wave" if len(gesture.landmarks) > 15 else "point"
        return {
            "type": gesture_type,
            "confidence": gesture.confidence,
            "action": f"Avatar should {gesture_type}",
            "timestamp": datetime.now().isoformat()
        }
    
    return {"status": "gesture_received"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming
    Inspired by adewaskar/jarvis bridge architecture
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "message":
                # Process message
                response_text = ollama.generate(message_data.get("content", "")) if ollama.is_available() else "Ollama not available"
                emotion = detect_emotion_from_text(response_text) if response_text else "neutral"
                
                response = {
                    "type": "response",
                    "content": response_text,
                    "emotion": emotion,
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send_text(json.dumps(response))
            
            elif message_data.get("type") == "gesture":
                # Process gesture
                gesture_response = {
                    "type": "gesture_processed",
                    "action": message_data.get("action"),
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_text(json.dumps(gesture_response))
            
            elif message_data.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}))
    
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    host = os.getenv("CORE_HOST", "0.0.0.0")
    port = int(os.getenv("CORE_PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    print(f"\n🧠 CORT Core starting on {host}:{port}")
    print("   - Chat: POST /chat")
    print("   - WebSocket: /ws")
    print("   - Memory: GET /memory")
    print("   - Personalities: GET /personalities")
    print("   - Gestures: POST /gesture")
    print(f"   - Health: GET /health")
    print(f"   - Ollama: {memory.ollama_config.base_url}")
    
    uvicorn.run(app, host=host, port=port, reload=debug)
