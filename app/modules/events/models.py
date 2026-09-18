from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.users.models import utcnow


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("status IN ('upcoming', 'completed')"),
        Index("ix_events_organizer", "organizer_id"),
        Index("ix_events_starts_at", "starts_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organizer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizers.id", ondelete="RESTRICT"), nullable=False
    )
    venue_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("venues.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AccessibilityClaim(Base):
    __tablename__ = "accessibility_claims"
    __table_args__ = (
        *(
            CheckConstraint(
                f"{column} IS NULL OR {column} IN (0, 0.5, 1)",
                name=f"ck_claim_{column}",
            )
            for column in (
                "step_free_entrance",
                "elevator_or_ramp",
                "accessible_restroom",
                "accessible_seating",
                "rest_area",
                "parking_or_dropoff",
            )
        ),
        CheckConstraint("walking_distance_m IS NULL OR walking_distance_m >= 0"),
        CheckConstraint("source IN ('organizer', 'open_data', 'demo')"),
    )

    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("events.id", ondelete="CASCADE"), primary_key=True
    )
    step_free_entrance: Mapped[Decimal | None] = mapped_column(Numeric(2, 1))
    elevator_or_ramp: Mapped[Decimal | None] = mapped_column(Numeric(2, 1))
    accessible_restroom: Mapped[Decimal | None] = mapped_column(Numeric(2, 1))
    accessible_seating: Mapped[Decimal | None] = mapped_column(Numeric(2, 1))
    rest_area: Mapped[Decimal | None] = mapped_column(Numeric(2, 1))
    parking_or_dropoff: Mapped[Decimal | None] = mapped_column(Numeric(2, 1))
    walking_distance_m: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
