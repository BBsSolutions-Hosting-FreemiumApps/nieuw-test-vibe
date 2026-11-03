from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import edit, health, telegram_webhook
from app.config import get_settings
from app.db import create_all
from app.services.storage import ensure_media_dir

app = FastAPI(title="Content Motor", version="0.1.0")

app.include_router(health.router)
app.include_router(telegram_webhook.router)
app.include_router(edit.router)


@app.on_event("startup")
def startup() -> None:
    settings = get_settings()
    ensure_media_dir(settings.media_dir)
    create_all()
    if not settings.database_url.startswith("sqlite"):
        create_all()


import os

os.makedirs("media", exist_ok=True)
app.mount("/media", StaticFiles(directory="media"), name="media")
app.mount("/static", StaticFiles(directory="static"), name="static")
