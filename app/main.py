from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings


app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
app.mount("/artifacts", StaticFiles(directory=str(settings.artifacts_dir)), name="artifacts")
app.include_router(router)
