import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from schemas.common import EmailString, NormalizedString, PasswordString


class UserBase(BaseModel):
    username: NormalizedString
    email: EmailString


class UserCreate(UserBase):
    password: PasswordString


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: NormalizedString | None = None
    email: EmailString | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_values(cls, data: Any) -> Any:
        if isinstance(data, dict):
            null_fields = [field for field in ("username", "email") if field in data and data[field] is None]
            if null_fields:
                raise ValueError("User update fields cannot be null")
        return data

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"]


class UserPublic(BaseModel):
    id: uuid.UUID
    username: NormalizedString
    image_file: str | None = None
    image_path: str

    model_config = ConfigDict(from_attributes=True)


class UserPrivate(UserPublic):
    email: EmailString
