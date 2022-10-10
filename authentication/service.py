import datetime as dt
from calendar import timegm
from distutils.log import error
from gettext import find
from typing import Dict, Optional, List
from beanie import PydanticObjectId
from fastapi import status, Cookie, HTTPException, Depends, BackgroundTasks
import bcrypt
import jwt
from injector import singleton, inject
from pydantic import EmailStr

from authentication.exceptions import (
    LoginFailed,
    ExpiredJwtRefreshToken,
    InvalidatedJwtRefreshToken,
    VerificationCodeSent,
)
from authentication.models import (
    UserCreate,
    JwtTokenPayload,
    JwtUser,
    JwtRefreshTokenPayload,
    JwtRefreshTokenCreate,
    JwtData,
    JwtTokenData,
    JwtRefreshTokenData,
)
from authentication.repo import AuthRepo
from authentication.security import decode_jwt_refresh_token
from authentication.entities import UserProfile
from common.concurrency import cpu_bound_task
from common.config import cfg
from common.injection import on
from common.utils.mail.service import MailService
from common.utils.utilities.verification_code.service import VerificationCodeService
from common.utils.utilities.verification_code.repo import VerificationCodeRepo
from common.optional import AllOptional


class UserProfileUpdate(UserProfile, metaclass=AllOptional):
    pass


@singleton
class AuthService:
    _mail_service: MailService = Depends(on(MailService))

    @inject
    def __init__(self, repo: AuthRepo, ver_repo: VerificationCodeRepo):
        self._repo = repo
        self._ver_repo = ver_repo

    async def register(self, user: UserCreate):
        """
        Register a new user.

        :param profile: profile data
        :return: newly created profile
        """

        return await self._repo.save_profile(user)

    async def login(self, email: str, password: str) -> JwtData:
        """
        Try to log the user in, using provided email and password.
        :param email: user's registered email
        :param password: user's (non-hashed) password
        :return: access_token, access_exp, refresh_token, refresh_exp
        """

        profile = await self._repo.find_profile_by_email(email=email)
        pass_is_match = await self._check_password(password, profile.password)

        if not profile or not pass_is_match:
            raise LoginFailed()

        code = await self._ver_repo.find_verification_code_by_email(email=email)

        if not profile.is_verified and code:
            raise VerificationCodeSent(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please check your email for verification code",
                code=status.HTTP_403_FORBIDDEN,
            )

        jwt_data = self._generate_jwt_access_token(profile)

        jwt_refresh_data = await self._generate_jwt_refresh_token(profile.id)

        return JwtData(
            access_token=jwt_data.access_token,
            access_exp=jwt_data.access_exp,
            refresh_token=jwt_refresh_data.refresh_token,
            refresh_exp=jwt_refresh_data.refresh_exp,
            profile_id=profile.id,
        )

    async def _check_password(self, password: str, password_hash: str) -> bool:
        return await cpu_bound_task(
            bcrypt.checkpw, password.encode(), password_hash.encode()
        )

    def _generate_jwt_access_token(self, profile_data: UserProfile) -> JwtTokenData:
        iat = dt.datetime.now(dt.timezone.utc)
        exp = iat + dt.timedelta(seconds=cfg.jwt_expiration_seconds)
        user_payload = profile_data.dict()
        user_payload["id"] = str(profile_data.id)
        payload = JwtTokenPayload(iat=iat, exp=exp, user=JwtUser(**user_payload))
        enc_jwt = jwt.encode(
            payload=payload.dict(), key=cfg.jwt_secret, algorithm=cfg.jwt_algorithm
        )
        return JwtTokenData(access_token=enc_jwt, access_exp=timegm(exp.utctimetuple()))

    async def refresh_jwt_access_token(self, encoded_refresh_token: str) -> JwtData:
        """
        Perform jwt access token refreshing and refresh token rotation,
        returning a new jwt access token if provided refresh token is still
        valid (not expired and not invalidated).
        :param encoded_refresh_token: encoded refresh token
        :return: a JwtData containing the new access token, its expiration time,
        a new refresh token and its expiration time
        """

        try:
            old_refresh_token = decode_jwt_refresh_token(encoded_refresh_token)
        except jwt.ExpiredSignatureError:
            raise ExpiredJwtRefreshToken()
        old_jti, profile_id = (
            old_refresh_token["jti"],
            old_refresh_token["profile_id"],
        )

        stored_token = await self._repo.find_jwt_refresh_token(old_jti)
        if not stored_token or not stored_token.valid:
            raise InvalidatedJwtRefreshToken()
        new_jwt_data = self._generate_jwt_access_token(
            await self._repo.find_profile_by_id(profile_id)
        )
        new_jwt_refresh_data = await self._perform_refresh_token_rotation(
            profile_id=profile_id, previous_token_id=old_jti
        )
        return JwtData(
            access_token=new_jwt_data.access_token,
            access_exp=new_jwt_data.access_exp,
            refresh_token=new_jwt_refresh_data.refresh_token,
            refresh_exp=new_jwt_refresh_data.refresh_exp,
        )

    async def _perform_refresh_token_rotation(
        self, profile_id: PydanticObjectId, previous_token_id: PydanticObjectId
    ) -> JwtRefreshTokenData:
        await self._repo.update_jwt_refresh_token(
            token_id=previous_token_id,
            values=dict(valid=False, invalidated_at=dt.datetime.now(dt.timezone.utc)),
        )
        return await self._generate_jwt_refresh_token(
            profile_id=profile_id, previous_token_id=previous_token_id
        )

    async def _generate_jwt_refresh_token(
        self,
        profile_id: PydanticObjectId,
        previous_token_id: Optional[PydanticObjectId] = None,
    ) -> JwtRefreshTokenData:
        token = JwtRefreshTokenCreate(
            profile_id=profile_id,
            issued_at=dt.datetime.now(dt.timezone.utc),
            expires_at=dt.datetime.now(dt.timezone.utc)
            + dt.timedelta(seconds=cfg.jwt_refresh_expiration_seconds),
            previous_token_id=previous_token_id,
        )
        token = await self._repo.save_jwt_refresh_token(token)

        enc_jwt_refresh = jwt.encode(
            payload=JwtRefreshTokenPayload(
                iat=token.issued_at,
                exp=token.expires_at,
                jti=str(token.id),
                profile_id=str(profile_id),
            ).dict(),
            key=cfg.jwt_secret,
            algorithm=cfg.jwt_algorithm,
        )
        return JwtRefreshTokenData(
            refresh_token=enc_jwt_refresh,
            refresh_exp=timegm(token.expires_at.utctimetuple()),
        )

    async def save_avatar(self, identifier: PydanticObjectId, email: str):
        """
        Save a new user profile.

        :param profile: profile data
        :return: newly created profile
        """
        return await self._repo.save_avatar(identifier, email)

    async def update_user_profile(self, profile_data: Dict) -> UserProfile:
        """
        Update an existing user profile.

        :param profile: profile data
        :return: updated profile
        """
        await self._repo.update_profile(profile_data)

    async def find_profile_by_id(self, profile_id: PydanticObjectId) -> UserProfile:
        """
        Find a user profile by its id.

        :param profile_id: profile id
        :return: profile
        """
        return await self._repo.find_profile_by_id(profile_id)
