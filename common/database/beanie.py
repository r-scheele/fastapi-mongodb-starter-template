from motor.motor_asyncio import AsyncIOMotorClient
from beanie import Document, Indexed, init_beanie


from common.config import cfg
from authentication.entities import UserProfile, JwtRefreshToken
from common.utils.utilities.verification_code.entity import VerificationCode


async def connect():
    # Create Motor client
    client = AsyncIOMotorClient(cfg.mongo_uri)
    # # Init beanie with the Product document class
    db = client.get_database(cfg.mongo_db)
    await init_beanie(
        database=db,
        document_models=[UserProfile, JwtRefreshToken, VerificationCode],
    )
