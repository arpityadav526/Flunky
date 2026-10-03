"""Revocable sessions, one-use account actions and device authorization."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_family_id", "sessions", ["family_id"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_table(
        "auth_actions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_auth_actions_user_id", "auth_actions", ["user_id"])
    op.create_table(
        "device_flows",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_code", sa.String(12), unique=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed", sa.Boolean(), nullable=False),
        sa.Column("last_poll", sa.DateTime(timezone=True)),
    )


def downgrade():
    op.drop_table("device_flows")
    op.drop_table("auth_actions")
    op.drop_table("sessions")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("email_verified")
