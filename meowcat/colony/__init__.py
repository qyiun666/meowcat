# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat Colony — Cat container (v1.0.2) + Federation (v1.0.12) + Nameplate (v1.1.4)
+ Shared Area (v1.1.6) + Group Chat (v1.1.7) + Unified Entry (v1.1.8)
+ Task Delegation (v1.3.0).

Colony manages peer-to-peer collaboration + shared storage for multiple cats.
Cats created in a colony are automatically registered and share storage.

v1.0.12: Federation — cross-host Colony mutual awareness, communication (federate + signal_remote).
v1.1.4: Nameplate — name/description/max_cats/colony_uid/is_full + ColonyConfig + default() factory.
v1.1.6: Shared Area — ColonyOwner + ColonyRules + 5 namespace SharedStorage (owner/rules/knowledge/growth/cats).
v1.1.7: Group Chat — broadcast_request (1→many) + signal_between (1→1) unified communication.
v1.1.8: Unified Entry — receive_external (address routing) + list_cat_capabilities + search scope guard (self/colony).
v1.1.20: Shared Memory — SharedMemoryPool for colony-wide sharing + VectorStore integration.
v1.1.21: Collective Intelligence — Cross-cat memory search (Hippocampus.locate scope=colony)
    + delegation with memory snapshot (snapshot + spawn_cat).
v1.1.22: Collective Growth — anomaly/correction shared to growth/ namespace + colony-level role emergence.
v1.2.11: File split — ColonyConfig/ColonyOwner → config.py, ColonyRules → rules.py,
    Federation → federation.py, GlobalColonyRegistry → registry.py.
v1.2.37: File split — Colony federation transports moved to colony/transports.py.
v1.3.0: Task Delegation — delegate_async (fire-and-forget, non-blocking)
    + await_task (poll with kitten health check) + check_cat (alive/stuck/dead)
    + signal_between timeout.
v1.3.8: File split — Namespace storage → namespace.py, Task delegation → delegation.py.
v1.3.9: File split — LLM shelf → llm_shelf.py, Cat ops → cat_ops.py,
    Communication + Storage → communication.py.

Orthogonal to Kitten (master/slave mode):
- Kitten: master cat spawns kitten → result delivered back (parent → child)
- Colony: multiple independent cats collaborate equally (peer ↔ peer), sharing state via SharedStorage
- Colony Federation: cross-host Colony peer-to-peer communication (colony ↔ colony), via FederationTransport
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from meowcat.assembly import CatBase
from meowcat.colony.cat_ops import _CatOpsMixin
from meowcat.colony.communication import _CommunicationMixin
from meowcat.colony.config import ColonyConfig, ColonyOwner
from meowcat.colony.delegation import _DelegationMixin
from meowcat.colony.federation import _FederationMixin
from meowcat.colony.llm_shelf import _LLMShelfMixin
from meowcat.colony.namespace import _NamespaceMixin
from meowcat.colony.registry import GlobalColonyRegistry
from meowcat.colony.rules import ColonyRules
from meowcat.errors import IllegalNeuralPathError
from meowcat.models import ModelConfig
from meowcat.pluggable import Pluggable
from meowcat.protocols_storage import FederationTransport
from meowcat.storage import SharedStore

if TYPE_CHECKING:
    from meowcat.biology.growth import CollectiveGrowth
    from meowcat.biology.roles import CollectiveEmergence

logger = logging.getLogger("meowcat.colony")


class Colony(
    Pluggable,
    _FederationMixin,
    _NamespaceMixin,
    _DelegationMixin,
    _LLMShelfMixin,
    _CatOpsMixin,
    _CommunicationMixin,
):
    """Cat container — manages peer-to-peer collaboration + shared storage.

    Typical usage::

        from meowcat import Colony, CatBase
        from meowcat.defaults import InMemorySharedStore

        colony = Colony("my-colony", storage=InMemorySharedStore(), name="客服组")
        colony = Colony.default("my-team")  # quick setup with defaults

        # Create cats (auto-register + shared storage)
        cat_a = colony.create_cat("a")
        cat_b = colony.create_cat("b", parent_id="a")

        # Inter-cat communication
        result = await colony.signal_between(
            "a", "b", "brain", "hippocampus", "locate",
            query="hello",
        )

        # Result delivery
        await colony.deliver_result("a", "b", {"done": True})

        # Broadcast
        results = await colony.broadcast("health_check")

        # Group chat (broadcast request, 1→many)
        results = await colony.broadcast_request("assess_safety", sql="DROP TABLE...")

    **Group Chat (v1.1.7)**:
    ``broadcast_request()`` sends a request to all cats and collects results
    (1→many request-response). ``signal_between()`` is the private chat path
    (1→1 direct communication). Together they form the colony communication layer.

    **Cross-cat wiring validation**:
    Colony maintains optional ``cross_wiring`` (cross-cat wiring table).
    When set, ``signal_between()`` validates whether the cross-cat edge is allowed.
    When not set, cross-cat signal skips wiring validation (pass through).
    ``broadcast_request()`` bypasses cross-wiring (colony-level operation).
    """

    # -- Cross-cat wiring edge type ------------------------------------
    # (from_cat_id, to_cat_id) allowlist/blocklist
    _CrossEdge = tuple[str, str]

    def __init__(
        self,
        colony_id: str | None = None,
        storage: SharedStore | None = None,
        *,
        name: str | None = None,
        description: str = "",
        max_cats: int | None = None,
        region: str = "",
        llm_shelf: dict[str, ModelConfig] | None = None,
        owner: ColonyOwner | None = None,
        rules: ColonyRules | None = None,
        cross_wiring_allowed: set[_CrossEdge] | None = None,
        cross_wiring_forbidden: set[_CrossEdge] | None = None,
    ) -> None:
        """Construct a cat container.

        Args:
            colony_id: Unique identifier for the colony.
                ``None`` = auto-generate (``CALL_SIGN + base36(timestamp)``,
                12 chars).  Pass a string to override.
            storage: Shared storage instance (satisfying SharedStore).
                None = auto-create InMemorySharedStore (for Colony.default() usage).
            name: Human-readable colony name. Defaults to colony_id.
            description: Colony description.
            max_cats: Maximum number of cats, None = unlimited.
            region: Deployment region (e.g. "us-east", "cn-beijing").
                Used to build ``global_address`` on cats.
            llm_shelf: Shared LLM shelf — named model configs cats can pick from.
                None = empty shelf; cats must bring their own LLM.
            owner: Colony owner profile (name/email/language). Defaults to empty.
            rules: Colony rules (safety/approval/rate-limit). Defaults to permissive.
            cross_wiring_allowed: Cross-cat allowlist edges. None = no validation (allow all by default).
            cross_wiring_forbidden: Cross-cat blocklist edges (higher priority than allowlist).
        """
        Pluggable.__init__(self)  # Pluggable init
        if colony_id is None:
            colony_id = Colony._generate_colony_uid()
        self.colony_id = colony_id
        self._name = name or colony_id
        self._description = description
        self._max_cats = max_cats
        self.region = region
        self._colony_uid = colony_id
        self._cat_counter: int = 0
        self._storage = storage
        self._llm_shelf: dict[str, ModelConfig] = dict(llm_shelf or {})
        self._cats: dict[str, CatBase] = {}
        self._cross_allowed: set[Colony._CrossEdge] = cross_wiring_allowed or set()
        self._cross_forbidden: set[Colony._CrossEdge] = cross_wiring_forbidden or set()
        self._has_cross_wiring = (
            cross_wiring_allowed is not None or cross_wiring_forbidden is not None
        )
        self._owner = owner or ColonyOwner()
        self._rules = rules or ColonyRules()
        self._registered_ns: set[str] = {
            "owner",
            "rules",
            "knowledge",
            "growth",
            "cats",
            "__tasks__",
        }
        # -- Federation state (initialized here, used by _FederationMixin) --
        self._transport: FederationTransport | None = None
        self._federation_task: asyncio.Task | None = None
        self._pending_remote: dict[str, asyncio.Future] = {}
        self._federated = False
        # -- Shared Memory (v1.1.20) ---------------------------------------
        self._memory_pool = None  # lazily created on first access
        # -- Collective Growth + Emergence (v1.1.22) -------------------------
        self._growth = None  # lazily created on first access
        self._emergence = None  # lazily created on first access
        # -- Task delegation (v1.3.0) -----------------------------------
        # actual task results (non-serialized)
        self._task_results: dict[str, Any] = {}

    # -- UID generation -----------------------------------------------

    @staticmethod
    def _base36(n: int) -> str:
        """Encode integer to base36 (0-9a-z)."""
        chars = "0123456789abcdefghijklmnopqrstuvwxyz"
        if n == 0:
            return "0"
        result = ""
        while n:
            n, m = divmod(n, 36)
            result = chars[m] + result
        return result

    @staticmethod
    def _generate_colony_uid() -> str:
        """Generate globally-unique colony UID.

        Format: ``{CALL_SIGN}{base36(timestamp)}``
        - CALL_SIGN (6 chars): MD5 first-6 of call-sign string (watermark)
        - base36 timestamp (6 chars): second-level Unix time in base36
        → 12 chars total, e.g. ``0efb30telx53``
        """
        from meowcat.constants import CALL_SIGN

        return f"{CALL_SIGN}{Colony._base36(int(time.time()))}"

    def _next_cat_uid(self) -> str:
        """Generate cat_uid: 2-digit increment."""
        self._cat_counter += 1
        return f"{self._cat_counter:02d}"

    # -- Nameplate properties ------------------------------------------

    @property
    def name(self) -> str:
        """Human-readable colony name."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        old = self._name
        self._name = value
        for _hook, _r in self._run_plugs_sync("on_name_change", old, value):
            pass  # fire-and-forget notification

    @property
    def description(self) -> str:
        """Colony description."""
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = value

    @property
    def max_cats(self) -> int | None:
        """Maximum cats capacity, None = unlimited."""
        return self._max_cats

    @property
    def colony_uid(self) -> str:
        """Colony unique identifier: ``CALL_SIGN + base36(timestamp)``, 12 chars.

        Auto-generated when ``colony_id`` is not explicitly passed.
        Same value as :attr:`colony_id`.
        """
        return self._colony_uid

    @property
    def is_full(self) -> bool:
        """Whether the colony has reached its cat capacity."""
        if self._max_cats is None:
            return False
        return len(self._cats) >= self._max_cats

    # -- Owner / Rules (v1.1.6) ---------------------------------------

    @property
    def owner(self) -> ColonyOwner:
        """Colony owner profile."""
        return self._owner

    @owner.setter
    def owner(self, value: ColonyOwner) -> None:
        self._owner = value

    @property
    def rules(self) -> ColonyRules:
        """Colony rules (safety/approval/rate-limit). Extends Pluggable."""
        return self._rules

    # -- Pluggable aliases ---------------------------------------------

    def plug(self, slot: str, handler: Any) -> None:
        """Insert a custom plugin (alias for mount_plug)."""
        self.mount_plug(slot, handler)

    def unplug(self, slot: str, handler: Any | None = None) -> None:
        """Remove a plugin (alias for unmount_plug)."""
        self.unmount_plug(slot, handler)

    # -- Factory -------------------------------------------------------

    @classmethod
    def default(cls, colony_id: str, **kwargs: Any) -> Colony:
        """Quick setup with InMemorySharedStore + name defaults.

        Args:
            colony_id: Unique identifier for the colony.
            **kwargs: Forwarded to Colony.__init__ (storage overridable).

        Returns:
            Ready-to-use Colony instance.
        """
        from meowcat.defaults.stores import InMemorySharedStore

        storage = kwargs.pop("storage", InMemorySharedStore())
        name = kwargs.pop("name", None) or colony_id
        return cls(colony_id, storage=storage, name=name, **kwargs)

    # -- Cross-cat wiring ---------------------------------------------

    def allow_cross(self, from_cat: str, to_cat: str) -> None:
        """Declare a cross-cat allowlist edge (from_cat → to_cat allows signal)."""
        self._cross_allowed.add((from_cat, to_cat))
        self._has_cross_wiring = True

    def forbid_cross(self, from_cat: str, to_cat: str) -> None:
        """Declare a cross-cat blocklist edge (from_cat → to_cat forbids signal)."""
        self._cross_forbidden.add((from_cat, to_cat))
        self._has_cross_wiring = True

    def _assert_cross_allowed(self, from_id: str, to_id: str) -> None:
        """Validate whether cross-cat edge is allowed.

        Raises:
            IllegalNeuralPathError: Cross-cat edge is not allowed.
        """
        if not self._has_cross_wiring:
            return  # No cross_wiring set → pass through

        if (from_id, to_id) in self._cross_forbidden:
            raise IllegalNeuralPathError(
                ("colony", from_id),
                ("colony", to_id),
                reason=f"cross-cat signal forbidden: {from_id} → {to_id}",
            )

        if self._cross_allowed and (from_id, to_id) not in self._cross_allowed:
            raise IllegalNeuralPathError(
                ("colony", from_id),
                ("colony", to_id),
                reason=f"cross-cat signal not allowed: {from_id} → {to_id}",
            )

    # -- Convenience methods ------------------------------------------

    @property
    def cat_count(self) -> int:
        """Number of cats in the colony."""
        return len(self._cats)

    # -- Shared Memory (v1.1.20) --------------------------------------

    @property
    def memory(self):  # noqa: F821
        """Colony-level shared memory pool (lazy-init).

        Usage::

            await colony.memory.remember("用户喜欢 Python 3.12", {"cat": "planner"})
            results = await colony.memory.recall("Python 版本")
        """
        if self._memory_pool is None:
            from meowcat.colony.memory import SharedMemoryPool

            self._memory_pool = SharedMemoryPool(self)
        return self._memory_pool

    # -- Collective Growth + Emergence (v1.1.22) -----------------------

    @property
    def growth(self) -> CollectiveGrowth:
        """Colony-level collective growth (lazy-init).

        Usage::

            await colony.growth.record_anomaly("cat1", "DB schema mismatch")
            await colony.growth.record_correction("cat1", "DROP TABLE",
                                                    correct="DELETE WHERE id=...")
            anomalies = await colony.growth.list_anomalies()
        """
        if self._growth is None:
            from meowcat.biology.growth import CollectiveGrowth

            self._growth = CollectiveGrowth(self)
        return self._growth

    @property
    def emergence(self) -> CollectiveEmergence:
        """Colony-level collective role emergence (lazy-init).

        Usage::

            roles = await colony.emergence.detect_roles()
            await colony.emergence.record_pattern("cat1", "SQL审查",
                                                    evidence="发现3次SQL异常")
        """
        if self._emergence is None:
            from meowcat.biology.roles import CollectiveEmergence

            self._emergence = CollectiveEmergence(self)
        return self._emergence


__all__ = [
    "Colony",
    "ColonyConfig",
    "ColonyOwner",
    "ColonyRules",
    "FederationTransport",
    "GlobalColonyRegistry",
]
