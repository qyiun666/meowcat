"""meowcat utility modules — shared helpers with zero framework dependency.

``meowcat/utils/`` has zero meowagent dependency.
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

from meowcat.utils.http import close_shared_client, get_shared_client

__all__ = [
    "get_shared_client",
    "close_shared_client",
]
