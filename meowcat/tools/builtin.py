"""meowcat universal built-in tools — atomic operations every cat needs.

These have no meowagent dependency, pure framework layer. Any ``pip install meowcat`` user
gets these out-of-the-box basic tools.

Built-in tool set:
- read_file: Read file contents
- write_file: Write file
- run_command: Execute shell command
- http_get: HTTP GET request
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from meowcat.tools.tool import RiskLevel, Tool, ToolSpec

# -- Working directory ------------------------------------------------

_DEFAULT_WORKSPACE = Path.home() / ".meowcat" / "workspace"


def _resolve_path(path: str, workspace: Path | None = None) -> Path:
    """Resolve path, constrain within workspace."""
    ws = workspace or _DEFAULT_WORKSPACE
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (ws / p).resolve()
    else:
        p = p.resolve()
    # Security check: ensure within workspace
    try:
        p.relative_to(ws.resolve())
    except ValueError:
        p = ws / p.name
    return p


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
        return p.read_text(encoding="utf-8", errors="replace")[:8000]
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


# -- Command execution -----------------------------------------------


async def _run_command(command: str, **_: Any) -> str:
    """Execute shell command."""
    if not command.strip():
        return "Error: empty command"
    try:
        import shlex
        args = shlex.split(command)
        result = subprocess.run(
            args, capture_output=True, text=True,
            timeout=30, cwd=str(_DEFAULT_WORKSPACE),
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )
        output = result.stdout or result.stderr or "(no output)"
        return output[:4000]
    except subprocess.TimeoutExpired:
        return "Command timed out (30s)"
    except FileNotFoundError:
        return f"Command not found: {command.split()[0]}"
    except Exception as e:
        return f"Command error: {e}"


# -- HTTP requests ---------------------------------------------------


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
            return resp.text[:5000]
    except Exception as e:
        return f"HTTP error: {e}"


# -- Built-in tool definitions ---------------------------------------


builtin_read_file = Tool(
    ToolSpec(
        name="read_file",
        description="Read the contents of a file at the given path",
        parameters={"path": {"type": "string", "description": "File path"}},
        risk=RiskLevel.LOW,
        category="file",
    ),
    handler=_read_file,
)

builtin_write_file = Tool(
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

builtin_run_command = Tool(
    ToolSpec(
        name="run_command",
        description="Execute a shell command",
        parameters={"command": {"type": "string",
                                "description": "Shell command"}},
        risk=RiskLevel.HIGH,
        category="system",
    ),
    handler=_run_command,
)

builtin_http_get = Tool(
    ToolSpec(
        name="http_get",
        description="Make an HTTP GET request to a URL",
        parameters={"url": {"type": "string", "description": "URL to fetch"}},
        risk=RiskLevel.LOW,
        category="network",
    ),
    handler=_http_get,
)


# -- General tool set ------------------------------------------------

BUILTIN_TOOLS: list[Tool] = [
    builtin_read_file,
    builtin_write_file,
    builtin_run_command,
    builtin_http_get,
]
