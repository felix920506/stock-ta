"""Shared logging setup. Call configure() once from an entry point,
after loading .env. Level is read from STOCK_TA_LOG_LEVEL (default INFO).
Logs go to stderr so stdout stays clean for reports / JSON output.
"""

import logging
import os
import sys

_configured = False


def configure() -> None:
    global _configured
    if _configured:
        return
    lvl = os.environ.get("STOCK_TA_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, lvl, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    _configured = True
