import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from schemas.posts import PaginatedPostsResponse, PostResponse, PostUpdatePatch
from schemas.users import UserCreate, UserUpdate


def test_user_create_keeps_password_secret() -> None:
    user = UserCreate.model_validate(
        {
            "username": "tester",
            "email": "tester@example.com",
            "password": "valid-password",
        }
    )

    assert str(user.password) == "**********"
    assert user.password.get_secret_value() == "valid-password"


@pytest.mark.parametrize("payload", [{}, {"username": None}, {"email": None}])
def test_user_update_requires_a_non_null_field(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        UserUpdate.model_validate(payload)


def test_user_update_accepts_a_partial_payload() -> None:
    update = UserUpdate(username="renamed")

    assert update.model_dump(exclude_unset=True) == {"username": "renamed"}


@pytest.mark.parametrize("payload", [{}, {"title": None}, {"content": None}])
def test_post_patch_requires_a_non_null_field(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PostUpdatePatch.model_validate(payload)


def test_post_patch_accepts_a_partial_payload() -> None:
    update = PostUpdatePatch(title="Updated title")

    assert update.model_dump(exclude_unset=True) == {"title": "Updated title"}


def test_paginated_response_validates_orm_like_objects() -> None:
    author_id = uuid.uuid4()
    author = SimpleNamespace(
        id=author_id,
        username="tester",
        image_path="/media/profile_pics/default.jpg",
    )
    post = SimpleNamespace(
        id=uuid.uuid4(),
        title="Title",
        content="Body",
        user_id=author_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        comments_count=0,
        likes_count=0,
        author=author,
    )

    response = PaginatedPostsResponse.model_validate(
        {
            "posts": [post],
            "total": 1,
            "skip": 0,
            "limit": 10,
            "has_more": False,
        }
    )

    assert isinstance(response.posts[0], PostResponse)
