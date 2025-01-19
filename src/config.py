from dataclasses import dataclass
import os
from dotenv import load_dotenv

@dataclass
class Config:
    CHANNEL_ID: int
    BOT_TOKEN: str
    MONGO_URI: str
    DB_NAME: str
    LOG_LEVEL: str

def load_config() -> Config:
    load_dotenv()
    return Config(
        CHANNEL_ID=int(os.getenv('CHANNEL_ID')),
        BOT_TOKEN=os.getenv('BOT_TOKEN'),
        MONGO_URI=os.getenv('MONGO_URI', 'mongodb://localhost:27017/'),
        DB_NAME=os.getenv('DB_NAME', 'holger_db'),
        LOG_LEVEL=os.getenv('LOG_LEVEL')
    )
