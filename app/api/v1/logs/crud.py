from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .orm import Log


async def get_logs(
    session: AsyncSession,
    incident_iid: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Log]:
    stmt = select(Log)
    if incident_iid is not None:
        stmt = stmt.where(Log.incident_iid == incident_iid)
    stmt = stmt.order_by(Log.timedate.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())
