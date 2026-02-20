from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.utils.structures import Status, resp
from app.config import settings
from app.database import db
from app.api.v1.base_model import Base
from app.api.v1 import router as api_v1_router

OPENAPI_TAGS = [
    {
        "name": "Incidents",
        "description": (
            "Основной ресурс. Каждое загруженное видео — это инцидент. "
            "**Флоу:** `POST /upload` → получаете `incident_iid` → "
            "открываете SSE `/{id}/status/stream` → ждёте `DONE` → "
            "читаете результат через `GET /{id}`."
        ),
    },
    {
        "name": "Events",
        "description": (
            "Значимые события, обнаруженные в видео. "
            "Заполняются из поля `events[]` ответа LLM. "
            "Фильтрация по инциденту: `?incident_iid=1`."
        ),
    },
    {
        "name": "Timelines",
        "description": (
            "Покадровая раскадровка видео по временным окнам. "
            "Заполняется из поля `timeline[]` ответа LLM. "
            "Фильтрация по инциденту: `?incident_iid=1`."
        ),
    },
    {
        "name": "Logs",
        "description": (
            "Журнал событий обработки инцидента (UPLOADED → PROCESSING_START → DONE/ERROR). "
            "Фиксирует версию модели и промптов для воспроизводимости."
        ),
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    description=settings.app_description,
    openapi_tags=OPENAPI_TAGS,
    version="1.0.0",
)

app.include_router(api_v1_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def get_health():
    return resp(Status.OK, {"name": settings.app_name, "db_echo": settings.db_echo})


@app.get("/")
def root():
    return resp(Status.OK, {"message": "Sigma Intelligence API. See /docs for documentation."})
