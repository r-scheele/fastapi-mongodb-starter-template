import glob
import hashlib
import random
from pathlib import Path
from typing import Any, List
from fastapi import status, Cookie, HTTPException, Depends, BackgroundTasks

from PIL import Image
from injector import singleton, inject

from common.concurrency import cpu_bound_task
from common.config import cfg
from common.injection import on
from authentication.service import AuthService
from authentication.repo import AuthRepo


@singleton
class AvatarService:
    @inject
    def __init__(self, repo: AuthRepo):
        self._avatar_images_path = Path(cfg.avatar_data_folder)
        self._avatar_images_path.mkdir(exist_ok=True, parents=True)
        self._bodies = self._get_layers_paths("bodies")
        self._accessories = self._get_layers_paths("accessories")
        self._glasses = self._get_layers_paths("glasses")
        self._hats = self._get_layers_paths("hats")

        self._user_repo = repo

    async def generate_and_save_avatar(self, identifier: str, email: str) -> None:
        await cpu_bound_task(self._generate_and_save_avatar, identifier, email)

    async def generate_avatar(self, identifier: str) -> Any:
        return await cpu_bound_task(self._generate_avatar, identifier)

    def _generate_and_save_avatar(self, identifier: str, email: str) -> None:
        avatar_image = self._generate_avatar(identifier)
        avatar_image.save(
            self._avatar_images_path / f"{email}.png", "PNG", optimize=True
        )

    def _generate_avatar(self, identifier: str) -> Any:
        identifier_hash = int(
            hashlib.md5(str(identifier).encode()).hexdigest(), base=16
        )
        random.seed(identifier_hash)
        layer0 = self._bodies[random.randint(0, len(self._bodies) - 1)]
        layer1 = self._accessories[random.randint(0, len(self._accessories) - 1)]
        layer2 = self._glasses[random.randint(0, len(self._glasses) - 1)]
        layer3 = self._hats[random.randint(0, len(self._hats) - 1)]
        avatar = Image.alpha_composite(Image.open(layer0), Image.open(layer1))
        avatar = Image.alpha_composite(avatar, Image.open(layer2))
        avatar = Image.alpha_composite(avatar, Image.open(layer3))
        return avatar

    def _get_layers_paths(self, layer_type: str) -> List[str]:
        paths = glob.glob(f"authentication/avatar/images/{layer_type}/*")
        paths.sort()
        return paths

    async def save_avatar(self, identifier: str, email: str):
        """
        Save identifier to database.

        :param identifier: identifier
        :param email: email
        :return: None
        """
        res = await self.generate_and_save_avatar(identifier, email)
        return await self._user_repo.save_avatar(identifier, email)
