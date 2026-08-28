# ruff: noqa: E402

"""Reset the local database and load deterministic development fixtures.

This script is destructive. It refuses to run against a non-local database,
requires the Alembic-managed tables to exist, and replaces all business data in
one transaction.
"""

import asyncio
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TypedDict

# Keep project imports below this path bootstrap so the script also works when
# executed directly as `python local/scripts/populate_db.py`.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import Connection, delete, func, inspect, select
from sqlalchemy.engine import make_url

from auth import hash_password, hash_reset_token
from config import settings
from database import AsyncSessionLocal, Base, async_engine
from image_utils import PROFILE_PICS_DIR
from models import Comment, Like, PasswordResetToken, Post, User
from models.posts import PostStatus

LOCAL_DATABASE_HOSTS = {"127.0.0.1", "::1", "localhost"}
SEED_NAMESPACE = uuid.UUID("3ef73c58-1f53-4a89-b458-d68591149ce0")


class UserSeed(TypedDict):
    username: str
    email: str
    password: str


class PostSeed(TypedDict):
    title: str
    content: str


USERS: list[UserSeed] = [
    {
        "username": "CoreyMSchafer",
        "email": "coreymschafer@gmail.com",
        "password": "TestPassword1!",
    },
    {
        "username": "DefaultDude",
        "email": "testemail2@test.com",
        "password": "TestPassword2!",
    },
    {
        "username": "WillowTheCat",
        "email": "testemail3@test.com",
        "password": "TestPassword3!",
    },
    {
        "username": "FarmDogs",
        "email": "testemail4@test.com",
        "password": "TestPassword4!",
    },
    {
        "username": "PoppyTheCoder",
        "email": "testemail5@test.com",
        "password": "TestPassword5!",
    },
    {
        "username": "GoodBoyBronx",
        "email": "testemail6@test.com",
        "password": "TestPassword6!",
    },
]

POSTS: list[PostSeed] = [
    {
        "title": "Why I Love FastAPI",
        "content": "FastAPI has completely changed how I build APIs. The automatic documentation, type hints, and async support make development so much faster. Plus, the performance is incredible!",
    },
    {
        "title": "Corey Schafer Has the Best YouTube Tutorials!",
        "content": "This was written by a viewer and definitely not by me... I mean him. Totally not written by him, but by me... a real viewer. Seriously, check out his channel for amazing Python content.",
    },
    {
        "title": "Async/Await Finally Clicked",
        "content": "I've been struggling with async programming for months, but FastAPI's approach finally made it click. Using 'async def' for endpoints and 'await' for database calls just makes sense.",
    },
    {
        "title": "Schafer? I Barely Know Her!",
        "content": "Is anyone actually reading these blog posts? Do they really need to say anything? I can keep going all day. At least AI can... Claude, keep going, please.",
    },
    {
        "title": "Pydantic Validation is Magic",
        "content": "The way Pydantic handles validation in FastAPI is incredible. Define your model with type hints, and boom - automatic validation, serialization, and documentation. No more writing validation code by hand!",
    },
    {
        "title": "From Flask to FastAPI",
        "content": "I made the switch from Flask to FastAPI last month. The learning curve was minimal, and the benefits are huge. Automatic OpenAPI docs, better performance, and native async support. No regrets!",
    },
    {
        "title": "Some of My Favorite Horror Movies",
        "content": "I love horror movies and practical effects. One of my favorites is 'The Thing'. Hereditary is a great modern one, but most people have seen it. One modern one I really liked that not as many people have seen is 'The Night House'. It's a slow burn but really effective. More psychological than jump-scare based.",
    },
    {
        "title": "Type Hints Changed My Life",
        "content": "I used to think type hints were just extra typing (pun intended). But after using FastAPI, I see how they enable incredible tooling - better autocomplete, automatic validation, and self-documenting code.",
    },
    {
        "title": "The Power of Dependency Injection",
        "content": "FastAPI's dependency injection system is so elegant. Need a database session? Just add it as a parameter. Need the current user? Same thing. It makes the code so clean and testable.",
    },
    {
        "title": "SQLAlchemy 2.0 Is Worth the Upgrade",
        "content": "If you're still using SQLAlchemy 1.x patterns, it's time to upgrade. The new 2.0 style with select() and mapped_column() is much more explicit and works beautifully with async.",
    },
    {
        "title": "Hot Take: Python > JavaScript for APIs",
        "content": "Yes, I said it. For backend APIs, Python with FastAPI beats Node.js. Fight me in the comments. (Just kidding, this blog doesn't have comments... yet.)",
    },
    {
        "title": "Understanding HTTP Status Codes",
        "content": "200 OK, 201 Created, 400 Bad Request, 404 Not Found, 500 Internal Server Error. Learn these codes - they're how your API communicates with the world. FastAPI makes it easy to return the right ones.",
    },
    {
        "title": "Some of My Favorite Video Games",
        "content": "The one I probably play the most, but not my favorite, is League of Legends... It's a love/hate relationship. If you play, you get it. My favorites are all single-player RPGs. The Elder Scrolls series (Especially Morrowind and Skyrim) were awesome. The Baldur's Gate series took up a lot of my time as a kid, and more recently, the 3rd one was great. Speaking of Baldur's Gate, I love that old isometric style of RPG, so I looked for more modern equivalents and found Pillars of Eternity, which was fantastic. Also both Pathfinder: Kingmaker and Wrath of the Righteous were a lot of fun as well.",
    },
    {
        "title": "JWT Authentication Demystified",
        "content": "JSON Web Tokens seemed scary at first, but they're actually pretty simple. Encode some user data, sign it with a secret, and use it to verify requests. FastAPI + PyJWT makes it straightforward.",
    },
    {
        "title": "Tips for API Design",
        "content": "Use nouns for resources (/users, /posts), HTTP verbs for actions (GET, POST, PUT, DELETE), and return consistent responses. FastAPI's response_model helps enforce this consistency.",
    },
    {
        "title": "Path Parameters vs Query Parameters",
        "content": "Use path parameters for required resource identifiers (/users/123) and query parameters for optional filters (/posts?author=corey&limit=10). FastAPI handles both beautifully with automatic validation.",
    },
    {
        "title": "Error Handling Done Right",
        "content": "Don't just return 500 for everything! Use HTTPException to return meaningful status codes and messages. Your API consumers will thank you when debugging issues.",
    },
    {
        "title": "Why I Switched to UV",
        "content": "UV is blazingly fast for Python package management. Install packages in milliseconds instead of minutes. If you haven't tried it yet, you're missing out!",
    },
    {
        "title": "What About Favorite Books?",
        "content": "I don't read a lot of fiction. The last fiction book I read was 'The Martian' by Andy Weir, which I really enjoyed. But most of my reading is non-fiction. Some of my favorites are 'Meditations' by Marcus Aurelius, 'Conscious' by Annaka Harris, 'How to Die' by Seneca, and 'The Last Lecture' by Randy Pausch. The latest fiction book I'm reading through (and have been for a while) is 'House of Leaves' by Mark Z. Danielewski. It's... different, but awesome.",
    },
    {
        "title": "Testing FastAPI Applications",
        "content": "FastAPI's TestClient makes testing a breeze. Write tests for your endpoints, mock dependencies, and catch bugs before they hit production. Your future self will thank you.",
    },
    {
        "title": "Environment Variables and Security",
        "content": "Never hardcode secrets! Use environment variables and pydantic-settings to keep your API keys, database URLs, and JWT secrets safe. It's Security 101.",
    },
    {
        "title": "CORS: The Bane of Frontend Devs",
        "content": "Getting CORS errors? FastAPI's CORSMiddleware is your friend. Just remember: be specific about allowed origins in production. Don't use '*' unless you really mean it.",
    },
    {
        "title": "Async Database Queries",
        "content": "Blocking database calls in async code? That's a performance killer. Use async drivers like psycopg (for PostgreSQL) or aiosqlite to keep your event loop happy.",
    },
    {
        "title": "The Beauty of Response Models",
        "content": "Response models aren't just for documentation - they filter out sensitive fields automatically. Define what goes out, and Pydantic handles the rest.",
    },
    {
        "title": "Let's Talk Board Games",
        "content": "I love Settlers of Catan. It's a classic for a reason. I'm actually going to make a sword in my woodshop soon that will be my friend group's trophy for the annual Catan champion that we're going to call 'The Katana of Catan'. One thing I've always wanted to do, but never have, is play an in-person Dungeons & Dragons campaign. I've played so many D&D inspired video games, but never the real deal. Hopefully someday...",
    },
    {
        "title": "API Versioning Strategies",
        "content": "APIs evolve. Version them from day one! Whether you use URL prefixes (/v1/users) or headers, plan for change. Breaking changes without versioning breaks trust.",
    },
    {
        "title": "Background Tasks in FastAPI",
        "content": "Don't make users wait for emails to send or files to process. FastAPI's BackgroundTasks lets you return immediately while work continues in the background.",
    },
    {
        "title": "Rate Limiting Your API",
        "content": "Protect your API from abuse with rate limiting. Too many requests? Return 429 Too Many Requests. Your server (and your wallet) will thank you.",
    },
    {
        "title": "Documentation That Writes Itself",
        "content": "Add docstrings to your endpoints and they appear in Swagger UI. Add examples to your Pydantic models and they show up too. Documentation has never been this easy.",
    },
    {
        "title": "WebSockets with FastAPI",
        "content": "REST isn't the only game in town. FastAPI supports WebSockets for real-time communication. Chat apps, live updates, notifications - all possible!",
    },
    {
        "title": "Favorite Hobbies, You Ask?",
        "content": "Woodworking, hands down. I love making things with wood, but I wish I had more time for it. There's something special about making something with your own hands, with materials that are local. A lot of the stuff I've built came from trees that fell on my family's property. My stuff might not always be as good as something you buy in a store, but there's a story and a connection there that makes it better than anything I could buy elsewhere.",
    },
    {
        "title": "Custom Validators in Pydantic",
        "content": "Need validation beyond type checking? Pydantic's field_validator and model_validator decorators let you add custom logic. Validate emails, check password strength, whatever you need.",
    },
    {
        "title": "The ORM vs Raw SQL Debate",
        "content": "ORMs like SQLAlchemy add abstraction but can hide performance issues. Know when to use the ORM and when to drop to raw SQL. Both have their place.",
    },
    {
        "title": "Debugging Async Code",
        "content": "Async bugs can be tricky. Use logging liberally, understand the event loop, and don't mix sync and async without care. asyncio.run() is your entry point.",
    },
    {
        "title": "Containerizing FastAPI Apps",
        "content": "Docker + FastAPI = deployment bliss. Create a Dockerfile, build your image, and deploy anywhere. Consistency across environments is priceless.",
    },
    {
        "title": "Health Check Endpoints",
        "content": "Add a /health endpoint to your API. Load balancers and orchestrators need to know if your service is alive. Return 200 if healthy, details if not. I didn't do this in this tutorial, but there's only so much time in a video!",
    },
    {
        "title": "Hmm... What Else?",
        "content": "I'm running out of ideas for these blog posts. Maybe I should just write about how great FastAPI is... Oh wait, I've already done that multiple times. Well, if you're still reading, thanks for sticking with it! You're awesome.",
    },
    {
        "title": "Pagination: Don't Return Everything",
        "content": "Returning 10,000 records in one response? Please don't. Implement pagination with limit and offset (or better, cursor-based). Your database and clients will be happier.",
    },
    {
        "title": "OpenAPI Schema Customization",
        "content": "FastAPI's auto-generated OpenAPI schema is great, but sometimes you need to customize. Add examples, descriptions, and tags to make your docs shine.",
    },
    {
        "title": "Security Headers Matter",
        "content": "Add security headers to your responses: X-Content-Type-Options, X-Frame-Options, Content-Security-Policy. Small effort, big security improvement.",
    },
    {
        "title": "Caching Strategies",
        "content": "Not every request needs to hit the database. Use caching with Redis or even in-memory for frequently accessed data. Your response times will plummet (in a good way).",
    },
    {
        "title": "GraphQL vs REST",
        "content": "GraphQL is trendy, but REST is battle-tested. Choose based on your needs, not hype. FastAPI excels at REST, but Strawberry brings GraphQL if you need it.",
    },
    {
        "title": "Movie Quotes!",
        "content": "'You wanna know how I did it? This is how I did it, Anton. I never saved anything for the swim back.' - 'Gattaca'. One of my favorite movies of all time. As silly as it sounds, that movie is actually one of the main reasons I decided to pursue an internship at NASA back in college. After that internship, I found I had a craving to learn and do more. It pushed me to take programming more seriously, which eventually led me to where I am today... Which is writing a blog post about FastAPI that's just meant to fill space. TLDR: I watched Gattaca and now I'm writing sample blog posts at 3am on a Saturday for this FastAPI tutorial. And you can too!",
    },
]

# The 44th post - always the oldest (easter egg for pagination tutorial)
POST_44: PostSeed = {
    "title": "Fun Fact: My High School Football Number Was #44",
    "content": "If you've paginated all the way to this post, the 44th one... you get to learn this fun fact: that my high school football number was #44. Other notable absolute legends who wore number #44 include: Jerry West (NBA - Also fellow WV Native), Hank Aaron (MLB), and Floyd Little (NFL).",
}


@dataclass(frozen=True, slots=True)
class ResetTokenFixture:
    email: str
    token: str
    expired: bool


@dataclass(frozen=True, slots=True)
class SeedData:
    users: list[User]
    posts: list[Post]
    comments: list[Comment]
    likes: list[Like]
    reset_tokens: list[PasswordResetToken]
    reset_token_fixtures: list[ResetTokenFixture]


@dataclass(frozen=True, slots=True)
class SeedCounts:
    users: int
    posts: int
    comments: int
    likes: int
    password_reset_tokens: int


def seed_uuid(entity: str, index: int) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"{entity}:{index}")


def comment_count_for_post(post_index: int) -> int:
    # The oldest post has enough comments to exercise the default page size.
    return 12 if post_index == 0 else post_index % 4 + 1


def like_count_for_post(post_index: int) -> int:
    return post_index % len(USERS) + 1


def reset_token_value(user_index: int) -> str:
    return f"local-seed-reset-token-{user_index + 1:02d}-{'x' * 32}"


def post_created_at(now: datetime, post_index: int, post_count: int) -> datetime:
    if post_count == 1:
        return now - timedelta(days=2)

    # Deterministically spread posts from 90 days ago to 2 days ago.
    days_ago = 90 - (88 * post_index / (post_count - 1))
    return now - timedelta(days=days_ago)


def post_status_for_index(post_index: int) -> PostStatus:
    match post_index % 11:
        case 9:
            return PostStatus.DRAFT
        case 10:
            return PostStatus.ARCHIVED
        case _:
            return PostStatus.PUBLISHED


def post_published_at(created_at: datetime, status: PostStatus) -> datetime | None:
    if status is PostStatus.DRAFT:
        return None

    return created_at + timedelta(hours=6)


def ensure_local_database() -> None:
    database_url = make_url(settings.database_url)
    if database_url.host not in LOCAL_DATABASE_HOSTS:
        raise RuntimeError(
            "Refusing to replace data in a non-local database. "
            f"Expected host in {sorted(LOCAL_DATABASE_HOSTS)}, got {database_url.host!r}."
        )


def get_table_names(connection: Connection) -> set[str]:
    return set(inspect(connection).get_table_names())


async def verify_schema() -> None:
    expected_tables = set(Base.metadata.tables)
    async with async_engine.connect() as connection:
        existing_tables = await connection.run_sync(get_table_names)

    missing_tables = expected_tables - existing_tables
    if missing_tables:
        missing = ", ".join(sorted(missing_tables))
        raise RuntimeError(f"Database schema is missing tables: {missing}. Run `make migrate` first.")


async def build_seed_data(now: datetime | None = None) -> SeedData:
    now = now or datetime.now(UTC).replace(microsecond=0)
    password_hashes = await asyncio.gather(
        *(asyncio.to_thread(hash_password, user_seed["password"]) for user_seed in USERS)
    )

    users = [
        User(
            id=seed_uuid("user", index),
            username=user_seed["username"],
            email=user_seed["email"],
            password_hash=password_hash,
            image_file=None,
            created_at=now - timedelta(days=180 - index),
            updated_at=now - timedelta(days=180 - index),
        )
        for index, (user_seed, password_hash) in enumerate(zip(USERS, password_hashes, strict=True))
    ]

    post_seeds = [POST_44, *reversed(POSTS)]
    posts: list[Post] = []
    for post_index, post_seed in enumerate(post_seeds):
        author_index = 0 if post_index == 0 else (post_index - 1) % len(users)
        created_at = post_created_at(now, post_index, len(post_seeds))
        status = post_status_for_index(post_index)
        published_at = post_published_at(created_at, status)
        posts.append(
            Post(
                id=seed_uuid("post", post_index),
                title=post_seed["title"],
                content=post_seed["content"],
                user_id=users[author_index].id,
                status=status,
                published_at=published_at,
                created_at=created_at,
                updated_at=published_at or created_at,
            )
        )

    comments: list[Comment] = []
    comment_index = 0
    for post_index, post in enumerate(posts):
        comment_count = comment_count_for_post(post_index)
        post_age = now - post.created_at
        for offset in range(comment_count):
            commenter = users[(post_index + offset + 1) % len(users)]
            comments.append(
                Comment(
                    id=seed_uuid("comment", comment_index),
                    user_id=commenter.id,
                    post_id=post.id,
                    content=f'Test comment {offset + 1} on "{post.title}" by {commenter.username}.',
                    created_at=post.created_at + post_age * ((offset + 1) / (comment_count + 1)),
                )
            )
            comment_index += 1

    likes: list[Like] = []
    for post_index, post in enumerate(posts):
        like_count = like_count_for_post(post_index)
        post_age = now - post.created_at
        for offset in range(like_count):
            user = users[(post_index + offset) % len(users)]
            likes.append(
                Like(
                    user_id=user.id,
                    post_id=post.id,
                    created_at=post.created_at + post_age * ((offset + 1) / (like_count + 1)),
                )
            )

    reset_tokens: list[PasswordResetToken] = []
    reset_token_fixtures: list[ResetTokenFixture] = []
    for user_index, user in enumerate(users):
        token = reset_token_value(user_index)
        expired = user_index % 2 == 1
        reset_tokens.append(
            PasswordResetToken(
                id=seed_uuid("reset-token", user_index),
                user_id=user.id,
                token_hash=hash_reset_token(token),
                expires_at=now - timedelta(hours=1) if expired else now + timedelta(hours=1),
                created_at=now - timedelta(hours=2 if expired else 1),
            )
        )
        reset_token_fixtures.append(
            ResetTokenFixture(
                email=user.email,
                token=token,
                expired=expired,
            )
        )

    return SeedData(
        users=users,
        posts=posts,
        comments=comments,
        likes=likes,
        reset_tokens=reset_tokens,
        reset_token_fixtures=reset_token_fixtures,
    )


async def replace_database_data(seed_data: SeedData) -> None:
    async with AsyncSessionLocal.begin() as session:
        # Explicit child-to-parent order keeps this correct even without relying on cascades.
        await session.execute(delete(PasswordResetToken))
        await session.execute(delete(Like))
        await session.execute(delete(Comment))
        await session.execute(delete(Post))
        await session.execute(delete(User))

        session.add_all(seed_data.users)
        await session.flush()
        session.add_all(seed_data.posts)
        await session.flush()
        session.add_all(seed_data.comments)
        await session.flush()
        session.add_all(seed_data.likes)
        await session.flush()
        session.add_all(seed_data.reset_tokens)


async def read_database_counts() -> SeedCounts:
    async with AsyncSessionLocal() as session:
        return SeedCounts(
            users=(await session.execute(select(func.count()).select_from(User))).scalar_one(),
            posts=(await session.execute(select(func.count()).select_from(Post))).scalar_one(),
            comments=(await session.execute(select(func.count()).select_from(Comment))).scalar_one(),
            likes=(await session.execute(select(func.count()).select_from(Like))).scalar_one(),
            password_reset_tokens=(
                await session.execute(select(func.count()).select_from(PasswordResetToken))
            ).scalar_one(),
        )


def expected_counts(seed_data: SeedData) -> SeedCounts:
    return SeedCounts(
        users=len(seed_data.users),
        posts=len(seed_data.posts),
        comments=len(seed_data.comments),
        likes=len(seed_data.likes),
        password_reset_tokens=len(seed_data.reset_tokens),
    )


def clear_profile_pictures() -> None:
    if not PROFILE_PICS_DIR.exists():
        return

    for file in PROFILE_PICS_DIR.iterdir():
        if file.is_file() and file.name != ".gitkeep":
            file.unlink()


def print_summary(seed_data: SeedData, counts: SeedCounts) -> None:
    print("\nDone! Database fixture counts:")
    print(f"  users: {counts.users}")
    print(f"  posts: {counts.posts}")
    print(f"  comments: {counts.comments}")
    print(f"  likes: {counts.likes}")
    print(f"  password_reset_tokens: {counts.password_reset_tokens}")

    print("\nLocal test users:")
    for user_seed in USERS:
        print(f"  {user_seed['email']} / {user_seed['password']}")

    print("\nLocal reset tokens:")
    for fixture in seed_data.reset_token_fixtures:
        status = "expired" if fixture.expired else "valid"
        print(f"  {fixture.email}: {fixture.token} ({status})")


async def populate() -> None:
    ensure_local_database()
    try:
        await verify_schema()
        seed_data = await build_seed_data()
        await replace_database_data(seed_data)
        clear_profile_pictures()

        counts = await read_database_counts()
        if counts != expected_counts(seed_data):
            raise RuntimeError(f"Seed verification failed: expected {expected_counts(seed_data)}, got {counts}")

        print_summary(seed_data, counts)
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(populate())
