from fastapi import status, Cookie, HTTPException, Depends, BackgroundTasks
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from starlette.responses import Response, JSONResponse

from authentication.exceptions import (
    LoginFailed,
    ExpiredJwtRefreshToken,
    InvalidatedJwtRefreshToken,
    UsernameAlreadyTaken,
    EmailAlreadyTaken,
    InvalidUsername,
)
from authentication.schemas import (
    RegisterResponse,
    LoginIn,
    LoginResponse,
)

from common.utils.mail.service import MailService
from common.utils.mail.schema import MailCreate, MailResponse

# from avatar.service import AvatarService
from common.exceptions import HTTPExceptionJSON
from common.injection import on
from common.rate_limiter import RateLimitTo
from common.config import cfg

mail_router = InferringRouter()


@cbv(mail_router)
class MailApi:
    _service: MailService = Depends(on(MailService))

    @mail_router.post(
        "/send",
        status_code=status.HTTP_200_OK,
        dependencies=[
            Depends(RateLimitTo(times=1, seconds=1)),
            Depends(RateLimitTo(times=10, minutes=1)),
        ],
    )
    async def send_email(self, mail_in: MailCreate, background_tasks: BackgroundTasks):
        """
        Send email
        """

        values = {"url": "https://www.google.com", "first_name": "Habeeb"}
        values["subject"] = mail_in.subject

        return await self._service.send_email(mail_in, values)
