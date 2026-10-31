"""Docker healthcheck for the collector.

`python -m holger.healthcheck` fails when the heartbeat file has not been touched recently.
"""

import os
import sys
import time
from pathlib import Path

MAX_HEARTBEAT_AGE = 180  # seconds


def main() -> None:
    heartbeat = Path(os.environ.get("DATA_DIR", "./data")) / "heartbeat"
    try:
        age = time.time() - heartbeat.stat().st_mtime
    except FileNotFoundError:
        sys.exit("No heartbeat yet")
    if age > MAX_HEARTBEAT_AGE:
        sys.exit(f"Heartbeat is {age:.0f}s old")


if __name__ == "__main__":
    main()
