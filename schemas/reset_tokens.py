from pydantic import BaseModel, Field

from schemas.common import EmailString, PasswordString


class ForgotPasswordRequest(BaseModel):
    email: EmailString


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: PasswordString


class ChangePasswordRequest(BaseModel):
    current_password: PasswordString
    new_password: PasswordString
