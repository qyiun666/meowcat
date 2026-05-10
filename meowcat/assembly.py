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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from meowcat.colony import Colony
    from meowcat.reflex import ReflexRegistry  # noqa: F401

from meowcat.assemblers import assemble_default_cat, mount_known_organs  # noqa: F401 (re-export)
from meowcat.assembly_diag import DiagnosticMixin
from meowcat.assembly_lifecycle import CatHook, LifecycleMixin
from meowcat.assembly_signals import SignalSystemMixin
from meowcat.errors import IllegalNeuralPathError, StandaloneCatError
from meowcat.events import EventBus, Handler
from meowcat.host import OrganHost
from meowcat.nervous import Nervous
from meowcat.reflex import ReflexArc
from meowcat.tools.skill import SkillRegistry
from meowcat.tools.tool import ToolRegistry
from meowcat.wiring import Wiring

_log = _logging.getLogger(__name__)


class CatBase(LifecycleMixin, DiagnosticMixin, SignalSystemMixin):
    """Cat assembly base class (v0.5.9 composer, v1.0.1 unified kitten model).

    v1.0.1: Added ``parent_id`` / ``allowed_organs`` / ``forbidden_methods``,
    replacing the original KittenBase class. A kitten = a CatBase with
    ``parent_id`` and organ/method permissions restricted.
    """

    def __init__(
        self,
        cat_uid: str,
        *,
        container: Colony | None = None,  # noqa: F821
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
        self._host._cat = self  # v2.1.0: back-reference for organ → cat access
        self._events = EventBus()
        self._nervous: Nervous | None = (
            Nervous(self._host, self._events,
                    forbidden_methods=forbidden_methods)
            if enable_wiring
            else None
        )
        self._reflex: ReflexArc | None = (
            ReflexArc(self._events, self._nervous) if enable_reflex else None
        )
        # v0.5.23: Tool/Skill registries — every cat has claws
        self.tool_registry = ToolRegistry()
        self.skill_registry = SkillRegistry()
        # v0.5.27: Path registry — atomic path table
        from meowcat.path import PathRegistry, register_builtin_paths

        self.path_registry = PathRegistry()
        if register_default_paths:
            register_builtin_paths(self.path_registry)
        # v0.5.28a: Chain registry — Path sequence composer
        from meowcat.chain import ChainRegistry, register_builtin_chains

        self.chain_registry = ChainRegistry()
        if register_default_chains:
            register_builtin_chains(self.chain_registry)
        # v0.5.28b: Loop registry — Chain + trigger/exit events
        from meowcat.loops import LoopRegistry
        from meowcat.loops import register_default_loops as _register_default_loops

        self.loop_registry = LoopRegistry()
        if register_default_loops:
            _register_default_loops(self.loop_registry, self.chain_registry)
        # v1.0.4: LoopSequence registry — Loop sequence composer
        from meowcat.loops import LoopSequenceRegistry

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
        # v2.1.0: Per-cat unified rule engine
        self.rule_set: Any = None
        # v2.2.0: TaskPad — room furniture #5 (to-do list)
        self._task_pad: Any = None
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
    def container(self) -> Colony:  # noqa: F821
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

    @property
    def reflexes(self) -> ReflexRegistry:  # noqa: F821
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

    # v2.2.0: TaskPad — room furniture #5

    @property
    def task_pad(self) -> Any:
        """TaskPad — the cat's to-do list (room furniture #5).

        Set by the app layer during assembly. When None, task-related
        features (do_task / spawn_worker with auto-task) skip TaskPad
        integration.

        Returns:
            :class:`~meowcat.biology.task_pad.TaskPad` instance, or None.
        """
        return self._task_pad

    @task_pad.setter
    def task_pad(self, value: Any) -> None:
        self._task_pad = value

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
        self,
        required: list[tuple[str, str]],
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

    # -- v2.2.0: do_task + spawn_worker -----------------------------------

    async def do_task(
        self,
        task: str,
        *,
        max_rounds: int = 10,
        timeout: float | None = 120.0,
        parser: Any = None,
    ) -> Any:
        """Brain-tool multi-round loop — think → call tools → think → ... until done.

        Each round:
        1. Cerebrum thinks about the current context
        2. If cerebrum output contains a tool call → safety check → execute tool
        3. Tool result feeds back into context for next round
        4. If cerebrum says no more tools needed → final answer

        Args:
            task: Task description (e.g. "写一个用户登录函数").
            max_rounds: Maximum brain-tool rounds (prevents infinite loops).
            timeout: Total timeout in seconds. None = no timeout.
            parser: Tool-call parser. Defaults to ``XmlToolCallParser``.

        Returns:
            :class:`~meowcat.tools.tool_call.DoTaskResult` with final_text,
            rounds, and tool_calls list.
        """
        from meowcat.tools.tool_call import DoTaskResult, ToolCall, XmlToolCallParser

        if parser is None:
            parser = XmlToolCallParser()

        tool_calls: list[ToolCall] = []
        context: str = task
        final_text: str = ""
        rounds: int = 0

        for _ in range(max_rounds):
            rounds += 1
            # 1. Cerebrum thinks
            cerebrum_result: str = await self.path_registry.run(
                self, "deep_reason", prompt=context,
            )

            # 2. Try to extract a tool call
            tool_call = parser.extract(cerebrum_result)
            if tool_call is None:
                # No tool → this is the final answer
                final_text = cerebrum_result
                break

            # 3. Safety check
            safe = await self.path_registry.run(
                self, "assess_safety",
                user_input=str(tool_call.params),
            )
            if isinstance(safe, dict) and safe.get("risk") == "high":
                context = (
                    f"工具 {tool_call.name} 被安全策略拒绝（高风险操作）。"
                    f"请尝试其他方法完成原始任务: {task}"
                )
                continue

            # 4. Execute tool (bypass wiring — PawsEngine is the standard entry)
            from meowcat.tools.paws import PawsEngine

            paws = PawsEngine(self.tool_registry)
            raw_result = await paws.execute(
                name=tool_call.name, **tool_call.params,
            )
            # Extract meaningful output for LLM context (not raw dict repr)
            tool_result: str = raw_result.get("output", str(raw_result))
            tool_calls.append(tool_call)

            # 5. Feed result back as context for next round
            context = (
                f"原始任务: {task}\n\n"
                f"上一轮工具 {tool_call.name} 的执行结果:\n{tool_result}\n\n"
                f"请根据以上结果继续完成原始任务。如果任务已完成请输出最终答案，"
                f"如果还需要调用工具请使用 <tool name=\"...\"> 标签。"
            )
        else:
            # max_rounds exhausted — use last cerebrum output
            final_text = cerebrum_result or ""

        return DoTaskResult(
            final_text=final_text,
            rounds=rounds,
            tool_calls=tool_calls,
        )

    def spawn_worker(
        self,
        name: str,
        task: str,
        *,
        allowed_organs: frozenset[str] | None = None,
    ) -> CatBase:
        """Summon a worker cat and stick a task on its TaskPad.

        The worker cat is a normal :class:`CatBase` instance with
        ``parent_id = self.cat_uid``. It gets a fresh :class:`TaskPad`
        with the task already posted.

        Args:
            name: Worker cat display name.
            task: Task description (auto-posted to worker's TaskPad).
            allowed_organs: Organ access restriction (security sandbox).
                ``None`` = all organs allowed.

        Returns:
            Worker :class:`CatBase` instance with task_pad and parent_id set.

        Emits:
            ``kitten.spawned`` event with ``{parent_id, kitten_id, task}``.
        """
        from meowcat.biology.task_pad import TaskPad

        worker = self._container.create_cat(
            name=name,
            parent_id=self.cat_uid,
            allowed_organs=allowed_organs,
        )
        worker.task_pad = TaskPad()
        worker.task_pad.post(task)

        self._events.emit_nowait("kitten.spawned", {
            "parent_id": self.cat_uid,
            "kitten_id": worker.cat_uid,
            "task": task,
        })
        return worker

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
        if name.startswith("_"):
            return super().__getattribute__(name)
        allowed = super().__getattribute__("_allowed_organs")
        if allowed is not None and name not in allowed and name not in CatBase._ALWAYS_ALLOWED:
            raise IllegalNeuralPathError(
                ("_cat", "_cat"),
                ("_cat", name),
                reason=(
                    f"Cat '{super().__getattribute__('cat_uid')}' "
                    f"is not allowed to access organ '{name}'."
                ),
            )
        return super().__getattribute__(name)

    _ALWAYS_ALLOWED: frozenset[str] = frozenset(
        {
            "cat_uid",
            "name",
            "cat_address",
            "global_address",
            "container",
            "parent_id",
            "tool_registry",
            "skill_registry",
            "path_registry",
            "chain_registry",
            "loop_registry",
            "loopseq_registry",
            "wiring",
            "reflexes",
            "events",
            "list_all_organs",
            "has_organ",
            "cat_self",  # v1.2.0
            "on_organs_mounted",  # v1.2.36: hook for post-mount organ injection
            "task_pad",  # v2.2.0: room furniture #5
            "do_task",  # v2.2.0: brain-tool multi-round loop
            "spawn_worker",  # v2.2.0: summon worker cat
        }
    )


__all__ = ["CatBase", "CatHook", "assemble_default_cat", "mount_known_organs"]
