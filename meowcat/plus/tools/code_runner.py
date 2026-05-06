# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat plus code runner — sandboxed code execution.

Executes Python or JavaScript code in an isolated subprocess with
timeout, output truncation, and restricted environment.
Import from ``meowcat.plus.tools`` or ``meowcat.plus``.

Security design:

- **Subprocess isolation**: code runs in a child process, stdout/stderr captured
- **Python -I mode**: isolates ``sys.path``, ignores ``PYTHON*`` env vars
- **Env stripping**: only PATH, HOME, TMPDIR, LANG, LC_ALL passed through
- **Timeout (10s)**: prevents infinite loops / resource exhaustion
- **Output truncation (4000 chars)**: prevents context overflow
- **Dedicated cwd** (``~/.meowcat/workspace``): keeps project files out of scope
- **Non-blocking**: uses ``asyncio.create_subprocess_exec`` to avoid blocking
  the event loop
- **RiskLevel.HIGH**: Paws confirm prompt + Amygdala intercept

Known limitations (acceptable for a framework-layer tool):

- No filesystem isolation (chroot / Docker) — code can read/write files
  as the host user
- No network isolation — code can make outbound HTTP requests
- No resource limits (CPU/memory) beyond timeout
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from meowcat.constants import COMMAND_MAX_OUTPUT_CHARS
from meowcat.tools.tool import RiskLevel, Tool, ToolSpec

_DEFAULT_WORKSPACE = Path.home() / ".meowcat" / "workspace"

# Restricted environment — minimal safe env vars
_SAFE_ENV: dict[str, str] = {
    "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
    "HOME": str(_DEFAULT_WORKSPACE),
    "TMPDIR": tempfile.gettempdir(),
    "LANG": "en_US.UTF-8",
    "LC_ALL": "en_US.UTF-8",
}

_CODE_TIMEOUT = 10  # seconds


async def _code_runner(language: str, code: str, **_: Any) -> str:
    """Execute code in a sandboxed subprocess.
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT


    Args:
        language: ``"python"`` or ``"javascript"``.
        code: Source code string.
    """
    lang = language.strip().lower()
    if lang not in ("python", "javascript"):
        return (
            f"Unsupported language: '{language}'. "
            "Use 'python' or 'javascript'."
        )

    if lang == "python":
        return await _run_python(code)
    return await _run_node(code)


async def _run_python(code: str) -> str:
    """Execute Python code in isolated subprocess (non-blocking)."""
    if not shutil.which("python3"):
        # fallback to python
        exe = shutil.which("python")
        if not exe:
            return "Error: Python interpreter not found"
    else:
        exe = "python3"

    try:
        proc = await asyncio.create_subprocess_exec(
            exe, "-I", "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(_DEFAULT_WORKSPACE),
            env=_SAFE_ENV,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=_CODE_TIMEOUT,
        )
        output = (
            stdout.decode("utf-8", errors="replace")
            or stderr.decode("utf-8", errors="replace")
            or "(no output)"
        )
        return output[:COMMAND_MAX_OUTPUT_CHARS]
    except asyncio.TimeoutError:
        return f"Code execution timed out ({_CODE_TIMEOUT}s)"
    except FileNotFoundError:
        return "Error: Python interpreter not found"
    except Exception as e:
        return f"Code runner error: {e}"


async def _run_node(code: str) -> str:
    """Execute JavaScript code in node subprocess (non-blocking)."""
    if not shutil.which("node"):
        return "Error: Node.js not found. Install with: brew install node"

    try:
        proc = await asyncio.create_subprocess_exec(
            "node", "-e", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(_DEFAULT_WORKSPACE),
            env=_SAFE_ENV,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=_CODE_TIMEOUT,
        )
        output = (
            stdout.decode("utf-8", errors="replace")
            or stderr.decode("utf-8", errors="replace")
            or "(no output)"
        )
        return output[:COMMAND_MAX_OUTPUT_CHARS]
    except asyncio.TimeoutError:
        return f"Code execution timed out ({_CODE_TIMEOUT}s)"
    except FileNotFoundError:
        return "Error: Node.js not found"
    except Exception as e:
        return f"Code runner error: {e}"


plus_code_runner = Tool(
    ToolSpec(
        name="code_runner",
        description=(
            "Execute Python or JavaScript code in a sandboxed subprocess "
            f"(timeout {_CODE_TIMEOUT}s)"
        ),
        parameters={
            "language": {"type": "string",
                         "description": "'python' or 'javascript'"},
            "code": {"type": "string", "description": "Code to execute"},
        },
        risk=RiskLevel.HIGH,
        category="system",
    ),
    handler=_code_runner,
)

__all__ = ["plus_code_runner"]

