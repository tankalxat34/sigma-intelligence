import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .orm import Incident
from app.api.v1.events.orm import Event
from app.api.v1.timelines.orm import Timeline
from app.api.v1.logs.orm import Log
from app.config import settings
from app.database import db


async def get_incidents(session: AsyncSession, limit: int, offset: int) -> list[Incident]:
    stmt = select(Incident).order_by(Incident.iid.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_incident(session: AsyncSession, incident_iid: int) -> Incident | None:
    return await session.get(Incident, incident_iid)


async def create_incident(
    session: AsyncSession,
    video_link: str,
    domain: str = "AUTO",
) -> Incident:
    incident = Incident(
        video_link=video_link,
        status="PENDING",
        inferred_domain=domain,
        has_event=False,
        duration_sec=0.0,
        num_frames=0,
        num_windows=0,
    )
    session.add(incident)
    await session.commit()
    await session.refresh(incident)
    return incident


async def update_incident(session: AsyncSession, incident: Incident, data: dict) -> Incident:
    for key, value in data.items():
        setattr(incident, key, value)
    await session.commit()
    await session.refresh(incident)
    return incident


async def save_analysis_results(
    session: AsyncSession,
    incident: Incident,
    llm_result: dict,
) -> None:
    metadata = llm_result.get("metadata") or {}

    for w in llm_result.get("timeline", []):
        session.add(Timeline(
            incident_iid=incident.iid,
            window_idx=w["window_idx"],
            timestamp_sec=w["timestamp_sec"],
            interval_end_sec=w.get("interval_end_sec"),
            label=w.get("label") or "",
            has_event=w.get("has_event", False),
            caption=w.get("caption", ""),
            risk_score=w.get("risk_score", 0.0),
            event_type=w.get("event_type", ""),
        ))

    for e in llm_result.get("events", []):
        session.add(Event(
            incident_iid=incident.iid,
            event_type=e["event_type"],
            start_time=e["interval_start_sec"],
            end_time=e["interval_end_sec"],
            confidence=1.0,
            description=e.get("description", ""),
            highlight=f"{e['highlight_start_sec']}-{e['highlight_end_sec']}",
        ))

    for key, value in {
        "status": "DONE",
        "has_event": llm_result.get("has_event", False),
        "inferred_domain": llm_result.get("inferred_domain", "unknown"),
        "duration_sec": float(metadata.get("duration_sec") or 0),
        "num_frames": int(metadata.get("num_frames") or 0),
        "num_windows": int(metadata.get("num_windows") or 0),
        "model_version": settings.model_version,
        "prompt_version": settings.prompt_version,
        "analysis_json": json.dumps(llm_result, ensure_ascii=False),
    }.items():
        setattr(incident, key, value)

    await session.commit()


async def write_log(session: AsyncSession, incident_iid: int, event: str = "UPD") -> Log:
    log = Log(
        incident_iid=incident_iid,
        event=event,
        model_version=settings.model_version,
        prompt_version=settings.prompt_version,
    )
    session.add(log)
    await session.commit()
    return log


async def get_incident_timelines(session: AsyncSession, incident_iid: int) -> list[Timeline]:
    stmt = (
        select(Timeline)
        .where(Timeline.incident_iid == incident_iid)
        .order_by(Timeline.window_idx)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def process_incident_with_llm(
    incident_iid: int,
    file_path: str,
    domain: str | None,
    progress_store: dict,
) -> None:
    from app.api.v1.services import llm_client

    progress_store[incident_iid] = {"status": "PROCESSING"}

    async with db.session_factory() as session:
        incident = await session.get(Incident, incident_iid)
        incident.status = "PROCESSING"
        await session.commit()
        await write_log(session, incident_iid, "PROCESSING_START")

    try:
        result = await llm_client.analyze_video(
            Path(file_path), domain=domain,
            _progress=progress_store, _iid=incident_iid,
        )

        async with db.session_factory() as session:
            incident = await session.get(Incident, incident_iid)
            await save_analysis_results(session, incident, result)
            await write_log(session, incident_iid, "DONE")

        progress_store[incident_iid] = {
            "status": "DONE",
            "has_event": result.get("has_event", False),
            "inferred_domain": result.get("inferred_domain", "unknown"),
            "events_found": len(result.get("events", [])),
        }

    except Exception as exc:
        async with db.session_factory() as session:
            incident = await session.get(Incident, incident_iid)
            incident.status = "ERROR"
            await session.commit()
            await write_log(session, incident_iid, "ERROR")

        progress_store[incident_iid] = {"status": "ERROR", "error": str(exc)}
