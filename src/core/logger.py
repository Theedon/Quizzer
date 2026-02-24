import sys
from pathlib import Path

from loguru import logger as _logger

from .settings import settings

logger = _logger
_configured = False


def _pretty_format() -> str:
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )


def configure_logging(*, force: bool = False) -> None:
    global _configured

    if _configured and not force:
        return

    environment = settings.ENVIRONMENT
    logger.remove()

    if environment == "development":
        logger.add(
            sys.stderr,
            level=settings.LOG_LEVEL,
            colorize=True,
            format=_pretty_format(),
            backtrace=True,
            diagnose=True,
            enqueue=False,
        )
    elif environment == "production":
        log_dir = Path(settings.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"

        logger.add(
            sys.stderr,
            level="INFO",
            colorize=False,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
            backtrace=True,
            diagnose=False,
            enqueue=True,
        )
        logger.add(
            str(log_file),
            level="INFO",
            rotation=settings.LOG_ROTATION,
            retention=settings.LOG_RETENTION,
            compression=settings.LOG_COMPRESSION,
            serialize=True,
            backtrace=True,
            diagnose=False,
            enqueue=True,
            catch=True,
        )
    else:
        logger.add(
            sys.stderr,
            level="WARNING",
            colorize=False,
            format="{level: <8} | {message}",
            backtrace=True,
            diagnose=False,
            enqueue=False,
        )

    logger.configure(extra={"environment": environment, "application": "quizzer"})
    _configured = True
