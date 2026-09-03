import uuid
from typing import Annotated

from pydantic import Field, StringConstraints

# User specific types
UserId = Annotated[
    uuid.UUID,
    Field(title="User ID", description="The unique identifier of the user"),
]


PostId = Annotated[
    uuid.UUID,
    Field(title="Post ID", description="The unique identifier of the post"),
]

PostTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
PostContent = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
