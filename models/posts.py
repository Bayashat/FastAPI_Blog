from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy import Enum as SAEnum

# from sqlalchemy import UUID, text
from sqlalchemy.orm import Mapped, mapped_column, query_expression, relationship

from database import Base
from enums import PostStatus

if TYPE_CHECKING:
    from models.comments import Comment
    from models.likes import Like
    from models.post_tags import PostTag
    from models.tags import Tag
    from models.users import User


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # works only for PSQL, Note: here Uuid and Uuid() in type doesn't have diff.
    # id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, server_default=text("gen_random_uuid()"))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[PostStatus] = mapped_column(
        SAEnum(
            PostStatus,
            # db stores "draft" instead of "DRAFT"
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            native_enum=False,  # use "Varchar"
            create_constraint=True,  # create check constraint
            name="post_status",  # let alembic manage constraint
        ),
        default=PostStatus.DRAFT,
        server_default=PostStatus.DRAFT.value,
    )

    # extra_data: Mapped[dict[str, Any]] = mapped_column(
    #     MutableDict.as_mutable(JSONB),
    #     default=dict,
    #     server_default=text("'{}'::jsonb"),
    # )

    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    comments_count: Mapped[int | None] = query_expression()
    likes_count: Mapped[int | None] = query_expression()

    @property
    def tags(self) -> list[Tag]:
        return sorted(
            [link.tag for link in self.tag_links],
            key=lambda tag: tag.name,
        )

    __table_args__ = (
        CheckConstraint(
            """
            (status = 'draft' AND published_at IS NULL)
            OR
            (
                status IN ('published', 'archived')
                AND published_at IS NOT NULL
            )
            """,
            name="status_published_at_consistency",
        ),
        Index("ix_posts_user_id_created_at_id", user_id, created_at.desc(), id.desc()),
        Index("ix_posts_status_published_at_id", status, published_at.desc(), id.desc()),
        Index("ix_posts_created_at_id", created_at.desc(), id.desc()),
        Index("ix_posts_updated_at_id", updated_at.desc(), id.desc()),
    )

    author: Mapped[User | None] = relationship(back_populates="posts")
    # cascade="all, delete-orphan" 表示: 删除 post 时, 相关对象也应该删除
    # passive_deletes: Trust the DB's ON DELETE CASCADE, so SQLAlchemy does not load all children on post delete.
    likes: Mapped[list[Like]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    comments: Mapped[list[Comment]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tag_links: Mapped[list[PostTag]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
