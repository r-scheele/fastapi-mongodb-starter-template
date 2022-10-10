from re import template
from pydantic import EmailStr, BaseModel
from typing import List, Optional, Union


class EmailSchema(BaseModel):
    email: List[EmailStr]


class MailCreate(BaseModel):
    subject: str
    recipients: Optional[Union[List[EmailStr], EmailStr]]
    template_name: Optional[str] = None


class MailResponse(BaseModel):
    message: str
