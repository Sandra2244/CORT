from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.llm import router as llm_router

app = FastAPI(title="CORT - Backend (scaffold)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(llm_router, prefix="/api/llm")

@app.get("/health")
async def health():
    return {"status":"ok"}
