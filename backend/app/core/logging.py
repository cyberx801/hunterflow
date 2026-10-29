"""Structured logging with correlation ids and central redaction.

Every log line carries ts/level/logger/service/event plus the request or job
correlation id. Secret patterns are redacted at the logging boundary
(Constitution P3, HF-SEC-007).
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar

import structlog

from .config import Settings
from .redaction import redact_text

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def set_correlation_id(cid: str | None) -> None:
    correlation_id_var.set(cid)


def get_correlation_id() -> str | None:
    return correlation_id_var.get()


def _add_correlation_id(
    logger: logging.Logger, method_name: str, event_dict: dict
) -> dict:
    cid = correlation_id_var.get()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def _redact_processor(
    logger: logging.Logger, method_name: str, event_dict: dict
) -> dict:
    return {
        k: redact_text(v) if isinstance(v, str) else v
        for k, v in event_dict.items()
    }


def configure_logging(settings: Settings) -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        timestamper,
        _add_correlation_id,
        _redact_processor,
    ]

    if settings.is_production:
        renderer = structlog.processors.JSONRenderer()
        structlog.configure(
            processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        handler = logging.StreamHandler(sys.stdout)
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=renderer, foreign_pre_chain=shared_processors
        )
        handler.setFormatter(formatter)
        root = logging.getLogger()
        root.handlers = [handler]
        root.setLevel(logging.INFO)
    else:
        renderer = structlog.dev.ConsoleRenderer()
        structlog.configure(
            processors=[*shared_processors, renderer],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)


def get_logger(name: str = "hunterflow") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
