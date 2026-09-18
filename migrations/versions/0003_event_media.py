"""Add event_media table for claim photo evidence (BE-009 / BE-API-017).

Revision ID: 0003_event_media
Revises: 0002_user_email_password
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_event_media"
down_revision = "0002_user_email_password"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_media",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploader_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_event_media_event", "event_media", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_event_media_event", table_name="event_media")
    op.drop_table("event_media")
