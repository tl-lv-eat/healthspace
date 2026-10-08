from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.db import init_db
from backend.app.routers import auth as auth_router
from backend.app.routers import body as body_router
from backend.app.routers import calendar as calendar_router
from backend.app.routers import chat as chat_router
from backend.app.routers import exercises as exercises_router
from backend.app.routers import goals as goals_router
from backend.app.routers import journal as journal_router
from backend.app.routers import push as push_router
from backend.app.routers import reports as reports_router
from backend.app.routers import rewards as rewards_router
from backend.app.routers import meals as meals_router
from backend.app.routers import water as water_router
from backend.app.routers import today as today_router
from backend.app.routers import points as points_router
from backend.app.routers import week_plans as week_plans_router
from backend.app.routers import workouts as workouts_router
from backend.app.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    sched = start_scheduler()
    app.state.scheduler = sched
    yield
    if sched is not None:
        sched.shutdown(wait=False)


app = FastAPI(title="健康space🐉🍃", lifespan=lifespan)
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
app.include_router(body_router.router, prefix="/api/body", tags=["body"])
app.include_router(week_plans_router.router, prefix="/api/week-plans", tags=["week-plans"])
app.include_router(calendar_router.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(journal_router.router, prefix="/api/journal", tags=["journal"])
app.include_router(points_router.router, prefix="/api/points", tags=["points"])
app.include_router(goals_router.router, prefix="/api/goals", tags=["goals"])
app.include_router(rewards_router.router, prefix="/api/rewards", tags=["rewards"])
app.include_router(reports_router.router, prefix="/api/reports", tags=["reports"])
app.include_router(chat_router.router, prefix="/api/chat", tags=["chat"])
app.include_router(push_router.router, prefix="/api/push", tags=["push"])


_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
_assets_dir = _frontend_dist / "assets"
if _assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="frontend-assets")


@app.get("/{full_path:path}")
def spa_fallback(full_path: str) -> FileResponse:
    """Serve SPA index for client routes like /today (avoid blank 404 on refresh)."""
    if not _frontend_dist.is_dir():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="frontend dist not built")
    candidate = (_frontend_dist / full_path).resolve()
    try:
        candidate.relative_to(_frontend_dist.resolve())
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="invalid path") from exc
    if full_path and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(_frontend_dist / "index.html")
