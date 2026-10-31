import logging
import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    token: str
    channel_id: int
    data_dir: Path
    tz: ZoneInfo
    rescan_days: int
    log_level: str

    @property
    def db_path(self) -> Path:
        return self.data_dir / "holger.db"

    @property
    def heartbeat_path(self) -> Path:
        return self.data_dir / "heartbeat"


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable {name}")
    return value


def load_config() -> Config:
    load_dotenv()
    data_dir = Path(os.environ.get("DATA_DIR", "./data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return Config(
        token=_required("DISCORD_TOKEN"),
        channel_id=int(_required("CHANNEL_ID")),
        data_dir=data_dir,
        tz=ZoneInfo(os.environ.get("TZ", "UTC")),
        rescan_days=int(os.environ.get("RESCAN_DAYS", "7")),
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    )


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
