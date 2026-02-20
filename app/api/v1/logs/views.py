from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import db
from app.utils.structures import Status, resp
from . import crud
from .schemas import Log as LogSchema

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get(
    "/",
    summary="Журнал событий обработки",
    description=(
        "Возвращает лог-записи с временными метками, типом события и версиями модели/промптов. "
        "Используйте `?incident_iid=1` для конкретного видео."
    ),
)
async def list_logs(
    session: AsyncSession = Depends(db.scoped_session_dependency),
    incident_iid: int | None = Query(default=None, description="Фильтр по инциденту"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    logs = await crud.get_logs(session, incident_iid=incident_iid, limit=limit, offset=offset)
    return resp(Status.OK, [LogSchema.model_validate(log).model_dump() for log in logs])
