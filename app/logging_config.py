"""Logging configuration: colored text in dev, JSON-ish lines in prod."""

from __future__ import annotations

import logging
from logging.config import dictConfig

from app.config import get_settings


def configure_logging() -> None:
    """Apply a dictConfig based on the current environment."""

    settings = get_settings()
    is_dev = settings.ENV == "dev"
    level = "DEBUG" if is_dev else "INFO"

    if is_dev:
        fmt = "\x1b[2m%(asctime)s\x1b[0m %(levelname)-8s \x1b[36m%(name)s\x1b[0m %(message)s"
    else:
        fmt = (
            '{"time": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": {"format": fmt}},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "root": {"handlers": ["console"], "level": level},
            "loggers": {
                "uvicorn": {"handlers": ["console"], "level": level, "propagate": False},
                "uvicorn.error": {"handlers": ["console"], "level": level, "propagate": False},
                "uvicorn.access": {"handlers": ["console"], "level": level, "propagate": False},
            },
        }
    )
    logging.getLogger(__name__).debug("Logging configured (env=%s, level=%s)", settings.ENV, level)
