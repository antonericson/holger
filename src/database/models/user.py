from dataclasses import dataclass
from datetime import datetime

@dataclass
class User:
    user_id: int
    memes_posted: list
    reactions_given: list
    reactions_recieved: list
    tracked_since: datetime
