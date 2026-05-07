# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat assembly skeleton — Cat base class (v0.5.9 facade pattern).

meowcat defines the cat skeleton and lifecycle; meowagent subclasses choose
what materials the organs are made of.

**v0.5.9 Subsystem decoupling**: CatBase is no longer a 440-line monolith,
but a composer of :class:`OrganHost` + :class:`Nervous` + :class:`ReflexArc`
+ :class:`EventBus`, maintaining 100% backward compatibility with the v0.5.0
external API through facade methods.

Five subsystems (each independently instantiable, each can fly solo):

+----------------+-------------------------------------+--------------------+
| Subsystem      | Responsibility                      | Solo-capable       |
+================+=====================================+====================+
| OrganHost      | Organ container (mount/organ)       | Yes                |
+----------------+-------------------------------------+--------------------+
| Wiring         | Connectivity graph (pure data)      | Yes                |
+----------------+-------------------------------------+--------------------+
| Nervous        | signal + probe dispatch             | Yes (needs host +  |
|                |                                     | events)            |
+----------------+-------------------------------------+--------------------+
| ReflexArc      | perceive reflex entry point         | Yes (needs events) |
+----------------+-------------------------------------+--------------------+
| EventBus       | Event bus                           | Yes (zero deps)    |
+----------------+-------------------------------------+--------------------+

CatBase does only four things:

1. **Compose five subsystems** (``_host`` / ``_events`` / ``_nervous`` / ``_reflex``)
2. **Facade forwarding**: external calls ``cat.mount/signal/perceive`` auto-route
   to the corresponding subsystem
3. **Lifecycle** (``start`` / ``shutdown``)
4. **Coordinate freeze**: first reflex validates paths, then wiring freezes

No: specific organ instantiation, config loading, I/O — these are meowagent's job.

**Disabled cats are first-class citizens**: ``CatBase("x", enable_wiring=False)``
can run, ``enable_reflex=False`` can also run; corresponding signal/perceive
will raise RuntimeError clearly indicating the subsystem is disabled.
"""


from __future__ import annotations

import logging as _logging
from collections.abc import Callable
from typing import Any, AsyncIterator

from meowcat.assembly_lifecycle import CatHook, LifecycleMixin
from meowcat.assembly_diag import DiagnosticMixin
from meowcat.errors import IllegalNeuralPathError, StandaloneCatError
from meowcat.events import EventBus, Handler
from meowcat.host import OrganHost
from meowcat.nervous import Nervous
from meowcat.reflex import Reflex, ReflexArc
from meowcat.tools.skill import SkillRegistry
from meowcat.tools.tool import ToolRegistry
from meowcat.wiring import Organ, Wiring

_log = _logging.getLogger(__name__)


class CatBase(LifecycleMixin, DiagnosticMixin):
    """Cat assembly base class (v0.5.9 composer, v1.0.1 unified kitten model).

    v1.0.1: Added ``parent_id`` / ``allowed_organs`` / ``forbidden_methods``,
    replacing the original KittenBase class. A kitten = a CatBase with
    ``parent_id`` and organ/method permissions restricted.
    """

    def __init__(
        self,
        cat_uid: str,
        *,
        container: "Colony | None" = None,
        parent_id: str | None = None,
        allowed_organs: frozenset[str] | None = None,
        forbidden_methods: frozenset[str] = frozenset(),
        enable_wiring: bool = True,
        enable_reflex: bool = True,
        register_default_paths: bool = True,
        register_default_chains: bool = True,
        register_default_loops: bool = True,
        register_default_tools: bool = True,
    ) -> None:
        """Construct cat skeleton.

        Args:
            cat_uid: Unique cat identifier (2-digit increment per colony).
            container: The Colony this cat belongs to (mandatory since v1.1.3).
            parent_id: Parent cat identifier (plain string, no object reference).
                Used for tracking and result routing back to parent.
            allowed_organs: Set of allowed organ attribute names.
                ``None`` = all allowed (default). When set,
                ``__getattribute__`` blocks access to forbidden organs.
            forbidden_methods: Method-level deny list.
                ``signal(..., method=X)`` raises
                :class:`IllegalNeuralPathError` when ``X in forbidden_methods``.
                Kittens use this to disable ``spawn_kitten`` / ``absorb_merge``
                and other main-cat-only methods.
            enable_wiring: When False, Nervous subsystem is not created;
                ``signal/probe`` calls raise RuntimeError. Suitable for
                "bare container" scenarios.
            enable_reflex: When False, ReflexArc subsystem is not created;
                ``perceive/register_reflex`` calls raise RuntimeError.
                Suitable for "signal-only, no-reflex" scenarios.
            register_default_paths: When False, BUILTIN_PATHS are not
                auto-registered. Call ``register_default_paths()`` later.
            register_default_chains: When False, BUILTIN_CHAINS are not
                auto-registered. Call ``register_default_chains()`` later.
            register_default_loops: When False, BUILTIN_LOOPS are not
                auto-registered. Call ``register_default_loops()`` later.
            register_default_tools: When False, BUILTIN_TOOLS are not
                auto-registered by ``assemble_default_cat()``.
                Call ``register_default_tools()`` later.
        """
        if container is None:
            raise StandaloneCatError(cat_uid)
        assert container is not None  # type guard: container is Colony after raise
        self._container = container
        self._cat_uid = cat_uid
        self._name = cat_uid  # default display name = uid
        self._address = f"{container.colony_id}_{cat_uid}"
        self._parent_id = parent_id
        self._allowed_organs: frozenset[str] | None = None
        self._host = OrganHost(cat_uid)
        self._events = EventBus()
        self._nervous: Nervous | None = (
            Nervous(self._host, self._events,
                    forbidden_methods=forbidden_methods)
            if enable_wiring else None
        )
        self._reflex: ReflexArc | None = (
            ReflexArc(self._events, self._nervous) if enable_reflex else None
        )
        # v0.5.23: Tool/Skill registries — every cat has claws
        self.tool_registry = ToolRegistry()
        self.skill_registry = SkillRegistry()
        # v0.5.27: Path registry — atomic path table
        from meowcat.path import PathRegistry, register_builtin_paths  # noqa: PLC0415
        self.path_registry = PathRegistry()
        if register_default_paths:
            register_builtin_paths(self.path_registry)
        # v0.5.28a: Chain registry — Path sequence composer
        from meowcat.chain import ChainRegistry, register_builtin_chains  # noqa: PLC0415
        self.chain_registry = ChainRegistry()
        if register_default_chains:
            register_builtin_chains(self.chain_registry)
        # v0.5.28b: Loop registry — Chain + trigger/exit events
        from meowcat.loops import LoopRegistry, register_default_loops as _register_default_loops  # noqa: PLC0415
        self.loop_registry = LoopRegistry()
        if register_default_loops:
            _register_default_loops(self.loop_registry, self.chain_registry)
        # v1.0.4: LoopSequence registry — Loop sequence composer
        from meowcat.loops import LoopSequenceRegistry  # noqa: PLC0415
        self.loopseq_registry = LoopSequenceRegistry()
        # v1.0.14: Lifecycle hooks
        self._start_hooks: list[CatHook] = []
        self._shutdown_hooks: list[CatHook] = []
        # v1.2.36: Organs mounted hooks — fired after mount_known_organs()
        self._organs_mounted_hooks: list[CatHook] = []
        # v1.0.15: Long-running workflow tracking
        self._active_workflows: dict[str, dict[str, Any]] = {}
        # v1.2.0: Unified self — all organ read/write converge here
        self._cat_self: Any = None
        # v1.2.5: Current self snapshot — set by DefaultLoops before each action
        self._current_snapshot: Any = None
        # v1.2.10: BUILTIN_* optional registration flags
        self._register_default_tools = register_default_tools
        # v1.0.1: allowed_organs must be assigned after all properties are set,
        # to avoid __init__ internal self.xxx assignments being intercepted
        # by __getattribute__
        self._allowed_organs = allowed_organs

    # -- Read-only facade properties -----------------------------------------

    @property
    def container(self) -> "Colony":
        """The Colony container this cat belongs to (mandatory since v1.1.3)."""
        return self._container

    @property
    def cat_address(self) -> str:
        """Colony-local address: ``{colony_uid}_{cat_uid}``.

        Example: ``0efb30telx53_01`` (15 chars).
        """
        return self._address

    @property
    def global_address(self) -> str:
        """Global address: ``{region}_{colony_uid}_{cat_uid}``.

        Reserved for future cross-region routing.  The *region* part
        comes from :attr:`Colony.region` and is empty when unset.

        Format:
            No region: ``{colony_uid}_{cat_uid}`` (same as :attr:`cat_address`)
            With region: ``{region}_{colony_uid}_{cat_uid}``

        Example (with region): ``us-east_0efb30telx53_01`` (22 chars).
        """
        region = self._container.region
        prefix = f"{region}_" if region else ""
        return f"{prefix}{self._address}"

    @property
    def cat_uid(self) -> str:
        """Cat unique identifier within the colony: 2-digit increment."""
        return self._cat_uid

    @property
    def parent_id(self) -> str | None:
        """Parent cat identifier (plain string, no object reference)."""
        return self._parent_id

    @property
    def name(self) -> str:
        """Human-readable display name (defaults to :attr:`cat_uid`).

        Mutable — users can rename cats at runtime.
        """
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def host(self) -> OrganHost:
        """Organ container (public accessor for diagnostic/injection tools).

        .. versionadded:: 1.2.12
            Previously only ``_host`` (private) was available.  This property
            gives :class:`Stethoscope` and :class:`Needle` a public access path.
        """
        return self._host

    @property
    def wiring(self) -> Wiring:
        """Neural connectivity graph (raises :class:`AttributeError` when
        Nervous is disabled)."""
        if self._nervous is None:
            raise AttributeError(
                "wiring disabled — construct with enable_wiring=True",
            )
        return self._nervous.wiring
# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

    @property
    def reflexes(self) -> "ReflexRegistry":
        """Reflex registry (raises :class:`AttributeError` when ReflexArc
        is disabled)."""
        if self._reflex is None:
            raise AttributeError(
                "reflex disabled — construct with enable_reflex=True",
            )
        return self._reflex.registry

    @property
    def events(self) -> EventBus:
        """Event bus (always available)."""
        return self._events

    # v1.2.0: Unified self

    @property
    def cat_self(self) -> Any:
        """Unified self — single entry/exit for all organ read/write paths.

        Set by the app layer during assembly. When None, closed-loop
        features (before_act / after_act / default loops) are unavailable.

        Returns:
            :class:`~meowcat.biology.cat_self.CatSelf` instance, or None.
        """
        return self._cat_self

    @cat_self.setter
    def cat_self(self, value: Any) -> None:
        self._cat_self = value

    # v1.2.5: Current self snapshot

    @property
    def current_snapshot(self) -> Any:
        """The most recent :class:`~meowcat.biology.cat_self.SelfSnapshot`
        from ``CatSelf.before_act()``.

        Set by DefaultLoops before each action. Organs can read this
        to access consistent self-state during action execution.

        Returns None if no snapshot has been taken yet.
        """
        return self._current_snapshot

    # -- Organ container facade ---------------------------------------------
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

    def mount(
        self,
        category: str,
        name: str,
        organ: Any,
        *,
        protocol: type | None = None,
    ) -> None:
        """Mount organ (forwards to :class:`OrganHost`)."""
        self._host.mount(category, name, organ, protocol=protocol)
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

    def organ(self, category: str, name: str) -> Any:
        """Retrieve organ (forwards to :class:`OrganHost`)."""
        return self._host.organ(category, name)

    def organs(self, category: str) -> dict[str, Any]:
        """Snapshot of all organs in a category."""
        return self._host.organs(category)

    def has_organ(self, category: str, name: str) -> bool:
        """Check if organ is mounted."""
        return self._host.has_organ(category, name)

    def unmount(self, category: str, name: str) -> bool:
        """Unmount organ."""
        return self._host.unmount(category, name)

    def assert_organs_mounted(
        self, required: list[tuple[str, str]],
    ) -> None:
        """Assert required organs are mounted."""
        self._host.assert_organs_mounted(required)

    def list_all_organs(self) -> list[tuple[str, str]]:
        """List all mounted organ coordinates (v1.1.8).

        Returns:
            List of ``(category, name)`` tuples.
        """
        return self._host.list_all_organs()

    # -- Event facade -------------------------------------------------------

    def on(self, event: str, handler: Handler | None = None) -> Any:
        """Register event handler."""
        return self._events.on(event, handler)

    def off(self, event: str, handler: Handler) -> bool:
        """Unregister event handler."""
        return self._events.off(event, handler)

    async def emit(self, event: str, payload: Any = None) -> None:
        """Emit event."""
        await self._events.emit(event, payload)

    # -- Organ attribute access control (v1.0.1) ------------------------------
    #
    # ``__getattribute__`` intercepts ALL non-private attribute access on CatBase
    # and kitten instances.  ``_ALWAYS_ALLOWED`` is the whitelist of attributes
    # that bypass the ``allowed_organs`` check.
    #
    # Maintenance rules (v1.2.33):
    #
    # 1. ADD to this set when you add a new public property/method on CatBase
    #    that ALL kittens must access regardless of their ``allowed_organs``.
    #    Typical candidates: lifecycle facades, registries, diagnostics.
    #
    # 2. Do NOT add organ-specific accessors (e.g. ``cat.ears.hear(...)``)
    #    — those go through ``allowed_organs`` filtering.
    #
    # 3. Properties that begin with ``_`` are automatically exempt (hot-path
    #    skip in ``__getattribute__``) and do not need listing here.
    #
    # 4. Review this list whenever a new CatBase constructor boolean switch
    #    (like ``enable_wiring``) is added — the corresponding property
    #    should usually be listed here.
    #
    # Performance: O(1) frozenset membership test.  Keep the set small;
    # each entry adds one lookup per attribute access in restricted kittens.

    def __getattribute__(self, name: str) -> Any:
        """Intercept direct access to forbidden organ names.

        When ``allowed_organs`` is None, all are allowed (default).
        When set, non-``_``-prefixed attribute names not in the allowed set
        nor in ``_ALWAYS_ALLOWED`` raise :class:`IllegalNeuralPathError`.

        Hot path: ``_``-prefixed private attributes skip with zero overhead
        → O(1) frozenset lookup.
        """
        if name.startswith('_'):
            return super().__getattribute__(name)
        allowed = super().__getattribute__('_allowed_organs')
        if allowed is not None and name not in allowed:
            if name not in CatBase._ALWAYS_ALLOWED:
                raise IllegalNeuralPathError(
                    ("_cat", "_cat"), ("_cat", name),
                    reason=(
                        f"Cat '{super().__getattribute__('cat_uid')}' "
                        f"is not allowed to access organ '{name}'."
                    ),
                )
        return super().__getattribute__(name)

    _ALWAYS_ALLOWED: frozenset[str] = frozenset({
        "cat_uid", "name", "cat_address", "global_address", "container", "parent_id",
        "tool_registry", "skill_registry",
        "path_registry", "chain_registry", "loop_registry",
        "loopseq_registry",
        "wiring", "reflexes", "events",
        "list_all_organs", "has_organ",
        "cat_self",  # v1.2.0
        "on_organs_mounted",  # v1.2.36: hook for post-mount organ injection
    })

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
        from meowcat.path import register_builtin_paths  # noqa: PLC0415
        register_builtin_paths(self.path_registry)

    def register_default_chains(self) -> None:
        """Register BUILTIN_CHAINS into chain_registry.

        Safe to call multiple times. Use when ``register_default_chains=False``
        was passed to ``__init__`` but chains are needed later.
        """
        from meowcat.chain import register_builtin_chains  # noqa: PLC0415
        register_builtin_chains(self.chain_registry)

    def register_default_loops(self) -> None:
        """Register BUILTIN_LOOPS into loop_registry (and associated Chains).

        Safe to call multiple times. Use when ``register_default_loops=False``
        was passed to ``__init__`` but loops are needed later.
        """
        from meowcat.loops import register_default_loops  # noqa: PLC0415
        register_default_loops(self.loop_registry, self.chain_registry)

    def register_default_tools(self) -> None:
        """Register BUILTIN_TOOLS into tool_registry.

        Safe to call multiple times — duplicates overwrite by tool name.
        Use when ``register_default_tools=False`` was passed to ``__init__``
        but builtin tools are needed later.
        """
        from meowcat.plus.tools import BUILTIN_TOOLS  # noqa: PLC0415
        for t in BUILTIN_TOOLS:
            self.tool_registry.register(t)

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
            from_organ, to_organ, method, *args, **kwargs,
        )

    async def probe(self, to_organ: Organ) -> dict[str, Any]:
        """Read-only diagnostic (forwards to :class:`Nervous`)."""
        if self._nervous is None:
            raise RuntimeError(
                "probe unavailable — cat was constructed with enable_wiring=False",
            )
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
        assemble_default_cat(
            self, reflex_stages=reflex_stages, reflexes=reflexes)
        self.freeze_nervous_system()


def mount_known_organs(cat: CatBase) -> None:
    """Scan known organ attributes on cat and mount to OrganHost.

    Covers brain / sense / voice / growth four core organ categories.
    Shared by ``factory.create_cat()`` and ``assemble_default_cat()``
    to eliminate duplicate organ name lists.

    Args:
        cat: CatBase instance with organ attributes already set
    """
    _BRAIN_NAMES = {
        "hippocampus", "thalamus", "amygdala", "frontal",
        "hypothalamus", "cerebellum", "cerebrum", "brainstem", "cortex",
    }
    _SENSE_NAMES = {"ears", "eyes", "whiskers", "paws"}
    _VOICE_NAMES = {"mouth", "purr", "tail"}
    _GROWTH_NAMES = {
        "anomaly_growth", "correction_growth", "crystallizer", "role_emergence",
    }

    for name in _BRAIN_NAMES:
        organ = getattr(cat, name, None)
        if organ is not None:
            cat.mount("brain", name, organ)

    for name in _SENSE_NAMES:
        organ = getattr(cat, name, None)
        if organ is not None:
            cat.mount("sense", name, organ)

    for name in _VOICE_NAMES:
        organ = getattr(cat, name, None)
        if organ is not None:
            cat.mount("voice", name, organ)

    for name in _GROWTH_NAMES:
        organ = getattr(cat, name, None)
        if organ is not None:
            cat.mount("growth", name, organ)

    # v1.2.36: Notify that organs are mounted — hooks can now access organs
    cat._notify_organs_mounted()


# -- Top-level assembly function (v0.5.9 added) ------------------------------

def assemble_default_cat(
    cat: CatBase,
    *,
    reflex_stages: list[Any] | None = None,
    reflexes: list[Reflex] | None = None,
) -> None:
    """One-click assemble default cat: scan organ attrs → mount → wire →
    register reflex.

    v0.5.21: No longer calls freeze_nervous_system(); caller controls freeze
    timing. The caller can freeze after wiring + reflex registration
    completes.

    Flow:

    1. Scan known organ attribute names on ``cat`` and ``mount`` to host
    2. ``cat.wire_default_nervous_system()`` assemble biological defaults
    3. Register reflexes (provided by caller)

    Args:
        cat: CatBase instance with organ attributes set
        reflex_stages: Stage list for default text_dialogue reflex
            (only effective when ``reflexes`` contains text_dialogue)
        reflexes: Reflex list; ``None`` means register no reflexes
    """
    mount_known_organs(cat)
    cat.wire_default_nervous_system()

    # v0.5.23: Register generic builtin tools (every cat needs these)
    # v1.2.10: Optional — skip when register_default_tools=False
    if cat._register_default_tools:
        from meowcat.plus.tools import BUILTIN_TOOLS  # noqa: PLC0415
        for t in BUILTIN_TOOLS:
            cat.tool_registry.register(t)

    # Reflexes (caller-provided)
    if reflexes:
        for ref in reflexes:
            # If reflex_stages are provided and it's text_dialogue, inject stages
            if ref.name == "text_dialogue" and reflex_stages is not None:
                ref = Reflex(
                    name=ref.name,
                    trigger=ref.trigger,
                    path=ref.path,
                    priority=ref.priority,
                    stages=list(reflex_stages),
                )
            cat.register_reflex(ref)


__all__ = ["CatBase", "CatHook", "assemble_default_cat", "mount_known_organs"]
