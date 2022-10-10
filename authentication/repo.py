from typing import Dict, Optional
from uuid import UUID, uuid4
import bcrypt
from injector import singleton, inject
from beanie import PydanticObjectId

from authentication.exceptions import EmailAlreadyTaken, UsernameAlreadyTaken
from authentication.models import JwtRefreshTokenCreate, UserCreate

from common.concurrency import cpu_bound_task
from authentication.entities import UserProfile, JwtRefreshToken


@singleton
class AuthRepo:
    @inject
    def __init__(self):
        self._user_profile = UserProfile
        self._jwt_refresh_token = JwtRefreshToken

    async def save_profile(self, new_user: UserCreate):

        """
        Save a new user profile.

        :param profile: profile data
        :return: newly created profile
        """
        user = await self._user_profile.find_one({"email": new_user.email})
        if user:
            raise EmailAlreadyTaken(new_user.email)

        user = await self._user_profile.find_one({"username": new_user.username})
        if user:
            raise UsernameAlreadyTaken(new_user.username)

        new_user.password = (
            await cpu_bound_task(
                bcrypt.hashpw, new_user.password.encode(), bcrypt.gensalt()
            )
        ).decode()
        new_user.email = new_user.email.lower()
        user = await self._user_profile(**new_user.dict()).save()

        return user

    async def find_profile_by_email(self, email: str) -> Optional[UserProfile]:
        """
        Find a user profile by email.

        :param email: user's email
        :return: user profile
        """
        return await self._user_profile.find_one({"email": email})

    async def save_avatar(self, identifier: UUID, email: str):
        """
        Save a new user profile.

        :param profile: profile data
        :return: newly created profile
        """
        user = await self._user_profile.find_one({"email": email})
        user.avatar_identifier = identifier
        await user.save()

        return user

    async def find_profile_by_id(
        self, profile_id: PydanticObjectId
    ) -> Optional[UserProfile]:
        return await self._user_profile.get(profile_id)

    async def find_jwt_refresh_token(
        self, token_id: PydanticObjectId
    ) -> Optional[JwtRefreshToken]:
        return await self._jwt_refresh_token.get(token_id)

    async def save_jwt_refresh_token(
        self, new_token: JwtRefreshToken
    ) -> JwtRefreshToken:
        """
        Save a new JWT refresh token.

        :param new_token: token data
        :return: newly created token
        """

        return await self._jwt_refresh_token(**new_token.dict()).save()

    async def update_jwt_refresh_token(
        self, token_id: PydanticObjectId, values: Dict
    ) -> JwtRefreshToken:

        token = await self._jwt_refresh_token.get(token_id)
        return await token.update({"$set": values})

    async def update_profile(self, values: Dict) -> UserProfile:

        profile = await self._user_profile.get(values.get("profile_id"))
        values.pop("profile_id")

        return await profile.update({"$set": values})
