from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# SQLALCHEMY_SYNC_DATABASE_URL = "sqlite:///./blog.db"

# sync_engine = create_engine(SQLALCHEMY_SYNC_DATABASE_URL, connect_args={"check_same_thread": False})
# SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# def get_sync_session():
#     with SyncSessionLocal() as session:
#         yield session


SQLALCHEMY_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./blog.db"

async_engine = create_async_engine(SQLALCHEMY_ASYNC_DATABASE_URL, connect_args={"check_same_thread": False})
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_async_session():
    async with AsyncSessionLocal() as session:
        yield session
