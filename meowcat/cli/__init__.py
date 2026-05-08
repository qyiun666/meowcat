# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat CLI subsystem — i18n, command router, system commands, TUI app (v1.1.9+).

All CLI-related components (i18n, CommandRouter, system commands, TUI, theme, etc.)
are placed under this package as they get lowered from meowagent.

v1.1.9:  I18n multi-language engine with builtin en/zh locales.
v1.1.10: CommandRouter command routing and registration framework.
v1.1.11: System commands — /version /wiring /inject /debug /help.
v1.1.12: Colony commands — /cats /adopt /release /switch + /health /brain.
v1.1.13: MeowTui — Textual TUI bare-bones App skeleton.
"""

from meowcat.cli.commands import (
    is_debug,
    register_colony_commands,
    register_system_commands,
)
from meowcat.cli.i18n import I18n
from meowcat.cli.router import Command, CommandContext, CommandRouter
from meowcat.cli.theme import Theme

try:
    from meowcat.cli.app import MeowTui  # requires textual
except ImportError:
    MeowTui = None

__all__ = [
    "I18n",
    "Command",
    "CommandContext",
    "CommandRouter",
    "register_system_commands",
    "register_colony_commands",
    "is_debug",
    "MeowTui",
    "Theme",
]
