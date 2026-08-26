from collections.abc import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

# SQLALCHEMY_SYNC_DATABASE_URL = "sqlite:///./blog.db"

# sync_engine = create_engine(SQLALCHEMY_SYNC_DATABASE_URL, connect_args={"check_same_thread": False})
# SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# def get_sync_session():
#     with SyncSessionLocal() as session:
#         yield session


# For Async + SQLite
# SQLALCHEMY_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./blog.db"

async_engine = create_async_engine(
    settings.database_url
    # connect_args={"check_same_thread": False},  # needed for SQLite
)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
