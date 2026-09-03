from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.users import User


class Follow(Base):
    __tablename__ = "follows"

    follower_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    followed_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    followed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            """
            follower_id <> followed_user_id
            """,
            name="no_self_follow",
        ),
        Index(
            "ix_follows_follower_followed_at_followed_user", follower_id, followed_at.desc(), followed_user_id.desc()
        ),
        Index(
            "ix_follows_followed_user_followed_at_follower", followed_user_id, followed_at.desc(), follower_id.desc()
        ),
    )

    follower: Mapped[User] = relationship(
        foreign_keys=[follower_id],
        back_populates="outgoing_follows",
    )
    followed_user: Mapped[User] = relationship(
        foreign_keys=[followed_user_id],
        back_populates="incoming_follows",
    )
