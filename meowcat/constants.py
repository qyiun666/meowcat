"""meowcat shared constants — extracted magic numbers (v1.2.33).

Previously hardcoded across plus/ and colony/ modules.
Centralising here makes thresholds configurable and self-documenting.

See :ref:`docs/架构/00-meowcat-框架架构.md` §21 for the architecture context.
"""
# (c) 2025-2026 Axonant. MIT License.


# -- Browser (meowcat.plus.browser) ----------------------------------

BROWSER_MAX_TEXT_CHARS: int = 10000
"""Max characters returned by browser text-content methods."""

BROWSER_MAX_HTML_CHARS: int = 50000
"""Max characters returned by browser get_content()."""

BROWSER_MAX_RESULT_CHARS: int = 5000
"""Max characters returned by browser evaluate()."""


# -- File operations (meowcat.plus.tools.file_ops) --------------------

FILE_OPS_MAX_READ_CHARS: int = 8000
"""Max characters returned by read_file tool (safeguard against huge files)."""


# -- Command execution (meowcat.plus.tools.command) -------------------

COMMAND_MAX_OUTPUT_CHARS: int = 4000
"""Max output characters retained from a subprocess command."""

COMMAND_DEFAULT_TIMEOUT: int = 30
"""Default timeout in seconds for subprocess command execution."""


# -- HTTP client (meowcat.plus.tools.http_client) ---------------------

HTTP_CLIENT_MAX_RESPONSE_CHARS: int = 5000
"""Max response characters returned by http_get tool."""


# -- Gateway adapters (meowcat.plus.gateway) --------------------------

GATEWAY_DEFAULT_TIMEOUT: int = 30
"""Default timeout in seconds for HTTP request-line read in gateway adapters."""


# -- MCP client (meowcat.plus.mcp_client) -----------------------------

MCP_DEFAULT_TIMEOUT: float = 30.0
"""Default timeout in seconds for MCP operations (discovery, tool call)."""


# -- Colony federation transports (meowcat.colony_transports) -----------

TRANSPORT_REQUEST_TIMEOUT: float = 30.0
"""Default timeout in seconds for federation request-response cycles.

Previously named ``_REQUEST_TIMEOUT`` in :mod:`meowcat.colony_transports`.
"""


# -- UID generation (v1.3.x) -----------------------------------------

CALL_SIGN_RAW: str = "zhaotongshigedashuaige|chinaniubi"
"""Raw call-sign string used to derive the copyright watermark in
colony/cat UIDs.  Kept as a constant so the hash can be recomputed
programmatically."""

CALL_SIGN: str = "0efb30"
"""Pre-computed MD5 first-6-hex of ``CALL_SIGN_RAW``.

Embedded as the watermark prefix in every auto-generated ``colony_uid``.
MD5('zhaotongshigedashuaige|chinaniubi') → ``0efb30...``
"""


__all__ = [
    "BROWSER_MAX_TEXT_CHARS",
    "BROWSER_MAX_HTML_CHARS",
    "BROWSER_MAX_RESULT_CHARS",
    "FILE_OPS_MAX_READ_CHARS",
    "COMMAND_MAX_OUTPUT_CHARS",
    "COMMAND_DEFAULT_TIMEOUT",
    "HTTP_CLIENT_MAX_RESPONSE_CHARS",
    "GATEWAY_DEFAULT_TIMEOUT",
    "MCP_DEFAULT_TIMEOUT",
    "TRANSPORT_REQUEST_TIMEOUT",
    "CALL_SIGN_RAW",
    "CALL_SIGN",
]
