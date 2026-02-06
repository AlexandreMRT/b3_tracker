"""
Centralized logging configuration for B3 Tracker.

Usage in any module:
    import logging
    logger = logging.getLogger(__name__)
    logger.info("message")

Or import the pre-configured logger:
    from logger import get_logger
    logger = get_logger(__name__)
"""
import logging
import os
import sys


LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


_logging_configured = False


def setup_logging() -> None:
    """Configure root logger. Call once at application startup."""
    global _logging_configured
    if _logging_configured:
        return
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        stream=sys.stdout,
    )
    # Quieten noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a named logger (ensures logging is configured)."""
    setup_logging()
    return logging.getLogger(name)
