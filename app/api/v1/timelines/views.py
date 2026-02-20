from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import db
from app.utils.structures import Status, resp
from . import crud
from .schemas import Timeline as TimelineSchema

router = APIRouter(prefix="/timelines", tags=["Timelines"])


@router.get(
    "/",
    summary="Раскадровка по временным окнам",
    description=(
        "Возвращает все окна анализа с таймкодами и описаниями от VLM. "
        "Используйте `?incident_iid=1` для конкретного видео."
    ),
)
async def list_timelines(
    session: AsyncSession = Depends(db.scoped_session_dependency),
    incident_iid: int | None = Query(default=None, description="Фильтр по инциденту"),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    timelines = await crud.get_timelines(session, incident_iid=incident_iid, limit=limit, offset=offset)
    return resp(Status.OK, [TimelineSchema.model_validate(t).model_dump() for t in timelines])
