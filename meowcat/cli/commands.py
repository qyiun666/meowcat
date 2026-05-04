"""meowcat system commands — /version /wiring /inject /debug /help (v1.1.11).

All five builtin commands with i18n support. ``register_system_commands()``
registers them on a :class:`CommandRouter`; handlers that need a CatBase
instance use closures over the ``cat`` reference.

v1.1.12: Colony commands — /cats /adopt /release /switch + /health /brain.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from meowcat.cli.router import Command, CommandContext, CommandRouter

_log = logging.getLogger(__name__)


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
        category, name = organ_str.split(
            ":") if ":" in organ_str else ("brain", organ_str)
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


# -- Colony commands (v1.1.12) ------------------------------------------------

def register_colony_commands(
    router: CommandRouter,
    colony: Any,
    active_cat_ref: list[Any],
) -> None:
    """Register colony management and diagnose commands on the router.

    Args:
        router: :class:`CommandRouter` to register on.
        colony: :class:`Colony` instance for cat management.
        active_cat_ref: Mutable list ``[cat_or_none]`` for tracking active cat.
            The list is mutated in-place by ``/switch``.
    """

    # -- /cats -----------------------------------------------------------

    def cmd_cats(ctx: CommandContext) -> str:
        t = ctx.i18n
        cat_ids = colony.list_cats()
        if not cat_ids:
            return t.t("cats_no_cats")
        max_cats = colony.max_cats if colony.max_cats is not None else t.t(
            "colony_unlimited")
        lines = [
            f"**{t.t('colony_info', name=colony.name, colony_id=colony.colony_id, count=len(cat_ids), max_cats=max_cats)}**",
            "",
        ]
        active_id = active_cat_ref[0].cat_id if active_cat_ref[0] else None
        for cid in cat_ids:
            marker = " ← active" if cid == active_id else ""
            try:
                cat = colony.get_cat(cid)
                organs = len(cat.list_all_organs())
                lines.append(f"  {cid} ({organs} organs){marker}")
            except Exception:
                _log.debug("Failed to list organs for cat '%s'",
                           cid, exc_info=True)
                lines.append(f"  {cid}{marker}")
        return "\n".join(lines)

    # -- /adopt ----------------------------------------------------------

    def cmd_adopt(ctx: CommandContext) -> str:
        t = ctx.i18n
        cat_id = ctx.args.strip()
        if not cat_id:
            return t.t("cats_adopt_usage")
        if cat_id in colony._cats:
            return t.t("cats_adopt_exists", cat_id=cat_id)
        if colony.is_full:
            return t.t("cats_adopt_full", count=len(colony._cats), max_cats=colony.max_cats)
        try:
            cat = colony.create_cat(cat_id)
            if active_cat_ref[0] is None:
                active_cat_ref[0] = cat
            return t.t("cats_adopt", cat_id=cat_id)
        except Exception as exc:
            return t.t("command_error", error=str(exc))

    # -- /release --------------------------------------------------------

    def cmd_release(ctx: CommandContext) -> str:
        t = ctx.i18n
        cat_id = ctx.args.strip()
        if not cat_id:
            return t.t("cats_release_usage")
        if cat_id not in colony._cats:
            return t.t("cats_release_not_found", cat_id=cat_id)
        try:
            colony.release(cat_id)
            if active_cat_ref[0] and active_cat_ref[0].cat_id == cat_id:
                active_cat_ref[0] = None
            return t.t("cats_release", cat_id=cat_id)
        except Exception as exc:
            return t.t("command_error", error=str(exc))

    # -- /switch ---------------------------------------------------------

    def cmd_switch(ctx: CommandContext) -> str:
        t = ctx.i18n
        cat_id = ctx.args.strip()
        if not cat_id:
            return t.t("cats_switch_usage")
        if cat_id not in colony._cats:
            return t.t("cats_not_found", cat_id=cat_id)
        active_cat_ref[0] = colony.get_cat(cat_id)
        return t.t("cats_switch", cat_id=cat_id)

    # -- /health (async) -------------------------------------------------

    def cmd_health(ctx: CommandContext) -> str:
        t = ctx.i18n
        if not colony._cats:
            return t.t("health_no_cats")
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return t.t("health_running") + "\n" + _health_sync(t, colony)
            results = loop.run_until_complete(colony.health_check_all())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            results = loop.run_until_complete(colony.health_check_all())
            loop.close()
        return _format_health_results(t, results)

    # -- /brain [cat_id] (async) ----------------------------------------

    def cmd_brain(ctx: CommandContext) -> str:
        t = ctx.i18n
        cat_id = ctx.args.strip()
        if cat_id:
            if cat_id not in colony._cats:
                return t.t("brain_cat_not_found", cat_id=cat_id)
            cat = colony.get_cat(cat_id)
        elif active_cat_ref[0]:
            cat = active_cat_ref[0]
        else:
            return t.t("brain_no_cat")
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return t.t("brain_running", cat_id=cat.cat_id)
            results = loop.run_until_complete(cat.brain_check())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            results = loop.run_until_complete(cat.brain_check())
            loop.close()
        return _format_brain_results(t, cat.cat_id, results)

    # -- Register --------------------------------------------------------

    router.register(Command(
        name="/cats", handler=cmd_cats, group="Colony",
        description="List all cats",
    ))
    router.register(Command(
        name="/adopt", handler=cmd_adopt, group="Colony",
        description="Adopt a new cat",
    ))
    router.register(Command(
        name="/release", handler=cmd_release, group="Colony",
        description="Release a cat",
    ))
    router.register(Command(
        name="/switch", handler=cmd_switch, group="Colony",
        description="Switch active cat",
    ))
    router.register(Command(
        name="/health", handler=cmd_health, group="Diagnose",
        description="Health check all cats",
    ))
    router.register(Command(
        name="/brain", handler=cmd_brain, group="Diagnose",
        description="Brain check a cat",
    ))


# -- Health / Brain formatters ------------------------------------------------

def _health_sync(t: Any, colony: Any) -> str:
    """Sync fallback: return basic cat info when async loop is running."""
    lines = []
    for cid in colony.list_cats():
        try:
            cat = colony.get_cat(cid)
            organs = cat.list_all_organs()
            lines.append(t.t("health_cat_status", cat_id=cid,
                         status=len(organs), errors=0))
        except Exception as exc:
            lines.append(
                t.t("health_cat_status", cat_id=cid, status=0, errors=1))
    return "\n".join(lines) if lines else t.t("health_no_cats")


def _format_health_results(t: Any, results: dict) -> str:
    """Format health check results dict into readable text."""
    lines = [f"**{t.t('health_title')}**", ""]
    total_organs = 0
    total_errors = 0
    for cat_id, organs in results.items():
        if isinstance(organs, dict):
            errs = sum(1 for v in organs.values()
                       if isinstance(v, dict) and "error" in v)
            total_organs += len(organs)
            total_errors += errs
            lines.append(t.t("health_cat_status", cat_id=cat_id,
                         status=len(organs), errors=errs))
        else:
            total_errors += 1
            lines.append(
                t.t("health_cat_status", cat_id=cat_id, status=0, errors=1))
    lines.append("")
    if total_errors == 0:
        lines.append(t.t("health_all_ok"))
    else:
        lines.append(t.t("health_issues"))
    return "\n".join(lines)


def _format_brain_results(t: Any, cat_id: str, results: dict) -> str:
    """Format brain check results dict into readable text."""
    lines = [f"**{t.t('brain_title')}: {cat_id}**", ""]
    err_count = 0
    for organ_name, data in sorted(results.items()):
        if isinstance(data, dict) and "error" in data:
            lines.append(f"  {organ_name}: ⚠ {data['error']}")
            err_count += 1
        else:
            summary = json.dumps(data, default=str) if data else "OK"
            lines.append(f"  {organ_name}: {summary}")
    lines.append("")
    lines.append(t.t("health_all_ok") if err_count ==
                 0 else t.t("health_issues"))
    return "\n".join(lines)


__all__ = ["cmd_help", "cmd_version", "cmd_debug",
           "register_system_commands", "is_debug",
           "register_colony_commands"]
