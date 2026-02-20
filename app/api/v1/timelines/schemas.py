from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TimelineBase(BaseModel):
    incident_iid: int
    window_idx: int
    timestamp_sec: float
    interval_end_sec: Optional[float] = None
    label: str = ""
    has_event: bool = False
    caption: str = ""
    risk_score: float = 0.0
    event_type: str = ""


class TimelineCreate(TimelineBase):
    pass


class Timeline(TimelineBase):
    model_config = ConfigDict(from_attributes=True)
    iid: int = Field(gt=0)
