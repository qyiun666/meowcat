# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat plus filesystem tools — list_dir / grep_files.

Concrete I/O implementations for directory listing and file-content search.
Import from ``meowcat.plus.tools`` or ``meowcat.plus``.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from meowcat.constants import COMMAND_MAX_OUTPUT_CHARS
from meowcat.tools.tool import RiskLevel, Tool, ToolSpec

logger = logging.getLogger(__name__)

_DEFAULT_WORKSPACE = Path.home() / ".meowcat" / "workspace"

# -- list_dir ----------------------------------------------------------


async def _list_dir(path: str, **_: Any) -> str:
    """List directory contents, truncated at 200 entries with file sizes."""
    ws = _DEFAULT_WORKSPACE
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (ws / p).resolve()
    else:
        p = p.resolve()

    if not p.exists():
        return f"Directory not found: {p}"
    if not p.is_dir():
        return f"Not a directory: {p}"

    try:
        entries: list[str] = []
        for entry in sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            if len(entries) >= 200:
                entries.append("... (truncated)")
                break
            try:
                sz = entry.stat().st_size
            except OSError:
                sz = 0
            prefix = "[DIR] " if entry.is_dir() else "[FILE]"
            entries.append(f"{prefix} {entry.name}  ({_fmt_size(sz)})")
        return "\n".join(entries)
    except PermissionError:
        return f"Permission denied: {p}"
    except Exception as e:
        return f"List error: {e}"


plus_list_dir = Tool(
    ToolSpec(
        name="list_dir",
        description="List directory contents (truncated at 200 entries, includes file sizes)",
        parameters={"path": {"type": "string",
                             "description": "Directory path"}},
        risk=RiskLevel.LOW,
        category="file",
    ),
    handler=_list_dir,
)

# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

# -- grep_files --------------------------------------------------------


async def _grep_files(pattern: str, path: str, **_: Any) -> str:
    """Search file contents with regex, max 300 files."""
    ws = _DEFAULT_WORKSPACE
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (ws / p).resolve()
    else:
        p = p.resolve()

    if not p.exists():
        return f"Path not found: {p}"

    try:
        pat = re.compile(pattern)
    except re.error as e:
        return f"Invalid regex: {e}"

    results: list[str] = []
    file_count = 0

    def _search_dir(d: Path) -> None:
        nonlocal file_count
        try:
            for entry in sorted(d.iterdir()):
                if file_count >= 300:
                    return
                if entry.name.startswith('.') and entry.name not in ('.', '..'):
                    continue
                if entry.is_dir():
                    _search_dir(entry)
                elif entry.is_file():
                    file_count += 1
                    if file_count > 300:
                        return
                    try:
                        content = entry.read_text(
                            encoding="utf-8", errors="replace")
                    except Exception:
                        return
                    for lineno, line in enumerate(content.splitlines(), 1):
                        if pat.search(line):
                            results.append(
                                f"{entry}:{lineno}: {line[:200]}")
                            if len(results) >= 500:
                                return
        except PermissionError:
            pass

    if p.is_dir():
        _search_dir(p)
    else:
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(content.splitlines(), 1):
                if pat.search(line):
                    results.append(f"{p}:{lineno}: {line[:200]}")
                    if len(results) >= 500:
                        break
        except Exception as e:
            return f"Read error: {e}"

    if not results:
        return f"No matches for pattern '{pattern}' (searched {file_count} files)"
    header = f"Found {len(results)} matches in {file_count} files:\n"
    return header + "\n".join(results)[:COMMAND_MAX_OUTPUT_CHARS]


plus_grep_files = Tool(
    ToolSpec(
        name="grep_files",
        description="Search file contents with regex (max 300 files)",
        parameters={
            "pattern": {"type": "string", "description": "Regex pattern"},
            "path": {"type": "string", "description": "Directory or file path"},
        },
        risk=RiskLevel.LOW,
        category="file",
    ),
    handler=_grep_files,
)

# -- helpers -----------------------------------------------------------


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f}MB"
    return f"{size / (1024 * 1024 * 1024):.1f}GB"


__all__ = ["plus_list_dir", "plus_grep_files"]

