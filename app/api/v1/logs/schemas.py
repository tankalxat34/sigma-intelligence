from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class LogBase(BaseModel):
    incident_iid: int
    timedate: datetime
    event: str = "UPD"
    model_version: str = ""
    prompt_version: str = ""


class LogCreate(LogBase):
    pass


class Log(LogBase):
    model_config = ConfigDict(from_attributes=True)
    iid: int = Field(gt=0)
