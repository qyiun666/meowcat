"""meowcat 通用内置工具 — 所有猫都需要的原子操作。

这些不依赖 meowagent，纯框架层。任何 ``pip install meowcat`` 的用户
都能获得这些开箱即用的基础工具。

内置工具集:
- read_file: 读取文件内容
- write_file: 写入文件
- run_command: 执行 Shell 命令
- http_get: HTTP GET 请求
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from meowcat.tools.tool import RiskLevel, Tool, ToolSpec

# -- 工作目录 -------------------------------------------------------

_DEFAULT_WORKSPACE = Path.home() / ".meowcat" / "workspace"


def _resolve_path(path: str, workspace: Path | None = None) -> Path:
    """解析路径，限制在 workspace 内。"""
    ws = workspace or _DEFAULT_WORKSPACE
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (ws / p).resolve()
    else:
        p = p.resolve()
    # 安全检查：确保在 workspace 内
    try:
        p.relative_to(ws.resolve())
    except ValueError:
        p = ws / p.name
    return p


# -- 文件操作 handlers ----------------------------------------------


async def _read_file(path: str, **_: Any) -> str:
    """读取文件内容。"""
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
    """写入文件内容。"""
    p = _resolve_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(content, encoding="utf-8")
        return f"Written: {p} ({len(content)} bytes)"
    except Exception as e:
        return f"Write error: {e}"


# -- 命令执行 -------------------------------------------------------


async def _run_command(command: str, **_: Any) -> str:
    """执行 Shell 命令。"""
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


# -- HTTP 请求 ------------------------------------------------------


async def _http_get(url: str, **_: Any) -> str:
    """HTTP GET 请求。"""
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


# -- 内置工具定义 ---------------------------------------------------


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


# -- 通用工具集 -----------------------------------------------------

BUILTIN_TOOLS: list[Tool] = [
    builtin_read_file,
    builtin_write_file,
    builtin_run_command,
    builtin_http_get,
]
