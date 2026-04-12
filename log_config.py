"""Shared logging setup. Call configure() once from an entry point,
after loading .env.

Level:       STOCK_TA_LOG_LEVEL (default INFO)
Destination: STOCK_TA_LOG_FILE  (default "log.txt"; use "-" or "stderr"
             for stderr, "stdout" for stdout)
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
    dest = os.environ.get("STOCK_TA_LOG_FILE", "log.txt")

    kwargs = dict(
        level=getattr(logging, lvl, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if dest in ("-", "stderr", ""):
        kwargs["stream"] = sys.stderr
    elif dest == "stdout":
        kwargs["stream"] = sys.stdout
    else:
        kwargs["filename"] = dest

    logging.basicConfig(**kwargs)
    _configured = True
