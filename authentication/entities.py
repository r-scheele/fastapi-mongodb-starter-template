import datetime as dt
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from beanie import Document, Indexed
from uuid import UUID, uuid4

from authentication.models import Role

from beanie import PydanticObjectId


class UserProfile(Document):

    username: Optional[str]
    email: EmailStr
    registered_at: Optional[dt.datetime] = dt.datetime.now()
    last_login_at: Optional[dt.datetime]
    password: str
    role: Role = Role.USER
    avatar_identifier: Optional[str]
    is_verified: bool = False

    class Settings:
        name = "profiles"


class JwtRefreshToken(Document):
    profile_id: PydanticObjectId
    issued_at: dt.datetime
    expires_at: dt.datetime
    invalidated_at: Optional[dt.datetime]
    previous_token_id: Optional[str]
    valid: bool = True

    class Settings:
        name = "refresh_tokens"
