from sqlalchemy import ForeignKey, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.v1.base_model import Base


class Event(Base):
    incident_iid: Mapped[int] = mapped_column(ForeignKey("incidents.iid"))
    event_type: Mapped[str] = mapped_column(String(50))
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    description: Mapped[str] = mapped_column(String(512), default="")
    highlight: Mapped[str] = mapped_column(String(255), default="")

    incident: Mapped["Incident"] = relationship(back_populates="events")
