from fastapi import APIRouter
from pydantic import BaseModel
from app.services.memory import MemoryService

router = APIRouter()
service = MemoryService()

class MemoryAdd(BaseModel):
    user: str
    content: str

@router.post("/add")
async def add_memory(payload: MemoryAdd):
    service.add(payload.user, payload.content)
    return {"status":"ok"}

@router.get("/query")
async def query_memory(q: str, user: str | None = None, k: int = 5):
    res = service.query(q, user=user, k=k)
    return {"results": res}
