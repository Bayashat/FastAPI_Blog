"""add case-insensitive username unique index

Revision ID: 9c7d5f2a1b3e
Revises: 1a12b6430e66
Create Date: 2026-06-05 14:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c7d5f2a1b3e"
down_revision: Union[str, Sequence[str], None] = "1a12b6430e66"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.drop_constraint("users_username_key", "users", type_="unique")

    op.create_index(
        "uq_users_username_lower",
        "users",
        [sa.text("lower(username)")],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    op.drop_index("uq_users_username_lower", table_name="users")

    if bind.dialect.name == "postgresql":
        op.create_unique_constraint("users_username_key", "users", ["username"])
