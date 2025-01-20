import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

class LeaderboardService:
    def __init__(self, db: AsyncIOMotorDatabase): # type: ignore
        self.db = db

    async def get_top_memes(self, limit: int = 10):
        return await self.db.memes.find().sort("reactions", -1).limit(limit).to_list(None)

    async def get_top_posters(self, since: datetime, limit: int = 10):
        pipeline = [
            {
                "$project": {
                    "user_id": 1,
                    "username": 1,
                    "memes_count": {
                        "$size": {
                            "$filter": {
                                "input": "$memes_posted",
                                "as": "meme",
                                "cond": {"$gte": ["$$meme.timestamp", since]}
                            }
                        }
                    }
                }
            },
            {"$sort": {"memes_count": -1}},
            {"$limit": limit}
        ]
        return await self.db.users.aggregate(pipeline).to_list(None)

    async def get_user_stats(self, user_id: int):
        return await self.db.users.find_one({"user_id": user_id})
    
    async def get_top_memes_since(self, since_date, limit: int = 10):
        return await self.db.memes.find(
            {"created_at": {"$gte": since_date}}
        ).sort("reactions", -1).limit(limit).to_list(None)