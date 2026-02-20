from typing import Annotated

from fastapi import Path, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .orm import Incident
from app.database import db

from . import crud


async def incident_by_id(
    incident_iid: Annotated[int, Path],
    session: AsyncSession = Depends(db.scoped_session_dependency),
) -> Incident:
    incident = await crud.get_incident(session=session, incident_iid=incident_iid)
    if incident is not None:
        return incident

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"incident {incident_iid} not found!",
    )
