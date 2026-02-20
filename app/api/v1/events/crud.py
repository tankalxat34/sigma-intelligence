from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .orm import Event


async def get_events(
    session: AsyncSession,
    incident_iid: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Event]:
    stmt = select(Event)
    if incident_iid is not None:
        stmt = stmt.where(Event.incident_iid == incident_iid)
    stmt = stmt.order_by(Event.start_time).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_event(session: AsyncSession, event_iid: int) -> Event | None:
    return await session.get(Event, event_iid)
