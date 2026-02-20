from datetime import datetime
from sqlalchemy import String, Float, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.api.v1.base_model import Base


class Incident(Base):
    video_link: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    inferred_domain: Mapped[str] = mapped_column(String(50), default="UNKNOWN")
    has_event: Mapped[bool] = mapped_column(default=False)
    duration_sec: Mapped[float] = mapped_column(Float, default=0.0)
    num_frames: Mapped[int] = mapped_column(default=0)
    num_windows: Mapped[int] = mapped_column(default=0)
    model_version: Mapped[str] = mapped_column(String(50), default="")
    prompt_version: Mapped[str] = mapped_column(String(50), default="")
    analysis_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        default=datetime.utcnow,
    )

    events: Mapped[list["Event"]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )
    timelines: Mapped[list["Timeline"]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )
    logs: Mapped[list["Log"]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )
