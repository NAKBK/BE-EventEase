"""Add email and password_hash to users for real registration/login (BE-006).

Revision ID: 0002_user_email_password
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_user_email_password"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "email")
