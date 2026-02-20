import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import db
from app.utils.structures import Status, resp
from . import crud, dependencies
from .schemas import Incident as IncidentSchema
from app.api.v1.services.upload import save_upload_file, validate_content_type

router = APIRouter(prefix="/incidents", tags=["Incidents"])

_progress: dict[int, dict] = {}


@router.get(
    "/",
    summary="Список инцидентов",
    description="Возвращает все инциденты с пагинацией, отсортированные от новых к старым.",
)
async def list_incidents(
    session: AsyncSession = Depends(db.scoped_session_dependency),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    incidents = await crud.get_incidents(session, limit, offset)
    return resp(Status.OK, [IncidentSchema.model_validate(i).model_dump() for i in incidents])


@router.get(
    "/{incident_iid}/status/stream",
    summary="SSE: стриминг статуса анализа",
    description=(
        "Server-Sent Events. Открывайте **до или сразу после** `POST /upload`. "
        "Поток закрывается автоматически при статусе `DONE` или `ERROR`. "
        "Формат сообщений: `data: {\"status\": \"PROCESSING\", ...}`"
    ),
)
async def stream_status(incident_iid: int):
    async def event_stream():
        last_state = None
        for _ in range(600):
            state = _progress.get(incident_iid, {"status": "PENDING"})
            if state != last_state:
                last_state = state.copy()
                yield f"data: {json.dumps(state, ensure_ascii=False)}\n\n"
            if state.get("status") in ("DONE", "ERROR"):
                yield 'data: {"event": "close"}\n\n'
                break
            await asyncio.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Загрузить видео на анализ",
    description=(
        "Сохраняет видео на диск и **немедленно** запускает анализ через LLM в фоне. "
        "Возвращает `incident_iid` не дожидаясь анализа. "
        "Следите за прогрессом через `GET /{incident_iid}/status/stream`.\n\n"
        "**Параметр `domain`** (опционально): `traffic` | `production` | `violence` | `other`. "
        "Если не передан — LLM определяет домен автоматически."
    ),
)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Видеофайл (mp4, avi, mov...)"),
    domain: str = Form(default=None, description="Домен: traffic | production | violence | other"),
    session: AsyncSession = Depends(db.scoped_session_dependency),
):
    validate_content_type(file)

    incident = await crud.create_incident(
        session=session,
        video_link="saving...",
        domain=domain or "AUTO",
    )
    incident_iid = incident.iid
    _progress[incident_iid] = {"status": "UPLOADING"}

    suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
    file_path = settings.media_dir / "videos" / f"{incident_iid}{suffix}"

    await save_upload_file(file, file_path)

    await crud.update_incident(session, incident, {
        "video_link": str(file_path),
        "status": "SAVED",
    })
    await crud.write_log(session, incident_iid, "UPLOADED")

    _progress[incident_iid] = {"status": "SAVED"}

    background_tasks.add_task(
        crud.process_incident_with_llm,
        incident_iid,
        str(file_path),
        domain,
        _progress,
    )

    return resp(Status.OK, {
        "incident_iid": incident_iid,
        "status": "SAVED",
        "stream_url": f"{settings.api_v1_prefix}/incidents/{incident_iid}/status/stream",
    })


@router.post(
    "/{incident_iid}/search",
    summary="Текстовый поиск по таймлайну",
    description=(
        "Ищет совпадения промпта в описаниях (`caption`) временных окон таймлайна. "
        "Возвращает окна с таймкодами, где найдены слова из запроса. "
        "Точка подключения реального LLM-поиска в будущем."
    ),
)
async def search_in_incident(
    incident_iid: int,
    prompt: str = Query(..., description="Текстовый запрос, например: 'столкновение' или 'падение груза'"),
    session: AsyncSession = Depends(db.scoped_session_dependency),
):
    timelines = await crud.get_incident_timelines(session, incident_iid)
    words = prompt.lower().split()
    matched = [t for t in timelines if any(w in t.caption.lower() for w in words)]
    return resp(Status.OK, {
        "prompt": prompt,
        "total_windows": len(timelines),
        "matches": len(matched),
        "results": [
            {
                "window_idx": t.window_idx,
                "timestamp_sec": t.timestamp_sec,
                "interval_end_sec": t.interval_end_sec,
                "caption": t.caption,
                "risk_score": t.risk_score,
                "event_type": t.event_type,
            }
            for t in matched
        ],
    })


@router.get(
    "/{incident_iid}/report",
    summary="Скачать DOCX-отчёт",
    description=(
        "Генерирует отчёт через LLM-сервис на основе сохранённого JSON анализа. "
        "Доступен только после завершения анализа (`status=DONE`). "
        "Возвращает `.docx` файл."
    ),
)
async def download_report(
    incident=Depends(dependencies.incident_by_id),
):
    if not incident.analysis_json:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail="Analysis not completed yet",
        )
    from app.api.v1.services import llm_client

    video_path = Path(incident.video_link)
    content = await llm_client.generate_report(
        analysis_json=incident.analysis_json,
        video_path=video_path if video_path.exists() else None,
        return_format="docx",
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=report_{incident.iid}.docx"},
    )


@router.get(
    "/{incident_iid}/media",
    summary="Стриминг видео",
    description="Отдаёт исходный видеофайл. Поддерживает Range-запросы — браузер может перематывать по таймкодам.",
)
async def get_video(
    incident=Depends(dependencies.incident_by_id),
):
    file_path = Path(incident.video_link)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on server")
    return FileResponse(str(file_path), media_type="video/mp4")


@router.get(
    "/{incident_iid}",
    summary="Получить инцидент по ID",
    description="Возвращает все поля инцидента включая `analysis_json` с полным ответом LLM.",
)
async def get_incident(
    incident=Depends(dependencies.incident_by_id),
):
    return resp(Status.OK, IncidentSchema.model_validate(incident).model_dump())


@router.delete(
    "/{incident_iid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить инцидент",
    description="Удаляет инцидент и каскадно все связанные события, таймлайн и логи.",
)
async def delete_incident(
    incident=Depends(dependencies.incident_by_id),
    session: AsyncSession = Depends(db.scoped_session_dependency),
):
    await session.delete(incident)
    await session.commit()
