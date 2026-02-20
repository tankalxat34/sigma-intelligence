from pydantic import BaseModel, ConfigDict, Field


class EventBase(BaseModel):
    incident_iid: int
    event_type: str
    start_time: float
    end_time: float
    confidence: float = 1.0
    description: str = ""
    highlight: str = ""


class EventCreate(EventBase):
    pass


class Event(EventBase):
    model_config = ConfigDict(from_attributes=True)
    iid: int = Field(gt=0)
