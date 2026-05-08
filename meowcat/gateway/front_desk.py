# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat Gateway FrontDesk — built-in receptionist (Protocol + Pluggable).

FrontDesk is the sole entry point for all external messages into a Colony.
Every message passes through ``route()`` — the default implementation forwards
to ``target_cat`` when specified, or returns a placeholder reply.

Application layer can:
- Subclass ``DefaultFrontDesk`` to override ``route()`` (security gates, custom routing)
- Use ``plug("on_route", my_hook)`` to inject hooks (audit logging, rate limiting)

Hooks run in registration order via first-hit semantics: the first plugin that
returns a non-None result short-circuits the chain.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from meowcat.pluggable import Pluggable

if TYPE_CHECKING:
    from meowcat.gateway.protocol import SignalContext


class DefaultFrontDesk(Pluggable):
    """Default FrontDesk — routes to target cat or returns placeholder.

    **Hooks**::

        HOOKS = {
            "on_route": {"in": "text: str, ctx: SignalContext, colony: Colony",
                         "out": "str | None"},
        }

    Plugins on ``"on_route"`` run in registration order.  First non-None
    return value short-circuits and becomes the reply.  If no plugin
    returns a value, the default ``route()`` logic runs.

    Usage::

        fd = DefaultFrontDesk()

        # Hook: audit log
        fd.plug("on_route", lambda text, ctx, colony: print(f"[audit] {ctx.user_id}: {text[:50]}"))

        # Hook: security gate (first-hit — blocks dangerous content)
        def security_gate(text, ctx, colony):
            if "DROP TABLE" in text.upper():
                return "⚠️ 危险操作已拦截"
            return None  # pass through
        fd.plug("on_route", security_gate)

        # Override: custom routing
        class MyFrontDesk(DefaultFrontDesk):
            async def route(self, text, ctx, colony):
                if ctx.platform == "feishu":
                    return await self._feishu_dispatch(text, ctx, colony)
                return await super().route(text, ctx, colony)

        gw = Gateway(colony, front_desk=MyFrontDesk())
    """

    HOOKS: dict[str, dict[str, str]] = {
        "on_route": {
            "in": "text: str, ctx: SignalContext, colony: Colony",
            "out": "str | None",
        },
    }

    async def route(
        self,
        text: str,
        ctx: "SignalContext",
        colony: Any,
    ) -> str | None:
        """Route external message → target cat or placeholder.

        1. Run ``on_route`` plugins (first-hit: first non-None reply wins).
        2. If ``ctx.target_cat`` is set → forward to that cat via ``perceive()``.
        3. Otherwise → return placeholder.

        Args:
            text: Incoming message text.
            ctx: Signal context with optional ``target_cat``.
            colony: Colony instance containing all cats.

        Returns:
            Reply string, or None for no reply.
        """
        # 1. Plugins — first-hit
        async for _name, result in self._run_plugs(
            "on_route", text, ctx, colony,
        ):
            if result is not None:
                return result  # type: ignore[no-any-return]

        # 2. Target cat specified → forward
        if ctx.target_cat:
            try:
                cat = colony.get_cat(ctx.target_cat)
                async for event in cat.perceive(text, context=ctx):
                    if event.kind == "output":
                        return event.content
                    if event.kind == "short_circuit" and event.reply:
                        return event.reply
                return None
            except KeyError:
                return f"喵？找不到猫『{ctx.target_cat}』..."

        # 3. No target → placeholder
        return "喵？我不知道你要找谁..."


__all__ = ["DefaultFrontDesk"]
