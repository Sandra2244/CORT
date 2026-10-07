from fastapi import APIRouter, UploadFile, File
from typing import List
import os
from app.services.avatar_service import AvatarService

router = APIRouter()
service = AvatarService()

@router.get("/")
async def list_avatars():
    return {"avatars": service.list_avatars()}

@router.post("/upload")
async def upload_avatar(file: UploadFile = File(...)):
    # Guarda avatar en carpeta /avatars (simple enfoque local)
    saved = service.save_avatar(file.filename, await file.read())
    return {"saved": saved}

@router.post("/{avatar_id}/set")
async def set_avatar(avatar_id: str):
    # En esta versión scaffold, solo devolvemos confirmación
    return {"status": "ok", "avatar_set": avatar_id}
