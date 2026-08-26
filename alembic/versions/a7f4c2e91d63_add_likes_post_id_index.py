"""add likes post_id index

Revision ID: a7f4c2e91d63
Revises: dd9cff3b2c2a
Create Date: 2026-08-21

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a7f4c2e91d63"
down_revision: Union[str, Sequence[str], None] = "dd9cff3b2c2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_likes_post_id", "likes", ["post_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_likes_post_id", table_name="likes")
