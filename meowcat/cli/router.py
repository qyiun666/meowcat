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

import asyncio
import shlex
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
    min_args: int = 0
    max_args: int | None = None


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

    async def route(self, user_input: str) -> str:
        """Route a user input string to the matching command handler.

        Async — both sync and async handlers are supported.

        Steps:
        1. Parse command name and args from input.
        2. Find matching command (exact name match).
        3. Run middleware chain (async); first non-None result short-circuits.
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

        # Middleware chain — async
        async for _hook, result in self._run_plugs("middleware", ctx):
            if result is not None:
                return str(result)

        try:
            result = cmd.handler(ctx)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)
        except Exception as exc:
            return self._t("command_error", error=str(exc))

    def command(
        self, name: str | None = None, group: str = "General",
        description: str = "", min_args: int = 0, max_args: int | None = None,
    ) -> Callable:
        """Decorator: register a command handler in one line.

        Usage::

            @router.command(name="/stats", group="System", description="Show stats")
            def cmd_stats(ctx: CommandContext) -> str:
                return "Stats: ..."

            @router.command()  # auto-derives name from handler: /foo for cmd_foo
            async def cmd_foo(ctx: CommandContext) -> str:
                return await do_something()
        """
        def decorator(handler):
            cmd_name = name or f"/{handler.__name__.removeprefix('cmd_')}"
            self.register(Command(
                name=cmd_name, handler=handler, group=group,
                description=description, min_args=min_args, max_args=max_args,
            ))
            return handler
        return decorator

    async def parse_and_route(self, raw: str) -> str:
        """``shlex`` parse → arg validation → route.

        Supports quoted arguments like ``/adopt "my cat"``.
        Returns translated error if arg count is out of bounds.
        """
        try:
            parts = shlex.split(raw)
        except ValueError:
            parts = raw.split()
        if not parts:
            return await self.route(raw)
        name, args = parts[0], parts[1:]
        cmd = self._commands.get(name)
        if cmd is not None:
            if len(args) < cmd.min_args:
                return self._t("too_few_args", cmd=name, expected=cmd.min_args)
            if cmd.max_args is not None and len(args) > cmd.max_args:
                return self._t("too_many_args", cmd=name, expected=cmd.max_args)
        return await self.route(raw)

    def _t(self, key: str, **kwargs: Any) -> str:
        """Translate via i18n if available, otherwise return the key."""
        if self.i18n is not None:
            return self.i18n.t(key, **kwargs)
        return key


__all__ = ["Command", "CommandContext", "CommandRouter"]
