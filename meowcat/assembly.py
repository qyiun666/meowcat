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
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import json as _json
import time as _time
from collections.abc import Awaitable, Callable
from typing import Any, AsyncIterator

from meowcat.errors import IllegalNeuralPathError
from meowcat.events import EventBus, Handler
from meowcat.host import OrganHost
from meowcat.loop import Lifecycle
from meowcat.nervous import Nervous
from meowcat.reflex import Reflex, ReflexArc
from meowcat.tools.skill import SkillRegistry
from meowcat.tools.tool import ToolRegistry
from meowcat.wiring import Organ, Wiring

# v1.0.14: Lifecycle hook type — async callable accepting a CatBase instance
CatHook = Callable[["CatBase"], Awaitable[None]]


class CatBase:
    """Cat assembly base class (v0.5.9 composer, v1.0.1 unified kitten model).

    v1.0.1: Added ``parent_id`` / ``allowed_organs`` / ``forbidden_methods``,
    replacing the original KittenBase class. A kitten = a CatBase with
    ``parent_id`` and organ/method permissions restricted.
    """

    def __init__(
        self,
        cat_id: str,
        *,
        parent_id: str | None = None,
        allowed_organs: frozenset[str] | None = None,
        forbidden_methods: frozenset[str] = frozenset(),
        enable_wiring: bool = True,
        enable_reflex: bool = True,
    ) -> None:
        """Construct cat skeleton.

        Args:
            cat_id: Unique cat identifier.
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
        """
        self._parent_id = parent_id
        # v1.0.1: Set _allowed_organs=None first to avoid __init__ internal
        # self.xxx assignments being intercepted by __getattribute__;
        # set the real value at the end.
        self._allowed_organs: frozenset[str] | None = None
        self._host = OrganHost(cat_id)
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
        register_builtin_paths(self.path_registry)
        # v0.5.28a: Chain registry — Path sequence composer
        from meowcat.chain import ChainRegistry, register_builtin_chains  # noqa: PLC0415
        self.chain_registry = ChainRegistry()
        register_builtin_chains(self.chain_registry)
        # v0.5.28b: Loop registry — Chain + trigger/exit events
        from meowcat.loops import LoopRegistry, register_default_loops  # noqa: PLC0415
        self.loop_registry = LoopRegistry()
        register_default_loops(self.loop_registry, self.chain_registry)
        # v1.0.4: LoopSequence registry — Loop sequence composer
        from meowcat.loops import LoopSequenceRegistry  # noqa: PLC0415
        self.loopseq_registry = LoopSequenceRegistry()
        # v1.0.14: Lifecycle hooks
        self._start_hooks: list[CatHook] = []
        self._shutdown_hooks: list[CatHook] = []
        # v1.0.15: Long-running workflow tracking
        self._active_workflows: dict[str, dict[str, Any]] = {}
        # v1.0.1: allowed_organs must be assigned after all properties are set,
        # to avoid __init__ internal self.xxx assignments being intercepted
        # by __getattribute__
        self._allowed_organs = allowed_organs

    # -- Read-only facade properties -----------------------------------------

    @property
    def parent_id(self) -> str | None:
        """Parent cat identifier (plain string, no object reference)."""
        return self._parent_id

    @property
    def cat_id(self) -> str:
        """Cat unique identifier (read from ``_host``)."""
        return self._host.cat_id

    @property
    def wiring(self) -> Wiring:
        """Neural connectivity graph (raises :class:`AttributeError` when
        Nervous is disabled)."""
        if self._nervous is None:
            raise AttributeError(
                "wiring disabled — construct with enable_wiring=True",
            )
        return self._nervous.wiring

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

    # -- Organ container facade ---------------------------------------------

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
                        f"Cat '{super().__getattribute__('cat_id')}' "
                        f"is not allowed to access organ '{name}'."
                    ),
                )
        return super().__getattribute__(name)

    _ALWAYS_ALLOWED: frozenset[str] = frozenset({
        "cat_id", "parent_id",
        "tool_registry", "skill_registry",
        "path_registry", "chain_registry", "loop_registry",
        "loopseq_registry",
        "wiring", "reflexes", "events",
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
        self._nervous._middleware.append(mw)

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

    # -- Diagnostic shortcuts --------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """Full-body checkup — returns diagnostic snapshots of all organs.

        Shortcut, equivalent to ``Stethoscope.probe_all(self)``.

        Returns:
            ``{"brain:hippocampus": {...}, "sense:ears": {...}, ...}``
        """
        from meowcat.diagnose import Stethoscope  # noqa: PLC0415
        return await Stethoscope.probe_all(self)

    async def brain_check(self) -> dict[str, Any]:
        """Check brain-area organs only.

        Shortcut, equivalent to ``Stethoscope.probe_category(self, "brain")``.

        Returns:
            ``{"hippocampus": {...}, "cerebrum": {...}, ...}``
        """
        from meowcat.diagnose import Stethoscope  # noqa: PLC0415
        return await Stethoscope.probe_category(self, "brain")

    def wiring_diagram(self, format: str = "mermaid") -> str:
        """Generate a visualization string of the wiring diagram.

        Raises :class:`AttributeError` when wiring is disabled.

        Args:
            format: ``"mermaid"`` or ``"dot"``

        Returns:
            Diagram description string in mermaid or dot format

        Examples:

            >>> print(cat.wiring_diagram())
            >>> print(cat.wiring_diagram(format="dot"))
        """
        from meowcat.diagnose import render_wiring  # noqa: PLC0415
        # Collect all mounted organs as input for orphan node detection
        mounted: frozenset[Organ] = frozenset(self._host.list_all_organs())
        return render_wiring(self.wiring, format=format, organs=mounted)

    # -- Lifecycle -----------------------------------------------------------

    def register_workflow(self, wf: dict[str, Any]) -> None:
        """Register a workflow entity to the active tracking list.

        The application layer calls this after creating a WorkflowShape;
        the framework auto-saves checkpoints on shutdown.

        Args:
            wf: Dict form of WorkflowShape, must contain ``entity_id`` key
        """
        eid = wf.get("entity_id", wf.get("id", ""))
        if eid:
            self._active_workflows[eid] = wf

    def active_workflows(self) -> list[dict[str, Any]]:
        """Return all currently active (unfinished) workflows."""
        return [
            wf for wf in self._active_workflows.values()
            if wf.get("status") in ("active", "awaiting_user")
        ]

    async def _resume_workflows(self) -> None:
        """Scan Hippocampus for unfinished Workflows and load into
        ``_active_workflows``.

        Silent failure: missing Hippocampus or query exceptions do not
        block startup.
        """
        if not self.has_organ("brain", "hippocampus"):
            return
        try:
            hippo = self.organ("brain", "hippocampus")
            active = hippo.list_active_workflows(self.cat_id)
            for wf in active:
                eid = wf.get("entity_id", wf.get("id", ""))
                if eid:
                    self._active_workflows[eid] = wf
        except Exception:
            pass

    async def _checkpoint_workflows(self) -> None:
        """Iterate all active Workflows and write checkpoint to Hippocampus.

        Silent failure: missing Hippocampus or write exceptions do not
        block shutdown.
        """
        if not self._active_workflows or not self.has_organ("brain", "hippocampus"):
            return
        if self._nervous is None:
            return
        try:
            from meowcat.anatomy import BRAINSTEM, HIPPOCAMPUS  # noqa: PLC0415
            for eid, wf in self._active_workflows.items():
                if wf.get("status") not in ("active", "awaiting_user"):
                    continue
                checkpoint_data = {
                    "current_step": wf.get("current_step", 0),
                    "checkpoint": wf.get("checkpoint", {}),
                    "updated_at": str(_time.time()),
                }
                await self._nervous.signal(
                    BRAINSTEM, HIPPOCAMPUS, "append_content",
                    entity_id=eid,
                    text="\n[checkpoint] " + _json.dumps(checkpoint_data),
                )
        except Exception:
            pass

    def on_start(self, hook: CatHook) -> None:
        """Register a start hook. Called in registration order after
        assembly completes.

        Args:
            hook: Async callable accepting a CatBase instance, called after
                  ``start()`` emits the lifecycle.start event.

        Examples:

            >>> cat.on_start(lambda c: c.gateway.start(c))
        """
        self._start_hooks.append(hook)

    def on_shutdown(self, hook: CatHook) -> None:
        """Register a shutdown hook. Called in **reverse** registration
        order before shutdown.

        Args:
            hook: Async callable accepting a CatBase instance, called in
                  reverse order before ``shutdown()`` emits the
                  lifecycle.shutdown event.

        Examples:

            >>> cat.on_shutdown(lambda c: c.gateway.stop())
        """
        self._shutdown_hooks.append(hook)

    async def start(self) -> None:
        """Start the cat. Scan unfinished Workflows → emit lifecycle.start
        → call on_start hooks in registration order.

        Subclasses may override, **must call ``await super().start()``**.
        """
        # v1.0.15: Scan Hippocampus for unfinished Workflows and load
        await self._resume_workflows()
        await self._events.emit(Lifecycle.START, {"cat": self})
        for hook in self._start_hooks:
            await hook(self)

    async def shutdown(self) -> None:
        """Shut down the cat. Save active Workflows → call on_shutdown hooks
        in reverse order → emit lifecycle.shutdown.

        Subclasses may override, **must call ``await super().shutdown()``**.
        """
        # v1.0.15: Save all active Workflows to Hippocampus
        await self._checkpoint_workflows()
        for hook in reversed(self._shutdown_hooks):
            await hook(self)
        await self._events.emit(Lifecycle.SHUTDOWN, {"cat": self})

    # -- Loop execution -------------------------------------------------------

    async def run_loop(self, name: str, **initial_input: Any) -> dict[str, Any]:
        """Execute a loop: trigger event → run chain → exit event.

        Equivalent to::

            self.loop_registry.run(self, name, **initial_input)

        Args:
            name: Loop name (e.g. ``"conversation"``)
            **initial_input: Initial input passed to chain's first step

        Returns:
            Chain execution result (dict)

        Raises:
            KeyError: Loop does not exist

        Examples:

            result = await cat.run_loop("conversation", message="hello")
        """
        return await self.loop_registry.run(self, name, **initial_input)

    # -- Loop sequence execution (v1.0.4) -------------------------------------

    async def run_loopseq(self, name: str, **initial_input: Any) -> dict[str, Any]:
        """Execute a loop sequence: compose multiple Loops sequentially or concurrently.

        Equivalent to::

            self.loopseq_registry.run(self, name, **initial_input)

        Args:
            name: Loop sequence name (e.g. ``"daily_maintenance"``)
            **initial_input: Initial input

        Returns:
            Last step result (sequential) or ``{loop_name: result, ...}``
            (event_driven)

        Raises:
            KeyError: Loop sequence does not exist

        Examples:

            result = await cat.run_loopseq("daily_maintenance")
        """
        return await self.loopseq_registry.run(self, name, **initial_input)

    # -- CLI facade methods (v1.0.9) ------------------------------------------

    async def search_memory(self, query: str, limit: int = 5) -> dict[str, Any]:
        """Search memory. Equivalent to ``/search <query>``.

        Executes the ``memory_search`` chain (locate path), retrieving
        relevant memories from the hippocampus.

        Args:
            query: Search keywords
            limit: Max results to return

        Returns:
            Memory retrieval result dict
        """
        return await self.chain_registry.run(
            self, "memory_search", msg=query, session_id=self.cat_id,
        )

    async def memory_stats(self) -> dict[str, Any]:
        """Memory stats. Equivalent to ``/stats``.

        Calls the hippocampus ``stats`` method via signal to get memory stats.

        Returns:
            Memory stats dict
        """
        from meowcat.anatomy import BRAINSTEM, HIPPOCAMPUS  # noqa: PLC0415
        result = await self.signal(BRAINSTEM, HIPPOCAMPUS, "stats")
        if isinstance(result, dict):
            return result
        return {"stats": result}

    async def run_maintenance(
        self, country_code: str | None = None,
    ) -> dict[str, Any]:
        """Run maintenance. Equivalent to ``/maintenance``.

        Executes the ``daily_maintenance`` loop sequence (self-maintenance
        then health check).

        Args:
            country_code: Optional country code for regional decay strategy

        Returns:
            Maintenance result dict
        """
        return await self.run_loopseq(
            "daily_maintenance",
        )


def mount_known_organs(cat: CatBase) -> None:
    """Scan known organ attributes on cat and mount to OrganHost.

    Covers brain / sense / voice three core organ categories.
    Growth organs are mounted by the application layer.
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
    from meowcat.tools.builtin import BUILTIN_TOOLS  # noqa: PLC0415
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
