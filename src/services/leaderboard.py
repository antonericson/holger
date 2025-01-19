from motor.motor_asyncio import AsyncIOMotorDatabase

class LeaderboardService:
    def __init__(self, db: AsyncIOMotorDatabase): # type: ignore
        self.db = db

    async def get_top_memes(self, limit: int = 10):
        return await self.db.memes.find().sort("reactions", -1).limit(limit).to_list(None)

    async def get_top_posters(self, limit: int = 10):
        return await self.db.users.find().sort("memes_posted", -1).limit(limit).to_list(None)

    async def get_user_stats(self, user_id: int):
        return await self.db.users.find_one({"user_id": user_id})