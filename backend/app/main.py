from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.db import init_db
from backend.app.routers import auth as auth_router
from backend.app.routers import exercises as exercises_router
from backend.app.routers import meals as meals_router
from backend.app.routers import water as water_router
from backend.app.routers import today as today_router
from backend.app.routers import workouts as workouts_router

app = FastAPI(title="双人减")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(meals_router.router, prefix="/api/meals", tags=["meals"])
app.include_router(water_router.router, prefix="/api/water", tags=["water"])
app.include_router(exercises_router.router, prefix="/api/exercises", tags=["exercises"])
app.include_router(workouts_router.router, prefix="/api/workouts", tags=["workouts"])
app.include_router(today_router.router, prefix="/api/today", tags=["today"])


@app.on_event("startup")
def on_startup() -> None:
    init_db()
