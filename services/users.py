import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from auth import hash_password, verify_password
from models import User
from schemas.users import UserCreate, UserUpdate
from services.pwd_reset_token import delete_existing_tokens


class IncorrectCurrentPasswordError(Exception):
    """The supplied current password does not match the stored password."""


class PasswordUnchangedError(Exception):
    """The new password is the same as the current password."""


class ProfileImageNotFoundError(Exception):
    """The user has no custom profile image to remove."""


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    stmt = select(User).where(func.lower(User.username) == username.lower())
    return await session.scalar(stmt)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    return await session.scalar(stmt)


async def username_or_email_exists(
    session: AsyncSession,
    username: str,
    email: str,
) -> bool:
    normalized_username = username.strip().lower()
    normalized_email = email.strip().lower()

    stmt = select(
        select(User.id)
        .where(
            or_(
                func.lower(User.username) == normalized_username,
                User.email == normalized_email,
            )
        )
        .exists()
    )

    return (await session.execute(stmt)).scalar_one()


async def create_user(
    session: AsyncSession,
    user: UserCreate,
    password_hash: str,
) -> User:
    new_user = User(username=user.username, email=user.email, password_hash=password_hash)
    session.add(new_user)
    await session.flush()
    return new_user


async def change_user_password(
    session: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    password_matches = await run_in_threadpool(
        verify_password,
        current_password,
        user.password_hash,
    )
    if not password_matches:
        raise IncorrectCurrentPasswordError

    user.password_hash = await run_in_threadpool(hash_password, new_password)
    await delete_existing_tokens(session, user.id)
    await session.commit()


async def update_user(
    session: AsyncSession,
    user: User,
    user_update: UserUpdate,
) -> User:
    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    await session.commit()
    return user


async def update_user_profile_image(
    session: AsyncSession,
    user: User,
    image_file: str | None,
) -> tuple[User, str | None]:
    old_file_name = user.image_file
    # 1. Old: None, New: "new.jpg" -> First time upload, ok.
    # 2. Old: "old.jpg", New: "new.jpg" -> Update, ok.
    # 3. Old: "old.jpg", New: None -> Delete, ok.
    # 4. Old: None, New: None -> Error, user has no image
    if old_file_name is None and image_file is None:
        raise ProfileImageNotFoundError

    user.image_file = image_file
    await session.commit()
    return user, old_file_name


async def delete_user(session: AsyncSession, user: User) -> str | None:
    old_file_name = user.image_file
    await session.delete(user)
    await session.commit()
    return old_file_name
