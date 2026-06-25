from typing import Annotated

from pydantic import EmailStr, Field, StringConstraints

EmailString = Annotated[
    EmailStr,
    StringConstraints(strip_whitespace=True, to_lower=True, max_length=255),
]
NormalizedString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]
PasswordString = Annotated[str, Field(min_length=8, max_length=256)]
