"""Durable creation identity for offline outbox replay."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("client_id", sa.String(36)))
        batch.create_unique_constraint("uq_task_client_id", ["user_id", "client_id"])


def downgrade():
    with op.batch_alter_table("tasks") as batch:
        batch.drop_constraint("uq_task_client_id", type_="unique")
        batch.drop_column("client_id")
