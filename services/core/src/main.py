#!/usr/bin/env python3
"""
CORT Core Service - Main LLM and Intelligence Engine
Handles reasoning, memory, tool orchestration, and agent management
"""

import os
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import httpx

app = FastAPI(
    title="CORT Core",
    description="Cognitive Operating Reactive Technology - Core Intelligence Engine",
    version="0.1.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Message(BaseModel):
    content: str
    author: str = "user"
    timestamp: str = None
    
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

class PersonalityConfig(BaseModel):
    name: str = "CORT"
    tone: str = "professional_friendly"
    verbose: bool = True
    language: str = "en"

# Global state
class CORTMemory:
    def __init__(self):
        self.conversation_history = []
        self.user_context = {}
        self.personality = PersonalityConfig()
        self.active_tools = []
        self.mood = "neutral"
    
    def add_message(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_context(self):
        return {
            "history_length": len(self.conversation_history),
            "mood": self.mood,
            "personality": self.personality.dict(),
            "context": self.user_context
        }

memory = CORTMemory()

# Personality Presets
PERSONALITY_PRESETS = {
    "professional": {
        "system_prompt": "You are CORT, a professional AI assistant. Be concise, helpful, and direct.",
        "response_style": "formal"
    },
    "friendly": {
        "system_prompt": "You are CORT, a friendly AI companion. Be warm, engaging, and conversational.",
        "response_style": "casual"
    },
    "technical": {
        "system_prompt": "You are CORT, a technical AI expert. Provide detailed, accurate technical information.",
        "response_style": "technical"
    },
    "creative": {
        "system_prompt": "You are CORT, a creative AI assistant. Be imaginative, poetic, and inspiring.",
        "response_style": "artistic"
    }
}

# Mock LLM Response Generator (will integrate with Ollama)
def generate_response(prompt: str, personality: str = "friendly") -> dict:
    """
    Generate response from LLM.
    TODO: Integrate with Ollama for real inference
    """
    
    # Simple response templates for MVP
    responses = {
        "hello": "Hi there! I'm CORT, your personal AI assistant. How can I help you today?",
        "time": f"The current time is {datetime.now().strftime('%H:%M:%S')}",
        "date": f"Today is {datetime.now().strftime('%A, %B %d, %Y')}",
        "help": "I can help with: conversation, information, tasks, and much more. Just ask!",
        "joke": "Why did the AI go to school? To improve its neural networks! 😄",
        "default": f"That's an interesting question! Let me think about '{prompt}' for a moment. In a full deployment, I would use a local LLM (like Ollama with Llama 3.1) to generate a meaningful response."
    }
    
    prompt_lower = prompt.lower()
    
    # Simple keyword matching for MVP
    for key, response in responses.items():
        if key in prompt_lower:
            return {
                "content": response,
                "emotion": "happy",
                "confidence": 0.95
            }
    
    return {
        "content": responses["default"],
        "emotion": "thoughtful",
        "confidence": 0.7
    }

# Routes

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "cort-core",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
        "memory_state": memory.get_context()
    }

@app.post("/chat")
async def chat(message: Message):
    """
    Process a message and return a response
    """
    # Store in memory
    memory.add_message(message.author, message.content)
    
    # Generate response
    response_data = generate_response(message.content)
    
    # Create response message
    response = ResponseMessage(
        content=response_data["content"],
        emotion=response_data.get("emotion", "neutral"),
        timestamp=datetime.now().isoformat()
    )
    
    # Store in memory
    memory.add_message("cort", response.content)
    memory.mood = response.emotion
    
    return response

@app.get("/memory")
async def get_memory():
    """
    Retrieve current memory state
    """
    return {
        "conversation_history": memory.conversation_history[-10:],  # Last 10 messages
        "total_messages": len(memory.conversation_history),
        "context": memory.user_context,
        "mood": memory.mood,
        "personality": memory.personality.dict()
    }

@app.post("/memory/clear")
async def clear_memory():
    """
    Clear conversation history
    """
    memory.conversation_history = []
    return {"status": "memory cleared"}

@app.post("/personality/{preset}")
async def set_personality(preset: str):
    """
    Set personality from preset
    """
    if preset not in PERSONALITY_PRESETS:
        return {"error": f"Unknown preset: {preset}"}
    
    memory.personality.tone = preset
    return {
        "status": "personality updated",
        "preset": preset,
        "config": PERSONALITY_PRESETS[preset]
    }

@app.get("/personalities")
async def list_personalities():
    """
    List available personality presets
    """
    return {
        "available": list(PERSONALITY_PRESETS.keys()),
        "current": memory.personality.tone,
        "presets": PERSONALITY_PRESETS
    }

@app.post("/context")
async def update_context(data: dict):
    """
    Update user context (time, location, mood, etc.)
    """
    memory.user_context.update(data)
    return {
        "status": "context updated",
        "context": memory.user_context
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Process message
            response_data = generate_response(message.get("content", ""))
            
            # Send response
            response = {
                "type": "response",
                "content": response_data["content"],
                "emotion": response_data.get("emotion"),
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send_text(json.dumps(response))
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    host = os.getenv("CORE_HOST", "0.0.0.0")
    port = int(os.getenv("CORE_PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    print(f"🧠 CORT Core starting on {host}:{port}")
    print("   - Chat: POST /chat")
    print("   - WebSocket: /ws")
    print("   - Memory: GET /memory")
    print("   - Personalities: GET /personalities")
    
    uvicorn.run(app, host=host, port=port, reload=debug)
