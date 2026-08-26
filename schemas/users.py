from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    StringConstraints,
    model_validator,
)

from schemas.common import UserId

EmailAddress = Annotated[
    EmailStr,
    StringConstraints(strip_whitespace=True, to_lower=True, max_length=255),
]
Username = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]
PlainPassword = Annotated[
    SecretStr,
    Field(min_length=8, max_length=256),
]


class UserBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Username
    email: EmailAddress


class UserCreate(UserBase):
    password: PlainPassword


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Username | None = None
    email: EmailAddress | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_values(cls, data: Any) -> Any:
        if isinstance(data, dict):
            null_fields = [field for field in ("username", "email") if field in data and data[field] is None]
            if null_fields:
                raise ValueError("User update fields cannot be null")
        return data

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]


class UserPublic(BaseModel):
    id: UserId
    username: Username
    image_path: str

    model_config = ConfigDict(from_attributes=True)


class CurrentUserResponse(UserPublic):
    email: EmailAddress
