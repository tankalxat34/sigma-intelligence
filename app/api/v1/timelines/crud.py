from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .orm import Timeline


async def get_timelines(
    session: AsyncSession,
    incident_iid: int | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[Timeline]:
    stmt = select(Timeline)
    if incident_iid is not None:
        stmt = stmt.where(Timeline.incident_iid == incident_iid)
    stmt = stmt.order_by(Timeline.window_idx).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())
