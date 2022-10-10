import datetime as dt
from re import template
from injector import singleton, inject
from fastapi_mail import MessageSchema, FastMail
from beanie import PydanticObjectId
from pydantic import EmailStr

from common.utils.mail.schema import MailCreate
from common.concurrency import cpu_bound_task
from common.config import cfg

from common.utils.mail.config import conf
from common.utils.utilities.verification_code.repo import VerificationCodeRepo


@singleton
class VerificationCodeService:
    @inject
    def __init__(self, repo: VerificationCodeRepo):
        self._repo = repo

    async def generate_verification_code(
        self, profile_id: PydanticObjectId, email: str
    ):

        code = await self._repo.save_verification_code(profile_id, email)
        return code

    async def verify_code(self, code: int):
        return await self._repo.find_code(code)

    async def find_by_email(self, email: EmailStr):
        return await self._repo.find_verification_code_by_email(email)
