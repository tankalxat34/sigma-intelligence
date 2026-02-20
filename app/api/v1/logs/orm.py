from datetime import datetime
from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.v1.base_model import Base


class Log(Base):
    incident_iid: Mapped[int] = mapped_column(ForeignKey("incidents.iid"))
    timedate: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        default=datetime.utcnow,
    )
    event: Mapped[str] = mapped_column(String(50), default="UPD")
    model_version: Mapped[str] = mapped_column(String(50), default="")
    prompt_version: Mapped[str] = mapped_column(String(50), default="")

    incident: Mapped["Incident"] = relationship(back_populates="logs")
