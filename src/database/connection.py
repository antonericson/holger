import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

async def verify_mongodb_connection(db: AsyncIOMotorDatabase) -> bool:
    logger = logging.getLogger('holger')
    try:
        await db.command('ismaster')
        logger.info("MongoDB connection successful")
        return True
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        return False
