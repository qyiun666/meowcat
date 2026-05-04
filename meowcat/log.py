"""meowcat structured logger — pluggable handlers + context-aware logging.

Replaces scattered ``logging.getLogger(...)`` calls with a unified structured
logger. Supports pluggable handlers for external sinks (file, network, etc.).

Usage::

    from meowcat.log import MeowLog

    log = MeowLog.get("meowcat.colony")
    log.info("cat_created", cat_id="planner", colony="feishu")

    # Custom handler
    MeowLog.plug_handler(lambda entry: print(entry))
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

import logging
import time
from typing import Any, Callable

_loggers: dict[str, "MeowLog"] = {}
_handlers: list[Callable[[dict[str, Any]], None]] = []


class MeowLog:
    """Structured logger with pluggable handlers.

    Wraps stdlib :mod:`logging` and adds structured ``**data`` + handler pipeline.
    """

    __slots__ = ("_name", "_py")

    def __init__(self, name: str) -> None:
        self._name = name
        self._py = logging.getLogger(name)

    @classmethod
    def get(cls, name: str) -> "MeowLog":
        """Get or create a logger by name (singleton per name)."""
        if name not in _loggers:
            _loggers[name] = cls(name)
        return _loggers[name]

    @classmethod
    def plug_handler(cls, handler: Callable[[dict[str, Any]], None]) -> None:
        """Register a custom handler. Receives ``{level, message, timestamp, logger, data}``."""
        _handlers.append(handler)

    @classmethod
    def clear_handlers(cls) -> None:
        """Remove all custom handlers."""
        _handlers.clear()

    # -- Level methods --------------------------------------------------

    def debug(self, msg: str, **data: Any) -> None:
        self._emit("DEBUG", msg, data)

    def info(self, msg: str, **data: Any) -> None:
        self._emit("INFO", msg, data)

    def warning(self, msg: str, **data: Any) -> None:
        self._emit("WARNING", msg, data)

    def error(self, msg: str, **data: Any) -> None:
        self._emit("ERROR", msg, data)

    # -- Internal --------------------------------------------------------

    def _emit(self, level: str, msg: str, data: dict[str, Any]) -> None:
        entry: dict[str, Any] = {
            "level": level,
            "message": msg,
            "timestamp": time.time(),
            "logger": self._name,
            "data": data,
        }
        level_int = getattr(logging, level)
        self._py.log(level_int, "%s  %s", msg, data or "")
        for handler in _handlers:
            try:
                handler(entry)
            except Exception:
                pass


__all__ = ["MeowLog"]
