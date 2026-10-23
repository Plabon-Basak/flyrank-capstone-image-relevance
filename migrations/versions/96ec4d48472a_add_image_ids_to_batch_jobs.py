
"""add image ids to batch jobs

Revision ID: 96ec4d48472a
Revises: f0d49857d563
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "96ec4d48472a"
down_revision: Union[str, Sequence[str], None] = "f0d49857d563"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "batch_jobs",
        sa.Column(
            "image_ids",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("batch_jobs", "image_ids")
