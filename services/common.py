from sqlalchemy import func, select

from models.comments import Comment
from models.likes import Like
from models.posts import Post

POST_COMMENT_COUNT_EXPR = (
    select(func.count(Comment.id))
    .where(Comment.post_id == Post.id)
    .correlate_except(Comment)
    .scalar_subquery()
    .label("comments_count")
)

POST_LIKE_COUNT_EXPR = (
    select(func.count())
    .select_from(Like)
    .where(Like.post_id == Post.id)
    .correlate_except(Like)
    .scalar_subquery()
    .label("likes_count")
)
