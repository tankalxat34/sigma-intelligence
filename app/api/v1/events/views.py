from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import db
from app.utils.structures import Status, resp
from . import crud
from .schemas import Event as EventSchema

router = APIRouter(prefix="/events", tags=["Events"])


@router.get(
    "/",
    summary="Список событий",
    description="Возвращает обнаруженные события. Используйте `?incident_iid=1` для фильтрации по конкретному видео.",
)
async def list_events(
    session: AsyncSession = Depends(db.scoped_session_dependency),
    incident_iid: int | None = Query(default=None, description="Фильтр по инциденту"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    events = await crud.get_events(session, incident_iid=incident_iid, limit=limit, offset=offset)
    return resp(Status.OK, [EventSchema.model_validate(e).model_dump() for e in events])


@router.get(
    "/{event_iid}",
    summary="Получить событие по ID",
)
async def get_event(
    event_iid: int,
    session: AsyncSession = Depends(db.scoped_session_dependency),
):
    event = await crud.get_event(session, event_iid)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {event_iid} not found")
    return resp(Status.OK, EventSchema.model_validate(event).model_dump())
