"""meowcat CLI subsystem — i18n, command router, system commands, TUI app (v1.1.9+).

All CLI-related components (i18n, CommandRouter, system commands, TUI, theme, etc.)
are placed under this package as they get lowered from meowagent.

v1.1.9:  I18n multi-language engine with builtin en/zh locales.
v1.1.10: CommandRouter command routing and registration framework.
v1.1.11: System commands — /version /wiring /inject /debug /help.
"""
# (c) 2025-2026 Axonant. MIT License.

from meowcat.cli.commands import (
    register_system_commands,
    is_debug,
)
from meowcat.cli.i18n import I18n
from meowcat.cli.router import Command, CommandContext, CommandRouter

__all__ = ["I18n", "Command", "CommandContext", "CommandRouter",
           "register_system_commands", "is_debug"]
