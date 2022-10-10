from typing import Optional
from uuid import UUID, uuid4

from pydantic import Field, EmailStr

from authentication.models import Role
from common.schemas import BaseSchema


class RegisterResponse(BaseSchema):
    username: Optional[str]
    email: EmailStr
    role: Optional[Role] = Role.USER
    avatar_identifier: str


class LoginIn(BaseSchema):
    email: EmailStr
    password: str

    class Config:
        schema_extra = {
            "example": {
                "email": "rscheele404@gmail.com",
                "password": "password",
            }
        }


class LoginResponse(BaseSchema):
    access_token: str
    access_exp: int
    refresh_exp: int
