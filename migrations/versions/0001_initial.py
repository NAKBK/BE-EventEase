"""Initial EventEase schema.

Revision ID: 0001_initial
Revises:
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('attendee', 'organizer')"),
    )
    op.create_table(
        "organizers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "venues",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("city", sa.String(80), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "need_profiles",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("step_free_entrance", sa.Boolean(), nullable=False),
        sa.Column("elevator_or_ramp", sa.Boolean(), nullable=False),
        sa.Column("accessible_restroom", sa.Boolean(), nullable=False),
        sa.Column("accessible_seating", sa.Boolean(), nullable=False),
        sa.Column("rest_area", sa.Boolean(), nullable=False),
        sa.Column("parking_or_dropoff", sa.Boolean(), nullable=False),
        sa.Column("walking_distance", sa.String(12), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("walking_distance IN ('short', 'moderate', 'any')"),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organizer_id", sa.String(36), sa.ForeignKey("organizers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("venue_id", sa.String(36), sa.ForeignKey("venues.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('upcoming', 'completed')"),
    )
    op.create_index("ix_events_organizer", "events", ["organizer_id"])
    op.create_index("ix_events_starts_at", "events", ["starts_at"])
    claim_columns = [
        sa.Column(name, sa.Numeric(2, 1), nullable=True)
        for name in (
            "step_free_entrance", "elevator_or_ramp", "accessible_restroom",
            "accessible_seating", "rest_area", "parking_or_dropoff",
        )
    ]
    op.create_table(
        "accessibility_claims",
        sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        *claim_columns,
        sa.Column("walking_distance_m", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        *(
            sa.CheckConstraint(
                f"{name} IS NULL OR {name} IN (0, 0.5, 1)",
                name=f"ck_claim_{name}",
            )
            for name in (
                "step_free_entrance", "elevator_or_ramp", "accessible_restroom",
                "accessible_seating", "rest_area", "parking_or_dropoff",
            )
        ),
        sa.CheckConstraint("walking_distance_m IS NULL OR walking_distance_m >= 0"),
        sa.CheckConstraint("source IN ('organizer', 'open_data', 'demo')"),
    )
    op.create_table(
        "accessibility_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("attendee_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("needs_snapshot", sa.JSON(), nullable=False),
        sa.Column("arrival_estimate", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("response_decision", sa.String(30), nullable=True),
        sa.Column("response_note", sa.Text(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'responded', 'confirmed', 'closed', 'verified')"),
        sa.CheckConstraint("response_decision IS NULL OR response_decision IN ('can_fulfill', 'partially_fulfill', 'cannot_fulfill')"),
    )
    op.create_index("ix_requests_event", "accessibility_requests", ["event_id"])
    op.create_index("ix_requests_attendee", "accessibility_requests", ["attendee_id"])
    op.create_table(
        "verifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_id", sa.String(36), sa.ForeignKey("accessibility_requests.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("attendee_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("verifications")
    op.drop_index("ix_requests_attendee", table_name="accessibility_requests")
    op.drop_index("ix_requests_event", table_name="accessibility_requests")
    op.drop_table("accessibility_requests")
    op.drop_table("accessibility_claims")
    op.drop_index("ix_events_starts_at", table_name="events")
    op.drop_index("ix_events_organizer", table_name="events")
    op.drop_table("events")
    op.drop_table("need_profiles")
    op.drop_table("venues")
    op.drop_table("organizers")
    op.drop_table("users")
