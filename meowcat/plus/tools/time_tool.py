# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat plus time tool — current_time.

Returns current UTC and local time for Agent time-awareness.
Import from ``meowcat.plus.tools`` or ``meowcat.plus``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from meowcat.tools.tool import RiskLevel, Tool, ToolSpec


async def _current_time(**_: Any) -> str:
    """Return current UTC and local time as formatted string."""
    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now()
    utc_str = now_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    local_str = now_local.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
    offset = now_local.utcoffset()
    offset_hours = int(offset.total_seconds() / 3600) if offset else 0
    return (
        f"UTC: {utc_str}\n"
        f"Local: {local_str} (UTC{offset_hours:+d})\n"
        f"Unix timestamp: {now_utc.timestamp():.0f}"
    )


plus_current_time = Tool(
    ToolSpec(
        name="current_time",
        description="Return current UTC and local time",
        parameters={},
        risk=RiskLevel.LOW,
        category="system",
    ),
    handler=_current_time,
)

__all__ = ["plus_current_time"]

