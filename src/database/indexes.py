import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

async def create_indexes(db: AsyncIOMotorDatabase):
    logger = logging.getLogger('holger')
    await db.memes.create_index([("reactions", -1), ("timestamp", -1)])
    await db.users.create_index([("memes_posted", -1)])
    await db.users.create_index([("reactions_given", -1)])
    logger.info("Indexes created successfully")
