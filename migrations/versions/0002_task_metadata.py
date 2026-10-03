"""Task metadata, soft deletion and query indexes."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(
            sa.Column("priority", sa.String(10), nullable=False, server_default="medium")
        )
        batch.add_column(sa.Column("due_date", sa.Date()))
        batch.add_column(sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("notes", sa.Text()))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.execute("UPDATE tasks SET updated_at = created_at")
    with op.batch_alter_table("tasks") as batch:
        batch.alter_column("updated_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    for name in ("user_id", "is_completed", "due_date", "deleted_at"):
        op.create_index(f"ix_tasks_{name}", "tasks", [name])


def downgrade():
    with op.batch_alter_table("tasks") as batch:
        for name in ("user_id", "is_completed", "due_date", "deleted_at"):
            batch.drop_index(f"ix_tasks_{name}")
        for name in ("priority", "due_date", "tags", "notes", "updated_at", "deleted_at"):
            batch.drop_column(name)
