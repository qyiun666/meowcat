# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat plus file operation tools — read_file / write_file.

Concrete I/O implementations that depend on the local filesystem.
Import from ``meowcat.plus.tools`` or ``meowcat.plus``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from meowcat.constants import FILE_OPS_MAX_READ_CHARS
from meowcat.tools.tool import RiskLevel, Tool, ToolSpec

logger = logging.getLogger(__name__)

# -- Working directory ------------------------------------------------

_DEFAULT_WORKSPACE = Path.home() / ".meowcat" / "workspace"


def _resolve_path(path: str, workspace: Path | None = None) -> Path:
    """Resolve path, constrain within workspace.

    Uses ``os.path.realpath`` to resolve all symlinks and checks that
    every parent component stays within the workspace to prevent
    symlink-based path traversal escapes.
    """
    ws = workspace or _DEFAULT_WORKSPACE
    ws_resolved = ws.resolve()
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (ws / p).resolve()
    else:
        p = p.resolve()

    # Resolve all symlinks via realpath
    real = Path(os.path.realpath(str(p)))
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

    # Check each parent component for symlink escapes
    for parent in real.parents:
        if parent == real.anchor:
            break
        if parent.is_symlink():
            resolved_parent = parent.resolve()
            try:
                resolved_parent.relative_to(ws_resolved)
            except ValueError:
                logger.warning(
                    "Path traversal blocked: symlink %s → %s outside workspace",
                    parent, resolved_parent,
                )
                raise ValueError(
                    f"Path traversal detected: {parent} is a symlink "
                    f"pointing outside the workspace"
                )

    # Security check: ensure resolved real path within workspace
    try:
        real.relative_to(ws_resolved)
    except ValueError:
        logger.warning("Path outside workspace: %s", real)
        raise ValueError(
            f"Path is outside the workspace: {real}"
        )
    return real


# -- File operation handlers ----------------------------------------


async def _read_file(path: str, **_: Any) -> str:
    """Read file contents."""
    if not path.strip():
        return "Error: empty file path"
    p = _resolve_path(path)
    if not p.exists():
        return f"File not found: {p}"
    if p.stat().st_size > 1024 * 1024:
        return f"File too large ({p.stat().st_size / 1024:.0f} KB), max 1 MB"
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:FILE_OPS_MAX_READ_CHARS]
    except Exception as e:
        return f"Read error: {e}"


async def _write_file(path: str, content: str, **_: Any) -> str:
    """Write file contents."""
    p = _resolve_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(content, encoding="utf-8")
        return f"Written: {p} ({len(content)} bytes)"
    except Exception as e:
        return f"Write error: {e}"


# -- Tool definitions ---------------------------------------


plus_read_file = Tool(
    ToolSpec(
        name="read_file",
        description="Read the contents of a file at the given path",
        parameters={"path": {"type": "string", "description": "File path"}},
        risk=RiskLevel.LOW,
        category="file",
    ),
    handler=_read_file,
)

plus_write_file = Tool(
    ToolSpec(
        name="write_file",
        description="Write content to a file",
        parameters={
            "path": {"type": "string", "description": "File path"},
            "content": {"type": "string", "description": "Content to write"},
        },
        risk=RiskLevel.HIGH,
        category="file",
    ),
    handler=_write_file,
)

