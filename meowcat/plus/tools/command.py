# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat plus command execution tool — run_command.

Concrete I/O implementation that executes shell commands via subprocess.
Import from ``meowcat.plus.tools`` or ``meowcat.plus``.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from meowcat.constants import COMMAND_DEFAULT_TIMEOUT, COMMAND_MAX_OUTPUT_CHARS
from meowcat.tools.tool import RiskLevel, Tool, ToolSpec

_DEFAULT_WORKSPACE = Path.home() / ".meowcat" / "workspace"

# Safe environment variables to pass to subprocess (whitelist)
_SAFE_ENV_KEYS: frozenset[str] = frozenset({
    "PATH", "HOME", "USER", "LOGNAME",
    "LANG", "LC_ALL", "LC_CTYPE",
    "TMPDIR", "TEMP", "TMP",
    "SHELL", "TERM",
    "VIRTUAL_ENV", "CONDA_PREFIX",  # Python env
})


def _build_safe_env() -> dict[str, str]:
    """Build a sanitised environment dict, filtering to whitelist only."""
    env: dict[str, str] = {}
    for key in _SAFE_ENV_KEYS:
        value = os.environ.get(key)
        if value is not None:
            env[key] = value
    # Always ensure PATH is present
    if "PATH" not in env:
        env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
    return env


async def _run_command(command: str, **_: Any) -> str:
    """Execute shell command."""
    if not command.strip():
        return "Error: empty command"
    try:
        import shlex
        args = shlex.split(command)
        result = subprocess.run(
            args, capture_output=True, text=True,
            timeout=COMMAND_DEFAULT_TIMEOUT, cwd=str(_DEFAULT_WORKSPACE),
            env=_build_safe_env(),
        )
        output = result.stdout or result.stderr or "(no output)"
        return output[:COMMAND_MAX_OUTPUT_CHARS]
    except subprocess.TimeoutExpired:
        return f"Command timed out ({COMMAND_DEFAULT_TIMEOUT}s)"
    except FileNotFoundError:
        return f"Command not found: {command.split()[0]}"
    except Exception as e:
        return f"Command error: {e}"


plus_run_command = Tool(
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

