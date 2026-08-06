"""Structured logging configuration."""

import logging


def configure_logging(debug: bool = False) -> None:
    """Configure root logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
