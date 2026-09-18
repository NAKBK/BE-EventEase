from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('attendee', 'organizer')"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class NeedProfile(Base):
    __tablename__ = "need_profiles"
    __table_args__ = (
        CheckConstraint("walking_distance IN ('short', 'moderate', 'any')"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    step_free_entrance: Mapped[bool] = mapped_column(Boolean, nullable=False)
    elevator_or_ramp: Mapped[bool] = mapped_column(Boolean, nullable=False)
    accessible_restroom: Mapped[bool] = mapped_column(Boolean, nullable=False)
    accessible_seating: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rest_area: Mapped[bool] = mapped_column(Boolean, nullable=False)
    parking_or_dropoff: Mapped[bool] = mapped_column(Boolean, nullable=False)
    walking_distance: Mapped[str] = mapped_column(String(12), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)