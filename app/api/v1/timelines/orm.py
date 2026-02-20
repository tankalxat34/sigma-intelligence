from sqlalchemy import ForeignKey, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.v1.base_model import Base


class Timeline(Base):
    incident_iid: Mapped[int] = mapped_column(ForeignKey("incidents.iid"))
    window_idx: Mapped[int]
    timestamp_sec: Mapped[float] = mapped_column(Float)
    interval_end_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    label: Mapped[str] = mapped_column(String(50), default="")
    has_event: Mapped[bool] = mapped_column(default=False)
    caption: Mapped[str] = mapped_column(String(512), default="")
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    event_type: Mapped[str] = mapped_column(String(50), default="")

    incident: Mapped["Incident"] = relationship(back_populates="timelines")
