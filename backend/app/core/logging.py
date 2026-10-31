import logging
import sys
from app.core.config import settings


def setup_logging() -> logging.Logger:
    """Configure basic structured application logging without exposing secrets."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger("janmitra")
    logger.setLevel(log_level)
    return logger


def get_logger(name: str = "janmitra") -> logging.Logger:
    """Return a named logger configured with application log settings."""
    return logging.getLogger(name)


logger = setup_logging()

