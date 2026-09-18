from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.users.models import utcnow


class AccessibilityRequest(Base):
    __tablename__ = "accessibility_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'responded', 'confirmed', 'closed', 'verified')"
        ),
        CheckConstraint(
            "response_decision IS NULL OR response_decision IN "
            "('can_fulfill', 'partially_fulfill', 'cannot_fulfill')"
        ),
        Index("ix_requests_event", "event_id"),
        Index("ix_requests_attendee", "attendee_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("events.id", ondelete="RESTRICT"), nullable=False
    )
    attendee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    needs_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    arrival_estimate: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    response_decision: Mapped[str | None] = mapped_column(String(30))
    response_note: Mapped[str | None] = mapped_column(Text)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
