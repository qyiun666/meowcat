# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat plus — optional pluggable module pack.

Install with ``pip install meowcat[plus]`` to pull in runtime dependencies
(httpx, playwright, chromadb).  Pure-framework users get zero I/O imports
because everything in ``meowcat/plus/`` is only loaded on demand.

See :ref:`meowcat-plus-architecture`.
"""

from __future__ import annotations
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


from meowcat.plus.browser import BrowserTool
from meowcat.plus.chroma_store import ChromaStore
from meowcat.plus.mcp_client import MCPClient, MCPServerConfig, MCPTool
from meowcat.plus.skill_loader import SkillLoader
from meowcat.plus.crystallizer import Crystallizer, DefaultDetector
from meowcat.plus.tools import BUILTIN_TOOLS
from meowcat.plus.gateway import (
    HttpAdapter,
    WsAdapter,
    WebhookAdapter,
    CliAdapter,
    IpcAdapter,
)
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


__all__ = [
    "BrowserTool",
    "ChromaStore",
    "MCPClient",
    "MCPServerConfig",
    "MCPTool",
    "SkillLoader",
    "Crystallizer",
    "DefaultDetector",
    "BUILTIN_TOOLS",
    "HttpAdapter",
    "WsAdapter",
    "WebhookAdapter",
    "CliAdapter",
    "IpcAdapter",
]

