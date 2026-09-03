import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth import oauth2_scheme, optional_oauth2_scheme, verify_access_token
from database import get_async_session
from models.users import User

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
) -> User:
    user_id = verify_access_token(token)

    if user_id is None:
        raise credentials_exception

    try:
        user_uuid = uuid.UUID(user_id)
    except (TypeError, ValueError):
        raise credentials_exception from None

    user = await session.get(User, user_uuid)
    if not user:
        raise credentials_exception

    return user


async def get_optional_current_user(
    token: Annotated[str | None, Depends(optional_oauth2_scheme)],
    session: SessionDep,
) -> User | None:
    if token is None:
        return None

    user_id = verify_access_token(token)

    if user_id is None:
        raise credentials_exception

    try:
        user_uuid = uuid.UUID(user_id)
    except (TypeError, ValueError):
        raise credentials_exception from None

    user = await session.get(User, user_uuid)

    if not user:
        raise credentials_exception

    return user


# async def get_current_active_user(
#     current_user: Annotated[User, Depends(get_current_user)],
# ):
#     if current_user.disabled:
#         raise HTTPException(status_code=400, detail="Inactive user")
#     return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]

OptionalCurrentUser = Annotated[
    User | None,
    Depends(get_optional_current_user),
]
