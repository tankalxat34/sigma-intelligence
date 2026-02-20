from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class IncidentBase(BaseModel):
    video_link: str
    status: str
    inferred_domain: str
    has_event: bool
    duration_sec: float
    num_frames: int
    num_windows: int
    model_version: str = ""
    prompt_version: str = ""


class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    inferred_domain: Optional[str] = None
    has_event: Optional[bool] = None
    duration_sec: Optional[float] = None
    num_frames: Optional[int] = None
    num_windows: Optional[int] = None
    model_version: Optional[str] = None
    prompt_version: Optional[str] = None


class Incident(IncidentBase):
    model_config = ConfigDict(from_attributes=True)
    iid: int = Field(gt=0)
    created_at: datetime
    analysis_json: Optional[str] = None
