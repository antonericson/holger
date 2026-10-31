"""Health signals.

`python -m holger.healthcheck` is the collector's Docker healthcheck: it fails when the
heartbeat file has not been touched recently. `ping` reports reporter runs to healthchecks.io.
"""

import logging
import os
import sys
import time
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

MAX_HEARTBEAT_AGE = 180  # seconds


def ping(url: str | None, fail: bool = False) -> None:
    if not url:
        return
    try:
        urllib.request.urlopen(url.rstrip("/") + ("/fail" if fail else ""), timeout=10)
    except OSError:
        log.warning("Healthcheck ping failed", exc_info=True)


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
