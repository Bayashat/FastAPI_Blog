from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.posts import Post
    from models.tags import Tag
    from models.users import User


class PostTag(Base):
    __tablename__ = "post_tags"

    post_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    added_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_post_tags_tag_id", tag_id),)

    post: Mapped[Post] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship(back_populates="post_links")
    added_by_user: Mapped[User | None] = relationship()
