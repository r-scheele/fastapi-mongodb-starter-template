from injector import singleton, inject
from beanie import PydanticObjectId
from typing import Dict, Optional

from common.utils.utilities.verification_code.entity import VerificationCode


@singleton
class VerificationCodeRepo:
    @inject
    def __init__(self):
        self._verification_code = VerificationCode

    async def save_verification_code(self, profile_id: PydanticObjectId, email: str):
        """
        Save a new user profile.

        :param profile: profile data
        :return: newly created profile
        """
        verification_code = await self.find_verification_code_by_email(email)

        if verification_code:
            await verification_code.delete()

        verification_code = await self._verification_code(
            profile_id=profile_id, email=email
        ).save()

        return verification_code

    async def find_verification_code_by_email(
        self, email: str
    ) -> Optional[VerificationCode]:
        """
        Find a user profile by email.

        :param email: user's email
        :return: user profile
        """
        return await self._verification_code.find_one({"email": email})

    async def find_code(self, code: int):
        return await self._verification_code.find_one({"code": code})
