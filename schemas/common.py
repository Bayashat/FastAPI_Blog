import uuid
from typing import Annotated

from pydantic import Field

# User specific types
UserId = Annotated[
    uuid.UUID,
    Field(title="User ID", description="The unique identifier of the user"),
]


PostId = Annotated[
    uuid.UUID,
    Field(title="Post ID", description="The unique identifier of the post"),
]
