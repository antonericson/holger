from dataclasses import dataclass
from datetime import datetime

@dataclass
class Meme:
    message_id: int
    author_id: int
    reactions: list
    timestamp: datetime
