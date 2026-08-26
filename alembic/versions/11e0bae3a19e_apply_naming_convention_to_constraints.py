"""apply naming convention to constraints

Revision ID: 11e0bae3a19e
Revises: 6ab965a8af94
Create Date: 2026-06-27 01:05:54.871891

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "11e0bae3a19e"
down_revision: str | Sequence[str] | None = "6ab965a8af94"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONSTRAINT_RENAMES: tuple[tuple[str, str, str], ...] = (
    ("users", "users_pkey", "pk_users"),
    ("users", "users_email_key", "uq_users_email"),
    ("posts", "posts_pkey", "pk_posts"),
    ("posts", "posts_user_id_fkey", "fk_posts_user_id_users"),
    ("comments", "comments_pkey", "pk_comments"),
    ("comments", "comments_post_id_fkey", "fk_comments_post_id_posts"),
    ("comments", "comments_user_id_fkey", "fk_comments_user_id_users"),
    ("likes", "likes_pkey", "pk_likes"),
    ("likes", "likes_post_id_fkey", "fk_likes_post_id_posts"),
    ("likes", "likes_user_id_fkey", "fk_likes_user_id_users"),
    ("password_reset_tokens", "password_reset_tokens_pkey", "pk_password_reset_tokens"),
    (
        "password_reset_tokens",
        "password_reset_tokens_user_id_fkey",
        "fk_password_reset_tokens_user_id_users",
    ),
    (
        "password_reset_tokens",
        "password_reset_tokens_token_hash_key",
        "uq_password_reset_tokens_token_hash",
    ),
)


def rename_constraint_if_present(table_name: str, old_name: str, new_name: str) -> None:
    op.execute(
        f"""
DO $$
BEGIN
    IF to_regclass('{table_name}') IS NOT NULL
       AND EXISTS (
           SELECT 1
           FROM pg_constraint
           WHERE conrelid = to_regclass('{table_name}')
             AND conname = '{old_name}'
       )
       AND NOT EXISTS (
           SELECT 1
           FROM pg_constraint
           WHERE conrelid = to_regclass('{table_name}')
             AND conname = '{new_name}'
       )
    THEN
        ALTER TABLE {table_name} RENAME CONSTRAINT {old_name} TO {new_name};
    END IF;
END;
$$
"""
    )


def upgrade() -> None:
    """Upgrade schema."""
    if op.get_context().dialect.name != "postgresql":
        return

    for table_name, old_name, new_name in CONSTRAINT_RENAMES:
        rename_constraint_if_present(table_name, old_name, new_name)


def downgrade() -> None:
    """Downgrade schema."""
    if op.get_context().dialect.name != "postgresql":
        return

    for table_name, old_name, new_name in reversed(CONSTRAINT_RENAMES):
        rename_constraint_if_present(table_name, new_name, old_name)
