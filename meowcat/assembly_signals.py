# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat CatBase signal system mixin — nervous system, reflex, perception.

Extracted from ``assembly.py`` (v1.3.9) to keep each file ≤500 lines.
Provides ``SignalSystemMixin`` with all signal/reflex/perception methods.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from meowcat.reflex import Reflex
from meowcat.wiring import Organ


class SignalSystemMixin:
    """Mixin providing nervous system, reflex, and perception methods for CatBase.

    All methods access ``self._*`` private attributes set by ``CatBase.__init__``.
    This mixin has no ``__init__`` — CatBase is responsible for initialising
    the attributes these methods depend on.
    """

    # -- Neural synapse facade -----------------------------------------------

    def use_middleware(self, mw: Any) -> None:
        """Register a signal middleware. Executed in registration order.

        Args:
            mw: Middleware instance implementing
                :class:`~meowcat.nervous.SignalMiddleware` Protocol

        Raises:
            RuntimeError: Subsystem not enabled when ``enable_wiring=False``.
        """
        if self._nervous is None:
            raise RuntimeError(
                "middleware unavailable — cat was constructed with enable_wiring=False",
            )
        self._nervous.use_middleware(mw)

    # -- Default registration methods (v1.2.10) ----------------------------

    def register_default_paths(self) -> None:
        """Register BUILTIN_PATHS into path_registry.

        Safe to call multiple times — duplicates overwrite in registration
        order. Use when ``register_default_paths=False`` was passed to
        ``__init__`` but paths are needed later.
        """
        from meowcat.path import register_builtin_paths

        register_builtin_paths(self.path_registry)

    def register_default_chains(self) -> None:
        """Register BUILTIN_CHAINS into chain_registry.

        Safe to call multiple times. Use when ``register_default_chains=False``
        was passed to ``__init__`` but chains are needed later.
        """
        from meowcat.chain import register_builtin_chains

        register_builtin_chains(self.chain_registry)

    def register_default_loops(self) -> None:
        """Register BUILTIN_LOOPS into loop_registry (and associated Chains).

        Safe to call multiple times. Use when ``register_default_loops=False``
        was passed to ``__init__`` but loops are needed later.
        """
        from meowcat.loops import register_default_loops

        register_default_loops(self.loop_registry, self.chain_registry)

    def register_default_tools(self) -> None:
        """Stub — builtin tools moved to application layer (v2.0).

        Safe to call multiple times; no-op when no tools are registered.
        Use ``cat.tool_registry.register(tool)`` at the application layer.
        """
        pass

    # -- Telemetry / CircuitBreaker facade (v1.3.6) -----------------------

    def enable_telemetry(self) -> None:
        """Enable observability tracing at runtime. Delegates to :class:`Nervous`.

        Raises:
            RuntimeError: Subsystem not enabled when ``enable_wiring=False``.
        """
        if self._nervous is None:
            raise RuntimeError(
                "telemetry unavailable — cat was constructed with enable_wiring=False",
            )
        self._nervous.enable_telemetry()

    def disable_telemetry(self) -> None:
        """Disable observability tracing at runtime. Delegates to :class:`Nervous`.

        Raises:
            RuntimeError: Subsystem not enabled when ``enable_wiring=False``.
        """
        if self._nervous is None:
            raise RuntimeError(
                "telemetry unavailable — cat was constructed with enable_wiring=False",
            )
        self._nervous.disable_telemetry()

    def enable_circuit_breaker(self) -> None:
        """Enable signal-level circuit breaker at runtime. Delegates to :class:`Nervous`.

        Raises:
            RuntimeError: Subsystem not enabled when ``enable_wiring=False``.
        """
        if self._nervous is None:
            raise RuntimeError(
                "circuit breaker unavailable — cat was constructed with enable_wiring=False",
            )
        self._nervous.enable_circuit_breaker()

    def disable_circuit_breaker(self) -> None:
        """Disable signal-level circuit breaker at runtime. Delegates to :class:`Nervous`.

        Raises:
            RuntimeError: Subsystem not enabled when ``enable_wiring=False``.
        """
        if self._nervous is None:
            raise RuntimeError(
                "circuit breaker unavailable — cat was constructed with enable_wiring=False",
            )
        self._nervous.disable_circuit_breaker()

    async def signal(
        self,
        from_organ: Organ,
        to_organ: Organ,
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Inter-organ signal (forwards to :class:`Nervous`).

        Raises:
            RuntimeError: Subsystem not enabled when ``enable_wiring=False``.
        """
        if self._nervous is None:
            raise RuntimeError(
                "signal unavailable — cat was constructed with enable_wiring=False",
            )
        return await self._nervous.signal(
            from_organ,
            to_organ,
            method,
            *args,
            **kwargs,
        )

    async def probe(self, to_organ: Organ) -> dict[str, Any]:
        """Read-only diagnostic (forwards to :class:`Nervous`)."""
        if self._nervous is None:
            raise RuntimeError(
                "probe unavailable — cat was constructed with enable_wiring=False",
            )
        # type: ignore[no-any-return]
        return await self._nervous.probe(to_organ)

    # -- Nervous system assembly ---------------------------------------------

    def wire_default_nervous_system(self) -> None:
        """Assemble default neural wiring table. No-op when
        ``enable_wiring=False``."""
        if self._nervous is None:
            return
        self._nervous.wire_default()

    def register_reflex(self, reflex: Reflex) -> None:
        """Register a reflex."""
        if self._reflex is None:
            raise RuntimeError(
                "register_reflex unavailable — enable_reflex=False",
            )
        self._reflex.register(reflex)

    def freeze_nervous_system(self) -> None:
        """Freeze nervous system: first validate reflex.path legality,
        then freeze wiring.

        Order matters: reflex.validate_paths needs to read ``nervous.wiring``.
        Once wiring is frozen it remains readable, so the order is theoretically
        interchangeable, but we use the conservative "validate first, freeze
        later" order for safety in case freeze later evolves to clean up wiring
        transient state.
        """
        if self._reflex is not None:
            self._reflex.validate_paths()
        if self._nervous is not None:
            self._nervous.freeze()

    # -- Perception entry ----------------------------------------------------

    async def perceive(
        self,
        input: Any,
        **extras: Any,
    ) -> AsyncIterator[Any]:
        """The cat's sole external reflex entry (forwards to
        :class:`ReflexArc`).

        Raises:
            RuntimeError: Subsystem not enabled when ``enable_reflex=False``.
            NoReflexMatchedError: No reflex matched ``input``.
        """
        if self._reflex is None:
            raise RuntimeError(
                "perceive unavailable — enable_reflex=False",
            )
        async for ev in self._reflex.perceive(input, cat=self, **extras):
            yield ev

    # -- Assembly tools ------------------------------------------------------

    def _assemble(
        self,
        *,
        reflex_stages: list[Any] | None = None,
        reflexes: list[Reflex] | None = None,
    ) -> None:
        """Auto-scan organ attributes on ``self`` and complete skeleton
        assembly.

        v0.5.9: The actual logic lives in the top-level function
        :func:`assemble_default_cat`; this method is a thin wrapper for
        backward compatibility. Subclasses (e.g. meowagent.Cat) just need
        to keep calling ``self._assemble(reflex_stages=[...])`` at the end
        of ``__init__`` — behavior unchanged.

        v0.5.20: Added ``reflexes`` param, forwarded to
        ``assemble_default_cat()``.

        v0.5.21: ``assemble_default_cat()`` no longer freezes;
        this method is responsible for that.

        Args:
            reflex_stages: Stage list for the default text_dialogue reflex.
                ``None`` means empty list.
            reflexes: Reflex list; ``None`` means register no reflexes.
        """
        from meowcat.assemblers import assemble_default_cat

        assemble_default_cat(
            self,  # type: ignore[arg-type]
            reflex_stages=reflex_stages, reflexes=reflexes)
        self.freeze_nervous_system()
