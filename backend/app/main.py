from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.db import init_db
from backend.app.routers import auth as auth_router

app = FastAPI(title="双人减")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])


@app.on_event("startup")
def on_startup() -> None:
    init_db()
