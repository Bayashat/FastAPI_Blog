from collections import Counter
from datetime import UTC, datetime

import pytest

from local.scripts import populate_db


@pytest.mark.asyncio
async def test_build_seed_data_populates_every_business_table(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(populate_db, "hash_password", lambda password: f"hashed::{password}")
    now = datetime(2026, 8, 27, 12, tzinfo=UTC)

    seed_data = await populate_db.build_seed_data(now)

    assert populate_db.expected_counts(seed_data) == populate_db.SeedCounts(
        users=6,
        posts=44,
        comments=121,
        likes=150,
        password_reset_tokens=6,
    )


@pytest.mark.asyncio
async def test_seed_relationships_are_valid_and_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(populate_db, "hash_password", lambda password: f"hashed::{password}")
    now = datetime(2026, 8, 27, 12, tzinfo=UTC)

    seed_data = await populate_db.build_seed_data(now)
    user_ids = {user.id for user in seed_data.users}
    post_ids = {post.id for post in seed_data.posts}

    assert len(user_ids) == len(seed_data.users)
    assert len(post_ids) == len(seed_data.posts)
    assert all(post.user_id in user_ids for post in seed_data.posts)
    assert all(comment.user_id in user_ids and comment.post_id in post_ids for comment in seed_data.comments)
    assert all(like.user_id in user_ids and like.post_id in post_ids for like in seed_data.likes)
    assert len({(like.user_id, like.post_id) for like in seed_data.likes}) == len(seed_data.likes)
    assert {token.user_id for token in seed_data.reset_tokens} == user_ids


@pytest.mark.asyncio
async def test_seed_distribution_covers_pagination_and_expiry_states(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(populate_db, "hash_password", lambda password: f"hashed::{password}")
    now = datetime(2026, 8, 27, 12, tzinfo=UTC)

    seed_data = await populate_db.build_seed_data(now)
    comments_per_post = Counter(comment.post_id for comment in seed_data.comments)
    likes_per_post = Counter(like.post_id for like in seed_data.likes)

    assert seed_data.posts[0].title == populate_db.POST_44["title"]
    assert seed_data.posts[0].created_at == min(post.created_at for post in seed_data.posts)
    assert comments_per_post[seed_data.posts[0].id] == 12
    assert all(comments_per_post[post.id] >= 1 for post in seed_data.posts)
    assert all(likes_per_post[post.id] >= 1 for post in seed_data.posts)
    assert sum(fixture.expired for fixture in seed_data.reset_token_fixtures) == 3
    assert sum(not fixture.expired for fixture in seed_data.reset_token_fixtures) == 3
