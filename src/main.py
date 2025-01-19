from motor.motor_asyncio import AsyncIOMotorClient
from src.bot import HolgerBot
from src.config import load_config
from src.utils.logging import setup_logging

def main():
    config = load_config()
    setup_logging(config.LOG_LEVEL)

    mongo_client = AsyncIOMotorClient(config.MONGO_URI)
    db = mongo_client[config.DB_NAME]

    bot = HolgerBot(db, config.CHANNEL_ID) 
    bot.run(config.BOT_TOKEN)

if __name__ == "__main__":
    main()
