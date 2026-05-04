"""meowcat plus HTTP client tool — http_get.

Concrete I/O implementation that performs HTTP GET requests via httpx.
Import from ``meowcat.plus.tools`` or ``meowcat.plus``.
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

from typing import Any

from meowcat.constants import HTTP_CLIENT_MAX_RESPONSE_CHARS
from meowcat.tools.tool import RiskLevel, Tool, ToolSpec


async def _http_get(url: str, **_: Any) -> str:
    """HTTP GET request."""
    try:
        import httpx
    except ImportError:
        return "httpx not installed. Run: pip install httpx"

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(
                url, headers={"User-Agent": "MeowCat/1.0"})
            resp.raise_for_status()
            return resp.text[:HTTP_CLIENT_MAX_RESPONSE_CHARS]
    except Exception as e:
        return f"HTTP error: {e}"


plus_http_get = Tool(
    ToolSpec(
        name="http_get",
        description="Make an HTTP GET request to a URL",
        parameters={"url": {"type": "string", "description": "URL to fetch"}},
        risk=RiskLevel.LOW,
        category="network",
    ),
    handler=_http_get,
)
