from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from schemas.users import EmailAddress, PlainPassword


class PasswordRequestBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ForgotPasswordRequest(PasswordRequestBase):
    email: EmailAddress


class ResetPasswordRequest(PasswordRequestBase):
    token: Annotated[SecretStr, Field(min_length=32, max_length=256)]
    new_password: PlainPassword


class ChangePasswordRequest(PasswordRequestBase):
    current_password: PlainPassword
    new_password: PlainPassword

    @model_validator(mode="after")
    def validate_passwords(self) -> "ChangePasswordRequest":
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password")
        return self
