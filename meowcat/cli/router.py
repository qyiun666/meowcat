"""meowcat CommandRouter — command routing and registration framework (v1.1.10).

Pluggable design: ``"middleware"`` slot intercepts commands before execution.
Built-in i18n integration via ``CommandContext.i18n``.

Usage::

    router = CommandRouter(i18n=I18n())
    router.register(Command(name="/help", handler=cmd_help, group="General"))
    result = router.route(user_input="/help --verbose")
"""
# (c) 2025-2026 Axonant. MIT License.

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from meowcat.pluggable import Pluggable


@dataclass
class Command:
    """A registered command with metadata.

    ``handler`` receives a :class:`CommandContext` and returns a string result.
    """

    name: str
    handler: Callable[..., Any]
    group: str = "General"
    description: str = ""


@dataclass
class CommandContext:
    """Context passed to command handlers at execution time."""

    router: CommandRouter
    name: str
    args: str = ""
    raw_input: str = ""
    i18n: Any = None  # I18n instance, optional


class CommandRouter(Pluggable):
    """Command routing registry — register, unregister, route.

    Extension slot ``"middleware"``: intercept before command execution.
    Middleware receives ``(ctx: CommandContext)`` and returns ``str | None``.
    Return ``None`` to continue; return a ``str`` to short-circuit and use
    that as the response.

    Usage::

        router = CommandRouter(i18n=I18n())
        router.register(Command(name="/help", handler=help_handler))
        print(router.route("/help"))
    """

    HOOKS: dict[str, dict[str, str]] = {
        "middleware": {
            "in": "ctx: CommandContext",
            "out": "str | None",
        },
    }

    def __init__(self, i18n: Any = None) -> None:
        super().__init__()
        self._commands: dict[str, Command] = {}
        self.i18n = i18n

    # -- Registration ----------------------------------------------------

    def register(self, command: Command) -> None:
        """Register a command. Overwrites if name already exists."""
        self._commands[command.name] = command

    def unregister(self, name: str) -> None:
        """Remove a registered command by name."""
        self._commands.pop(name, None)

    def get_command(self, name: str) -> Command | None:
        """Look up a command by name (exact match)."""
        return self._commands.get(name)

    def list_commands(self) -> list[Command]:
        """Return all registered commands."""
        return list(self._commands.values())

    def list_groups(self) -> dict[str, list[Command]]:
        """Return commands grouped by their group label."""
        groups: dict[str, list[Command]] = {}
        for cmd in self._commands.values():
            groups.setdefault(cmd.group, []).append(cmd)
        return groups

    # -- Routing ---------------------------------------------------------

    def route(self, user_input: str) -> str:
        """Route a user input string to the matching command handler.

        Steps:
        1. Parse command name and args from input.
        2. Find matching command (exact name match).
        3. Run middleware chain; first non-None result short-circuits.
        4. If no middleware short-circuits, execute the handler.
        5. Return result string or i18n-translated error.
        """
        stripped = user_input.strip()
        if not stripped or not stripped.startswith("/"):
            return self._t("unknown_command", cmd=stripped or "(empty)")

        parts = stripped.split(maxsplit=1)
        name = parts[0]
        arg_str = parts[1] if len(parts) > 1 else ""

        cmd = self._commands.get(name)
        if cmd is None:
            return self._t("unknown_command", cmd=name)

        ctx = CommandContext(
            router=self,
            name=name,
            args=arg_str,
            raw_input=stripped,
            i18n=self.i18n,
        )

        # Run middleware chain
        for _hook, result in self._run_plugs_sync("middleware", ctx):
            if result is not None:
                return str(result)

        # Execute handler
        try:
            result = cmd.handler(ctx)
            return str(result)
        except Exception as exc:
            return self._t("command_error", error=str(exc))

    # -- Helpers ---------------------------------------------------------

    def _t(self, key: str, **kwargs: Any) -> str:
        """Translate via i18n if available, otherwise return the key."""
        if self.i18n is not None:
            return self.i18n.t(key, **kwargs)
        return key


__all__ = ["Command", "CommandContext", "CommandRouter"]
