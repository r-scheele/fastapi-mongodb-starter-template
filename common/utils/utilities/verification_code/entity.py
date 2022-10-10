import datetime as dt
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from beanie import Document, Indexed
from uuid import UUID, uuid4

from authentication.models import Role

from beanie import PydanticObjectId


class VerificationCode(Document):

    profile_id: PydanticObjectId
    email: EmailStr
    created_at: Optional[dt.datetime] = dt.datetime.now()
    code: int = Field(default_factory=lambda: uuid4().int % 1000000)

    class Settings:
        name = "verification_codes"
