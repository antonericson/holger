from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

class MemeTrackingService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def create_user_if_not_exists(self, user_id):
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$setOnInsert": {
                "user_id": user_id,
                "reactions_given": [],
                "reactions_recieved": [],
                "memes_posted": [],
                "tracked_since": datetime.now()
            }},
            upsert=True
        )

    async def create_meme_if_not_exists(self, message_id,):
        await self.db.memes.update_one(
            {"message_id": message_id},
            {"$setOnInsert": {
                "message_id": message_id,
                "author_id": "Unknown",
                "reactions": [],
                "timestamp": datetime.now()
            }},
            upsert=True
        )
    
    async def update_meme_with_reactions(self, message_id, reactor_user_id, add):
        meme_reaction_data = {
            "user_id": reactor_user_id,
            "count": 1,
            "first_reacted": datetime.now()
        }
        # Update meme reactions count and add reaction details
        await self.db.memes.update_one(
            {
                "message_id": message_id,
                "reactions.user_id": reactor_user_id
            },
            {
                "$inc": {"reactions.$.count": 1 if add else -1},
            } if add else {
                "$inc": {"reactions.$.count": -1}
            }
        )

        # If no existing reaction found, insert new one
        if add:
            await self.db.memes.update_one(
                {
                    "message_id": message_id,
                    "reactions.user_id": {"$ne": reactor_user_id}
                },
                {"$push": {"reactions": meme_reaction_data}}
            )
        
        # Clean up any reactions with count 0
        await self.db.memes.update_one(
            {"message_id": message_id},
            {"$pull": {"reactions": {"count": {"$lte": 0}}}}
        )


    async def update_reactor_with_reactions(self, message_id, reactor_user_id, add):
        user_reaction_data = {
            "message_id": message_id,
            "count": 1,
            "first_reacted": datetime.now()
        }
        # Update reactions given by reactor using upsert and inc
        await self.db.users.update_one(
            {
                "user_id": reactor_user_id,
                "reactions_given.message_id": message_id
            },
            {
                "$inc": {"reactions_given.$.count": 1 if add else -1},
            } if add else {
                "$inc": {"reactions_given.$.count": -1}
            }
        )

        # If no existing reaction found, insert new one
        if add:
            await self.db.users.update_one(
                {
                    "user_id": reactor_user_id,
                    "reactions_given.message_id": {"$ne": message_id}
                },
                {"$push": {"reactions_given": user_reaction_data}}
            )

        # Clean up any reactions with count 0
        await self.db.users.update_one(
            {"user_id": reactor_user_id},
            {"$pull": {"reactions_given": {"count": {"$lte": 0}}}}
        )

    async def update_op_with_reactions(self, message_id, op_user_id, add):
        op_reaction_data = {
            "message_id": message_id,
            "count": 1,
            "first_reacted": datetime.now()
        }
        # Update reactions given by reactor using upsert and inc
        await self.db.users.update_one(
            {
                "user_id": op_user_id,
                "reactions_recieved.message_id": message_id
            },
            {
                "$inc": {"reactions_recieved.$.count": 1 if add else -1},
            } if add else {
                "$inc": {"reactions_recieved.$.count": -1}
            }
        )

        # If no existing reaction found, insert new one
        if add:
            await self.db.users.update_one(
                {
                    "user_id": op_user_id,
                    "reactions_recieved.message_id": {"$ne": message_id}
                },
                {"$push": {"reactions_recieved": op_reaction_data}}
            )

        # Clean up any reactions with count 0
        await self.db.users.update_one(
            {"user_id": op_user_id},
            {"$pull": {"reactions_recieved": {"count": {"$lte": 0}}}}
        )

    async def track_meme(self, message_id: int, author_id: int):
        await self.create_user_if_not_exists(author_id)
        
        meme_data = {
            "message_id": message_id,
            "timestamp": datetime.now()
        }
        
        # Add meme to user's posted memes list
        await self.db.users.update_one(
            {"user_id": author_id},
            {"$push": {"memes_posted": meme_data}}
        )
        
        # Insert meme record
        await self.db.memes.insert_one({
            "message_id": message_id,
            "author_id": author_id,
            "reactions": [],
            "timestamp": datetime.now()
        })

    async def track_reaction(self, message_id: int, reactor_user_id: int, add: bool = True):
        await self.create_meme_if_not_exists(message_id)
        await self.create_user_if_not_exists(reactor_user_id)

        meme = await self.db.memes.find_one({"message_id": message_id})
        op_user_id = meme["author_id"]
        if meme and op_user_id == reactor_user_id:
            return

        await self.update_reactor_with_reactions(message_id, reactor_user_id, add)
        await self.update_op_with_reactions(message_id, op_user_id, add)
        await self.update_meme_with_reactions(message_id, reactor_user_id, add)

        