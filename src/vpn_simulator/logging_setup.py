"""Centralized logging configuration for VPN Simulator v2.

The project logs through structlog everywhere. This module wires structlog to
the standard library ``logging`` pipeline via structlog's stdlib integration,
so structured loggers delegate to the usual logging handlers (uvicorn, the
in-memory :class:`LogHandler`, etc.) while staying structured.

Both entrypoints — the API (``vpn_simulator.api.app``) and the CLI
(``vpn_simulator.cli``) — must call :func:`configure_logging` before any module
that binds a ``structlog.get_logger`` is imported, because structlog caches the
first logger it creates for each name. This module therefore lives at the
package top level (not under ``vpn_simulator.core``, whose ``__init__`` eagerly
imports modules that bind loggers).
"""

from __future__ import annotations

import logging
import os
import sys

import structlog


def configure_logging() -> None:
    """Configure structlog and the underlying stdlib logging pipeline.

    The log level is read from the ``VPN_SIM_LOG_LEVEL`` environment variable
    (matching :class:`vpn_simulator.core.config.ConfigManager`) and defaults to
    ``INFO``.
    """
    level_name = os.getenv("VPN_SIM_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(format="%(message)s", stream=sys.stderr, level=level)

    structlog.configure(
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


__all__ = ["configure_logging"]
