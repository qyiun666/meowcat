# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat HTTP connection pool — shared httpx AsyncClient singleton.

Provides a reusable connection pool for all HTTP-based tools (Browser,
ChromaStore, MCP HTTP transport, builtin http_get) with configurable
timeout and connection limits. Eliminates per-request client creation.

Usage::

    from meowcat.utils.http import get_shared_client, close_shared_client

    client = get_shared_client(timeout=30)
    resp = await client.get("https://api.example.com/data")
    await close_shared_client()  # graceful shutdown
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_shared_client: Any = None
_shared_client_config: dict[str, Any] = {}


def get_shared_client(
    *,
    timeout: float = 30.0,
    max_connections: int = 100,
    max_keepalive: int = 20,
    headers: dict[str, str] | None = None,
) -> Any:
    """Get or create a shared httpx AsyncClient.

    On first call, creates a new client with the given config.
    Subsequent calls return the same client — config params are
    ignored once created. To force re-creation, call
    :func:`close_shared_client` first.

    Args:
        timeout: Request timeout in seconds (default 30).
        max_connections: Max concurrent connections (default 100).
        max_keepalive: Max keep-alive connections (default 20).
        headers: Default headers for every request.

    Returns:
        Shared ``httpx.AsyncClient`` instance.

    Raises:
        ImportError: If ``httpx`` is not installed.
    """
    global _shared_client, _shared_client_config

    if _shared_client is not None:
        return _shared_client

    try:
        import httpx  # type: ignore[import-not-found,import-untyped]
    except ImportError:
        logger.warning(
            "httpx not installed — HTTP features require: pip install httpx")
        raise ImportError(
            "httpx not installed. Install with: pip install httpx") from None

    limits = httpx.Limits(
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive,
    )
    _shared_client = httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        limits=limits,
        headers=headers or {"User-Agent": "MeowCat/1.0"},
        follow_redirects=True,
    )
    _shared_client_config = {
        "timeout": timeout,
        "max_connections": max_connections,
        "max_keepalive": max_keepalive,
    }
    logger.info(
        "Shared HTTP client created: timeout=%.1fs, max_conn=%d, keepalive=%d",
        timeout,
        max_connections,
        max_keepalive,
    )
    return _shared_client


async def close_shared_client() -> None:
    """Gracefully close the shared HTTP client, releasing connections."""
    global _shared_client, _shared_client_config

    if _shared_client is not None:
        await _shared_client.aclose()
        _shared_client = None
        _shared_client_config = {}
        logger.info("Shared HTTP client closed")
