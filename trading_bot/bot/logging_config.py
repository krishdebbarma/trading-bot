import logging
import logging.handlers
import os
from pathlib import Path

_INITIALIZED = False


def get_logger(name: str = "trading_bot") -> logging.Logger:
    global _INITIALIZED
    logger = logging.getLogger(name)
    if _INITIALIZED:
        return logger

    log_dir = Path(os.getenv("BOT_LOG_DIR",
                             Path(__file__).resolve().parent.parent / "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    file_h = logging.handlers.RotatingFileHandler(
        log_dir / "bot.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8",
    )
    file_h.setLevel(logging.INFO)
    file_h.setFormatter(fmt)

    console_h = logging.StreamHandler()
    console_h.setLevel(logging.WARNING)
    console_h.setFormatter(fmt)

    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(file_h)
    logger.addHandler(console_h)

    _INITIALIZED = True
    return logger
