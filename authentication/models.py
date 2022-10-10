import datetime as dt
import enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID, uuid4
from beanie import Document, PydanticObjectId


class Role(str, enum.Enum):
    USER = "USER"
    INSTRUCTOR = "INSTRUCTOR"
    MENTOR = "MENTOR"
    ADMIN = "ADMIN"


class UserCreate(BaseModel):
    username: Optional[str] = Field(min_length=2, max_length=32)
    email: EmailStr
    password: str
    role: Role = Role.USER
    avatar_identifier: str = str(uuid4())

    class Config:
        schema_extra = {
            "example": {
                "username": "scheele",
                "email": "rscheele404@gmail.com",
                "password": "password",
                "role": "USER",
            }
        }


class JwtRefreshTokenCreate(BaseModel):
    profile_id: PydanticObjectId
    issued_at: dt.datetime
    expires_at: dt.datetime
    invalidated_at: Optional[dt.datetime]
    previous_token_id: Optional[str]
    valid: bool = True


class JwtUser(BaseModel):
    id: str
    email: EmailStr
    role: Role
    is_verified: bool
    avatar_identifier: str


class User(JwtUser):
    id: PydanticObjectId


class JwtTokenPayload(BaseModel):
    iat: dt.datetime
    exp: dt.datetime
    user: JwtUser


class JwtRefreshTokenPayload(BaseModel):
    iat: dt.datetime
    exp: dt.datetime
    jti: str
    profile_id: str


class JwtTokenData(BaseModel):
    access_token: str
    access_exp: int


class JwtRefreshTokenData(BaseModel):
    refresh_token: str
    refresh_exp: int


class JwtData(JwtTokenData, JwtRefreshTokenData):
    profile_id: PydanticObjectId
