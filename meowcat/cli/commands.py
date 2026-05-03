"""meowcat system commands — /version /wiring /inject /debug /help (v1.1.11).

All five builtin commands with i18n support. ``register_system_commands()``
registers them on a :class:`CommandRouter`; handlers that need a CatBase
instance use closures over the ``cat`` reference.
"""

from __future__ import annotations

from typing import Any

from meowcat.cli.router import Command, CommandContext, CommandRouter


# -- Module-level debug flag ---------------------------------------------------

_debug_mode: bool = False


def is_debug() -> bool:
    """Check if debug mode is active."""
    return _debug_mode


# -- Command handlers ----------------------------------------------------------

def cmd_help(ctx: CommandContext) -> str:
    """``/help`` — display all commands grouped by category."""
    t = ctx.i18n
    lines = [f"**{t.t('help_title')}**"]
    groups = ctx.router.list_groups()
    for group, cmds in sorted(groups.items()):
        lines.append(f"\n[{group}]")
        for cmd in cmds:
            desc = cmd.description or t.t("help_no_description")
            lines.append(f"  {cmd.name:<16} {desc}")
    lines.append(f"\n{t.t('help_usage')}: /<command> [args]")
    return "\n".join(lines)


def cmd_version(ctx: CommandContext) -> str:
    """``/version`` — display meowcat version."""
    import meowcat

    t = ctx.i18n
    return t.t("version_info", name="meowcat", version=meowcat.__version__)


def _make_cmd_wiring(cat: Any):
    """Closure factory — captures ``cat`` for ``/wiring``."""

    def handler(ctx: CommandContext) -> str:
        try:
            return cat.wiring_diagram(format="mermaid")
        except AttributeError:
            return ctx.i18n.t("wiring_no_data")

    return handler


def _make_cmd_inject(cat: Any):
    """Closure factory — captures ``cat`` for ``/inject``.
    
    Usage: ``/inject brain:hippocampus add_entity name=Python``
    """
    from meowcat.inject import Needle, NeedleDisabledError

    def handler(ctx: CommandContext) -> str:
        t = ctx.i18n
        try:
            needle = Needle(cat)
        except NeedleDisabledError:
            return t.t("inject_disabled")
        args = ctx.args.strip().split()
        if len(args) < 2:
            return f"{t.t('help_usage')}: /inject <organ> <method> [key=value ...]"
        organ_str = args[0]
        method = args[1]
        kwargs: dict[str, Any] = {}
        for kv in args[2:]:
            if "=" in kv:
                k, v = kv.split("=", 1)
                kwargs[k.strip()] = v.strip()
        category, name = organ_str.split(":") if ":" in organ_str else ("brain", organ_str)
        try:
            result = needle.poke((category, name), method, **kwargs)
            # poke returns sync; unwrap if coroutine
            import inspect
            if inspect.isawaitable(result):
                import asyncio
                result = asyncio.get_event_loop().run_until_complete(result)
            return f"{t.t('inject_result')}: {result}"
        except Exception as exc:
            return t.t("command_error", error=str(exc))

    return handler


def cmd_debug(ctx: CommandContext) -> str:
    """``/debug`` — toggle debug mode on/off."""
    global _debug_mode
    _debug_mode = not _debug_mode
    t = ctx.i18n
    return t.t("debug_on") if _debug_mode else t.t("debug_off")


# -- Registration --------------------------------------------------------------

def register_system_commands(router: CommandRouter, cat: Any | None = None) -> None:
    """Register all five system commands on the router.

    Args:
        router: :class:`CommandRouter` to register on.
        cat: Optional :class:`CatBase` instance for commands that need it
             (``/wiring``, ``/inject``). When ``None``, those commands
             return an error message.
    """
    router.register(Command(
        name="/help", handler=cmd_help, group="System",
        description="Show help",
    ))
    router.register(Command(
        name="/version", handler=cmd_version, group="System",
        description="Show version",
    ))
    router.register(Command(
        name="/debug", handler=cmd_debug, group="System",
        description="Toggle debug mode",
    ))

    if cat is not None:
        router.register(Command(
            name="/wiring", handler=_make_cmd_wiring(cat), group="System",
            description="Show wiring topology",
        ))
        router.register(Command(
            name="/inject", handler=_make_cmd_inject(cat), group="System",
            description="Needle injection debug",
        ))
    else:
        router.register(Command(
            name="/wiring", handler=lambda _: "No cat attached",
            group="System", description="Show wiring topology",
        ))
        router.register(Command(
            name="/inject", handler=lambda _: "No cat attached",
            group="System", description="Needle injection debug",
        ))


__all__ = ["cmd_help", "cmd_version", "cmd_debug",
           "register_system_commands", "is_debug"]
