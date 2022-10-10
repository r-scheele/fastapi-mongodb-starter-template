from datetime import datetime
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
from authentication.service import AuthService
from authentication.avatar.service import AvatarService
from common.utils.mail.service import MailService
from common.utils.utilities.verification_code.service import VerificationCodeService
from authentication.models import UserCreate

# from avatar.service import AvatarService
from common.exceptions import HTTPExceptionJSON
from common.injection import on
from common.rate_limiter import RateLimitTo
from common.config import cfg

auth_router = InferringRouter()


@cbv(auth_router)
class AuthApi:
    _service: AuthService = Depends(on(AuthService))
    _avatar_service: AvatarService = Depends(on(AvatarService))
    _mail_service: MailService = Depends(on(MailService))
    _verification_code_service: VerificationCodeService = Depends(
        on(VerificationCodeService)
    )

    @auth_router.post(
        "/register",
        response_model=RegisterResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[
            Depends(RateLimitTo(times=1, seconds=1)),
            Depends(RateLimitTo(times=10, minutes=1)),
        ],
    )
    async def register(self, user_in: UserCreate, background_tasks: BackgroundTasks):

        """Register a new user."""
        try:
            profile = await self._service.register(
                UserCreate(**user_in.dict(exclude={"avatar_identifier"}))
            )

            # handle verification code generation
            verification_code = (
                await self._verification_code_service.generate_verification_code(
                    profile_id=profile.id, email=profile.email
                )
            )

            background_tasks.add_task(
                self._mail_service.send_verification_code,
                profile.email,
                verification_code.code,
            )

            background_tasks.add_task(
                self._avatar_service.save_avatar,
                user_in.avatar_identifier,
                profile.email,
            )
            return profile
        except InvalidUsername as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
            )
        except (EmailAlreadyTaken, UsernameAlreadyTaken) as e:
            raise HTTPExceptionJSON(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
                code=type(e).__name__,
                data=dict(field=e.field),
            )

    @auth_router.post("/login", response_model=LoginResponse)
    async def login(
        self, log_in: LoginIn, response: Response, background_tasks: BackgroundTasks
    ):
        """Perform a login attempt; if successful, refresh token cookie is set
        and access token is returned to the client."""
        try:
            jwt_data = await self._service.login(log_in.email, log_in.password)
        except LoginFailed:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        response.set_cookie(
            key="Authorization",
            value=f"Bearer {jwt_data.access_token}",
            httponly=True,
            max_age=jwt_data.access_exp,
            expires=jwt_data.access_exp,
        )

        response.set_cookie(
            key="refresh_token",
            value=jwt_data.refresh_token,
            httponly=True,
            secure=cfg.prod,
            expires=cfg.jwt_refresh_expiration_seconds,
        )

        # update user profile last login
        background_tasks.add_task(
            self._service.update_user_profile,
            {
                "last_login_at": datetime.utcnow(),
                "profile_id": jwt_data.profile_id,
            },
        )

        return {
            "access_token": jwt_data.access_token,
            "access_exp": jwt_data.access_exp,
            "refresh_exp": jwt_data.refresh_exp,
        }

    @auth_router.post("/refresh", response_model=LoginResponse)
    async def refresh(self, response: Response, refresh_token: str = Cookie(None)):
        """If refresh token hasn't expired, perform jwt token refresh, returning
        a new access token as well as setting a new refresh token cookie."""
        if not refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            jwt_data = await self._service.refresh_jwt_access_token(refresh_token)
        except (ExpiredJwtRefreshToken, InvalidatedJwtRefreshToken):
            response = JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED)
            response.delete_cookie("refresh_token")
            return response
        response.set_cookie(
            key="refresh_token",
            value=jwt_data.refresh_token,
            httponly=True,
            secure=cfg.prod,
            expires=cfg.jwt_refresh_expiration_seconds,
        )
        return {
            "access_token": jwt_data.access_token,
            "access_exp": jwt_data.access_exp,
            "refresh_exp": jwt_data.refresh_exp,
        }

    @auth_router.get("/verify")
    async def verify_verfication_code(
        self, code: int, background_tasks: BackgroundTasks
    ):
        """Verify a user's email address."""
        code_exist = await self._verification_code_service.verify_code(code)

        await self._service.update_user_profile(
            {
                "is_verified": True,
                "profile_id": code_exist.profile_id,
            }
        )

        background_tasks.add_task(self._verification_code_service.delete_code, code)
        return {"message": "Email verified successfully."}
