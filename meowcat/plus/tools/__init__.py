# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat plus builtin tools — pre-assembled tool set.

These are the concrete tool implementations every cat can use
out of the box.  Pure-framework abstractions live in ``meowcat.tools``.
"""

from __future__ import annotations

from meowcat.plus.tools.code_runner import plus_code_runner
from meowcat.plus.tools.command import plus_run_command
from meowcat.plus.tools.file_ops import plus_read_file, plus_write_file
from meowcat.plus.tools.fs_tools import plus_grep_files, plus_list_dir
from meowcat.plus.tools.http_client import plus_http_get
from meowcat.plus.tools.time_tool import plus_current_time
from meowcat.tools.tool import Tool

BUILTIN_TOOLS: list[Tool] = [
    plus_read_file,
    plus_write_file,
    plus_run_command,
    plus_http_get,
    plus_list_dir,
    plus_grep_files,
    plus_current_time,
    plus_code_runner,
]

__all__ = ["BUILTIN_TOOLS"]
