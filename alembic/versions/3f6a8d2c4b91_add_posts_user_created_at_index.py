"""add posts user created_at index

Revision ID: 3f6a8d2c4b91
Revises: 9c7d5f2a1b3e
Create Date: 2026-06-05 15:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f6a8d2c4b91"
down_revision: Union[str, Sequence[str], None] = "9c7d5f2a1b3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_posts_user_id"), table_name="posts")
    op.create_index(
        "ix_posts_user_id_created_at",
        "posts",
        ["user_id", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_posts_user_id_created_at", table_name="posts")
    op.create_index(op.f("ix_posts_user_id"), "posts", ["user_id"], unique=False)
