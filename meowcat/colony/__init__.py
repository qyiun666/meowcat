"""meowcat Colony — Cat container (v1.0.2) + Federation (v1.0.12) + Nameplate (v1.1.4) + Shared Area (v1.1.6) + Group Chat (v1.1.7) + Unified Entry (v1.1.8).

Colony manages peer-to-peer collaboration + shared storage for multiple cats.
Cats created in a colony are automatically registered and share storage.

v1.0.12: Federation — cross-host Colony mutual awareness, communication (federate + signal_remote).
v1.1.4: Nameplate — name/description/max_cats/colony_uid/is_full + ColonyConfig + default() factory.
v1.1.6: Shared Area — ColonyOwner + ColonyRules + 5 namespace SharedStorage (owner/rules/knowledge/growth/cats).
v1.1.7: Group Chat — broadcast_request (1→many request-response) + signal_between (1→1 private chat) unified communication.
v1.1.8: Unified Entry — receive_external (address routing) + list_cat_capabilities + search scope guard (self/colony).
v1.1.20: Shared Memory — SharedMemoryPool for colony-wide knowledge sharing + VectorStore integration.
v1.1.21: Collective Intelligence — Cross-cat memory search (Hippocampus.locate scope=colony) + delegation with memory snapshot (snapshot + spawn_cat).
v1.1.22: Collective Growth — anomaly/correction shared to growth/ namespace + colony-level role emergence.
v1.2.11: File split — ColonyConfig/ColonyOwner → config.py, ColonyRules → rules.py, Federation → federation.py, GlobalColonyRegistry → registry.py.

Orthogonal to Kitten (master/slave mode):
- Kitten: master cat spawns kitten → result delivered back (parent → child)
- Colony: multiple independent cats collaborate equally (peer ↔ peer), sharing state via SharedStorage
- Colony Federation: cross-host Colony peer-to-peer communication (colony ↔ colony), via FederationTransport
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

import asyncio
import logging
from typing import Any, TYPE_CHECKING

from meowcat.assembly import CatBase
from meowcat.errors import IllegalNeuralPathError
from meowcat.models import ModelConfig
from meowcat.pluggable import Pluggable
from meowcat.storage import SharedStore
from meowcat.protocols_storage import FederationTransport

from meowcat.colony.config import ColonyConfig, ColonyOwner
from meowcat.colony.rules import ColonyRules
from meowcat.colony.federation import _FederationMixin
from meowcat.colony.registry import GlobalColonyRegistry

if TYPE_CHECKING:
    from meowcat.biology.growth import CollectiveGrowth
    from meowcat.biology.roles import CollectiveEmergence

logger = logging.getLogger("meowcat.colony")


class Colony(Pluggable, _FederationMixin):
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
        colony_id: str,
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
        self._cross_allowed: set[Colony._CrossEdge] = cross_wiring_allowed or set(
        )
        self._cross_forbidden: set[Colony._CrossEdge] = cross_wiring_forbidden or set(
        )
        self._has_cross_wiring = (
            cross_wiring_allowed is not None or cross_wiring_forbidden is not None
        )
        self._owner = owner or ColonyOwner()
        self._rules = rules or ColonyRules()
        self._registered_ns: set[str] = {
            "owner", "rules", "knowledge", "growth", "cats"}
        # -- Federation state (initialized here, used by _FederationMixin) --
        self._transport: FederationTransport | None = None
        self._federation_task: asyncio.Task | None = None
        self._pending_remote: dict[str, asyncio.Future] = {}
        self._federated = False
        # -- Shared Memory (v1.1.20) ---------------------------------------
        self._memory_pool = None  # lazily created on first access
        # -- Collective Growth + Emergence (v1.1.22) -------------------------
        self._growth = None     # lazily created on first access
        self._emergence = None   # lazily created on first access

    # -- UID generation -----------------------------------------------

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
        for _hook, r in self._run_plugs_sync("on_name_change", old, value):
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
        """Colony unique identifier: ``colony_id + 6-char MD5``."""
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

    # -- Namespace storage (v1.1.6) -----------------------------------

    _NS_PREFIX = "__colony__"

    def _ns_key(self, namespace: str, key: str) -> str:
        """Construct a namespace-isolated storage key: ``__colony__/{ns}/{key}``."""
        return f"{self._NS_PREFIX}/{namespace}/{key}"

    def _ns_prefix(self, namespace: str) -> str:
        """Prefix for listing keys in a namespace."""
        return f"{self._NS_PREFIX}/{namespace}/"

    async def ns_get(self, namespace: str, key: str) -> Any:
        """Read from a colony-level namespace in shared storage.

        Args:
            namespace: e.g. ``"owner"``, ``"rules"``, ``"knowledge"``, ``"growth"``, ``"cats"``.
            key: Key within the namespace.
        """
        return await self._ensure_storage().get(self._ns_key(namespace, key))

    async def ns_set(self, namespace: str, key: str, value: Any) -> None:
        """Write to a colony-level namespace in shared storage.

        Args:
            namespace: e.g. ``"knowledge"``.
            key: Key within the namespace.
            value: Arbitrary value to store.
        """
        await self._ensure_storage().set(self._ns_key(namespace, key), value)

    async def ns_delete(self, namespace: str, key: str) -> None:
        """Delete a key from a colony-level namespace."""
        await self._ensure_storage().delete(self._ns_key(namespace, key))

    async def ns_list_keys(self, namespace: str) -> list[str]:
        """List all keys in a colony-level namespace (prefix stripped).

        Args:
            namespace: e.g. ``"knowledge"``.

        Returns:
            List of keys within the namespace, without prefix.
        """
        prefix = self._ns_prefix(namespace)
        all_keys = await self._ensure_storage().list_keys()
        return [k[len(prefix):] for k in all_keys if k.startswith(prefix)]

    async def ns_watch(self, namespace: str, pattern: str) -> Any:
        """Watch namespace key changes matching pattern.

        Args:
            namespace: e.g. ``"growth"``.
            pattern: Key pattern for matching.

        Yields:
            ``(key, value)`` tuples.
        """
        ns_pattern = f"{self._ns_prefix(namespace)}{pattern}"
        async for item in self._ensure_storage().watch(ns_pattern):
            yield item

    @property
    def registered_namespaces(self) -> frozenset[str]:
        """Currently registered namespace names (frozen snapshot)."""
        return frozenset(self._registered_ns)

    def storage_plug(self, slot: str, name: str) -> None:
        """Register a custom namespace or other storage-level plugin.

        Usage::

            colony.storage_plug("namespace", "audit")  # 新增 audit/ 命名空间

        Args:
            slot: Plugin slot name (currently supports ``"namespace"``).
            name: Namespace name to register.
        """
        if slot == "namespace":
            self._registered_ns.add(name)

    # -- LLM shelf (v1.1.5) -------------------------------------------

    @property
    def llm_shelf(self) -> dict[str, ModelConfig]:
        """Read-only copy of the shared LLM shelf."""
        return dict(self._llm_shelf)

    def stock_llm(self, name: str, config: ModelConfig) -> None:
        """Stock a new LLM config on the shelf (overwrite if exists)."""
        self._llm_shelf[name] = config

    def unstock_llm(self, name: str) -> bool:
        """Remove an LLM from the shelf. Returns True if removed."""
        return self._llm_shelf.pop(name, None) is not None

    def pick_llm(self, name: str | None = None) -> ModelConfig:
        """Pick an LLM config from the shelf with cascade fallback.

        Cascade order:
        1. Named lookup — ``pick_llm("smart")``
        2. First available — ``pick_llm()`` returns any entry
        3. Plugin hook — ``on_pick`` plugin can override (first-hit)

        Raises:
            ValueError: Shelf is empty and no name specified.
            KeyError: Named LLM not found on shelf.
        """
        # Plugin hook (first-hit)
        for _hook, r in self._run_plugs_sync("on_pick", name, dict(self._llm_shelf)):
            if isinstance(r, ModelConfig):
                return r

        if name is not None:
            if name not in self._llm_shelf:
                raise KeyError(
                    f"LLM '{name}' not found on shelf. "
                    f"Available: {list(self._llm_shelf.keys())}"
                )
            return self._llm_shelf[name]

        if not self._llm_shelf:
            raise ValueError(
                f"LLM shelf is empty in colony '{self.colony_id}'. "
                f"Stock at least one LLM or pass llm=... explicitly."
            )
        return next(iter(self._llm_shelf.values()))

    def assemble_cat(
        self,
        *,
        name: str | None = None,
        llm: str | ModelConfig | None = None,
        parent_id: str | None = None,
        allowed_organs: frozenset[str] | None = None,
        memory_snapshot: dict | None = None,
        **cat_kwargs: Any,
    ) -> CatBase:
        """Create a cat with LLM picked from shelf (or own config).

        LLM resolution order:
        1. ``llm=ModelConfig(...)`` — cat brings its own LLM
        2. ``llm="smart"`` — pick named LLM from shelf
        3. ``llm=None`` — pick first available from shelf

        Args:
            name: Optional display name (defaults to cat_uid).
            llm: LLM config or shelf name. None = auto-pick from shelf.
            parent_id: Parent cat identifier.
            allowed_organs: Organ access allowlist.
            memory_snapshot: Context slice assigned by parent cat.
            **cat_kwargs: Additional arguments passed to CatBase.

        Returns:
            Registered CatBase instance with ``_llm_config`` attribute.
        """
        if isinstance(llm, ModelConfig):
            llm_config = llm
        else:
            llm_config = self.pick_llm(llm)

        cat = self.create_cat(
            name=name,
            parent_id=parent_id,
            allowed_organs=allowed_organs,
            memory_snapshot=memory_snapshot,
            **cat_kwargs,
        )
        cat._llm_config = llm_config  # type: ignore[attr-defined]
        return cat

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
        from meowcat.defaults.stores import InMemorySharedStore  # noqa: PLC0415
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
                ("colony", from_id), ("colony", to_id),
                reason=f"cross-cat signal forbidden: {from_id} → {to_id}",
            )

        if self._cross_allowed and (from_id, to_id) not in self._cross_allowed:
            raise IllegalNeuralPathError(
                ("colony", from_id), ("colony", to_id),
                reason=f"cross-cat signal not allowed: {from_id} → {to_id}",
            )

    # -- Create -------------------------------------------------------

    def create_cat(
        self,
        *,
        name: str | None = None,
        parent_id: str | None = None,
        allowed_organs: frozenset[str] | None = None,
        memory_snapshot: dict | None = None,
        **cat_kwargs: Any,
    ) -> CatBase:
        """Create a cat in the colony and auto-register it.

        The ``cat_uid`` is auto-generated (2-digit increment).

        Args:
            name: Optional display name (defaults to cat_uid).
            parent_id: Parent cat identifier (string, no object reference).
            allowed_organs: Organ access allowlist, None = allow all.
            memory_snapshot: Context slice assigned by parent cat.
            **cat_kwargs: Additional arguments passed to CatBase.

        Returns:
            Registered CatBase instance.
        """
        if self.is_full:
            raise RuntimeError(
                f"Colony '{self.colony_id}' is full "
                f"({len(self._cats)}/{self._max_cats} cats)"
            )

        cat_uid = self._next_cat_uid()
        cat = CatBase(
            cat_uid,
            container=self,
            parent_id=parent_id,
            allowed_organs=allowed_organs,
            **cat_kwargs,
        )
        if name is not None:
            cat._name = name  # type: ignore[attr-defined]
        # type: ignore[attr-defined]
        cat._address = f"{self.colony_id}_{cat_uid}"

        # Inject shared storage reference
        if self._storage is not None:
            cat._colony_storage = self._storage  # type: ignore[attr-defined]

        # Inject memory_snapshot (context slice)
        if memory_snapshot:
            # type: ignore[attr-defined]
            cat._memory_snapshot = memory_snapshot

        # v1.1.21: Wire colony memory to hippocampus for cross-cat search
        if cat.has_organ("brain", "hippocampus"):
            hippo = cat.organ("brain", "hippocampus")
            if hasattr(hippo, "set_colony_memory"):
                hippo.set_colony_memory(self.memory)

        self.register(cat)
        return cat

    # -- v1.1.21 Delegation: spawn cat with memory snapshot ----------

    def spawn_cat(
        self,
        *,
        name: str | None = None,
        parent_id: str | None = None,
        memory_snapshot: dict | None = None,
        allowed_organs: frozenset[str] | None = None,
        **cat_kwargs: Any,
    ) -> CatBase:
        """Create a kitten with inherited memory context.

        Convenience wrapper around :meth:`create_cat` that explicitly
        names the delegation intent.

        Usage::

            slice = parent.hippocampus.snapshot("users表", "auth模块")
            kitten = colony.spawn_cat(
                parent_id=parent.cat_uid,
                memory_snapshot=slice,
            )

        Args:
            name: Optional display name (defaults to cat_uid).
            parent_id: Parent cat identifier.
            memory_snapshot: Context slice from parent's hippocampus.
            allowed_organs: Organ access allowlist.
            **cat_kwargs: Forwarded to CatBase.
        """
        return self.create_cat(
            name=name,
            parent_id=parent_id,
            memory_snapshot=memory_snapshot,
            allowed_organs=allowed_organs,
            **cat_kwargs,
        )

    # -- Register / Remove --------------------------------------------

    def register(self, cat: CatBase) -> None:
        """Register a cat into the colony (overwrites if already exists).

        Args:
            cat: CatBase instance.
        """
        if self._storage is not None:
            cat._colony_storage = self._storage  # type: ignore[attr-defined]
        self._cats[cat.cat_uid] = cat

    def unregister(self, cat_uid: str) -> None:
        """Remove a cat from the colony.

        Args:
            cat_uid: Unique identifier for the cat.

        Raises:
            KeyError: Cat does not exist.
        """
        del self._cats[cat_uid]

    def get_cat(self, cat_uid: str) -> CatBase:
        """Get a cat by uid.

        Args:
            cat_uid: Unique identifier for the cat.

        Returns:
            CatBase instance.

        Raises:
            KeyError: Cat does not exist.
        """
        return self._cats[cat_uid]

    def list_cats(self) -> list[str]:
        """List all cat uids in the colony.

        Returns:
            List of cat_uid strings.
        """
        return list(self._cats.keys())

    # -- Alias methods (v1.0.9) ---------------------------------------

    def adopt(self, cat: CatBase) -> None:
        """Adopt a cat (semantic alias for register).

        Args:
            cat: CatBase instance.
        """
        self.register(cat)

    def release(self, cat_uid: str) -> None:
        """Release a cat (semantic alias for unregister).

        Args:
            cat_uid: Unique identifier for the cat.

        Raises:
            KeyError: Cat does not exist.
        """
        self.unregister(cat_uid)

    # -- Shared storage (namespace isolation) -------------------------

    def _ensure_storage(self) -> SharedStore:
        """Lazy-init storage if not provided."""
        if self._storage is None:
            from meowcat.defaults.stores import InMemorySharedStore  # noqa: PLC0415
            self._storage = InMemorySharedStore()
        return self._storage

    def _cat_key(self, cat_uid: str, key: str) -> str:
        """Construct a cat-isolated storage key: ``cat_uid/key``.

        cat_uid prefix provides automatic isolation.
        """
        return f"{cat_uid}/{key}"

    async def storage_get(self, cat_uid: str, key: str) -> Any:
        """Cat reads from shared storage (auto cat_uid prefix isolation)."""
        return await self._ensure_storage().get(self._cat_key(cat_uid, key))

    async def storage_set(self, cat_uid: str, key: str, value: Any) -> None:
        """Cat writes to shared storage (auto cat_uid prefix isolation)."""
        await self._ensure_storage().set(self._cat_key(cat_uid, key), value)

    async def storage_delete(self, cat_uid: str, key: str) -> None:
        """Cat deletes a shared storage entry."""
        await self._ensure_storage().delete(self._cat_key(cat_uid, key))

    async def storage_list_keys(self, cat_uid: str) -> list[str]:
        """List all shared storage keys for a cat (prefix stripped)."""
        prefix = f"{cat_uid}/"
        all_keys = await self._ensure_storage().list_keys()
        return [
            k[len(prefix):] for k in all_keys if k.startswith(prefix)
        ]

    async def storage_watch(
        self, cat_uid: str, pattern: str,
    ) -> Any:
        """Watch shared storage key changes matching pattern.

        Delegates to the underlying storage.watch(). Returns AsyncIterator.
        """
        ns_pattern = f"{cat_uid}/{pattern}"
        # type: ignore[attr-defined]
        async for item in self._ensure_storage().watch(ns_pattern):
            yield item

    # -- Result delivery ---------------------------------------------

    async def deliver_result(
        self, parent_id: str, from_kitten: str, result: Any,
    ) -> None:
        """Kitten delivers result back to parent cat.

        Writes to shared storage ``{parent_id}/kitten:{from_kitten}/result``.

        Args:
            parent_id: Parent cat ID.
            from_kitten: Kitten ID.
            result: Arbitrary result to deliver.
        """
        key = f"kitten:{from_kitten}/result"
        await self.storage_set(parent_id, key, result)

    # -- Broadcast ----------------------------------------------------

    async def broadcast(self, event: str, **data: Any) -> None:
        """Broadcast an event to all cats in the colony (fire-and-forget).

        Args:
            event: Event name.
            **data: Event data.
        """
        for cat in self._cats.values():
            await cat.emit(event, data)

    async def broadcast_request(
        self,
        method: str,
        *,
        to_category: str = "brain",
        to_name: str = "amygdala",
        ignore_errors: bool = True,
        **kw: Any,
    ) -> dict[str, Any]:
        """Broadcast a request to all cats and collect responses (group chat).

        Calls ``method`` on ``to_category:to_name`` organ of every cat,
        collecting results keyed by cat_id. This is the 1→many request-response
        pattern — group chat where every cat responds.

        Unlike :meth:`broadcast` (fire-and-forget event), this method waits
        for all cats to respond and returns a result dict. Unlike
        :meth:`signal_between` (1→1 private chat), this sends to everyone.

        Bypasses cross-wiring (colony-level operation, not cat-to-cat).

        Usage::

            # Safety assessment — every cat weighs in
            results = await colony.broadcast_request(
                "assess_safety", sql="DROP TABLE users"
            )
            # → {"planner": {"safe": True}, "executor": {"safe": False}}

            # Custom organ target
            results = await colony.broadcast_request(
                "diagnose", to_category="brain", to_name="hippocampus"
            )

        Args:
            method: Method name to call on the target organ.
            to_category: Target organ category (default: ``"brain"``).
            to_name: Target organ name (default: ``"amygdala"``).
            ignore_errors: If True, cat errors become ``{"error": str(exc)}``
                in results. If False, re-raises the first exception.
            **kw: Keyword arguments forwarded to the target method.

        Returns:
            ``{cat_id: result, ...}`` — each cat's response keyed by cat_id.
            Cat errors become ``{"error": "..."}`` when ``ignore_errors=True``.
        """
        results: dict[str, Any] = {}
        for cat_id, cat in self._cats.items():
            try:
                organ = cat.organ(to_category, to_name)
                fn = getattr(organ, method)
                result = fn(**kw)
                import inspect as _inspect
                if _inspect.isawaitable(result):
                    result = await result
                results[cat_id] = result
            except Exception as exc:
                if not ignore_errors:
                    raise
                results[cat_id] = {"error": str(exc)}
        return results

    async def health_check_all(self) -> dict[str, dict]:
        """Run health check on all cats.

        Returns:
            ``{cat_id: {...diagnose...}, ...}``
        """
        results: dict[str, dict] = {}
        for cat_id, cat in self._cats.items():
            try:
                results[cat_id] = await cat.health_check()
            except Exception as exc:
                results[cat_id] = {"error": str(exc)}
        return results

    # -- Unified External Entry (v1.1.8) ------------------------------

    async def receive_external(self, address: str, **kwargs: Any) -> Any:
        """Receive external message addressed to a specific cat.

        This is the **unified external entry point** for a colony — any external
        system (CLI, HTTP, WebSocket, etc.) delivers messages through this method
        by specifying a cat address.

        Address format: ``colony_id/cat_id``, e.g. ``"feishu/planner"``.

        Usage::

        result = await colony.receive_external("feishu_planner", message="查询表结构")

        Args:
            address: Cat address in ``colony_id_cat_uid`` format.
            **kwargs: Message payload — forwarded to the target cat as an event.

        Returns:
            ``{"status": "delivered", "cat_id": ..., "cats_count": ...}``

        Raises:
            ValueError: Invalid address format or colony mismatch.
            KeyError: Target cat not found in colony.
        """
        parts = address.split("_", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"Invalid address '{address}': expected 'colony_id_cat_uid'"
            )
        colony_id, cat_uid = parts
        if colony_id != self.colony_id:
            raise ValueError(
                f"Address colony '{colony_id}' does not match "
                f"this colony '{self.colony_id}'"
            )
        cat = self.get_cat(cat_uid)
        await cat.emit("external_message", {"address": address, **kwargs})
        return {
            "status": "delivered",
            "cat_uid": cat_uid,
            "cats_count": len(self._cats),
        }

    def list_cat_capabilities(self) -> dict[str, list[dict[str, Any]]]:
        """List capabilities of every cat in the colony.

        Each cat's capabilities are its mounted organ coordinates
        ``(category, name)``.

        Usage::

            caps = colony.list_cat_capabilities()
            # → {"planner": [{"category": "brain", "name": "cerebrum"}, ...]}

        Returns:
            ``{cat_id: [{"category": ..., "name": ...}, ...], ...}``
        """
        result: dict[str, list[dict[str, Any]]] = {}
        for cat_id, cat in self._cats.items():
            organs = cat.list_all_organs()
            result[cat_id] = [
                {"category": c, "name": n} for c, n in organs
            ]
        return result

    def search_scope_guard(self, cat_uid: str, scope: str) -> None:
        """Validate search scope boundaries (v1.1.8).

        Enforces the search boundary contract defined in §2.2:

        - ``scope="self"``   → cat's own Hippocampus + public area (optional)
        - ``scope="colony"`` → SharedStorage ONLY, **never** other cats' private data

        Raises:
            ValueError: Invalid scope value.
            KeyError: Cat not found.
        """
        if scope not in ("self", "colony"):
            raise ValueError(
                f"Invalid search scope '{scope}': must be 'self' or 'colony'"
            )
        # Ensure cat exists
        if cat_uid not in self._cats:
            raise KeyError(
                f"Cat '{cat_uid}' not found in colony '{self.colony_id}'")

    # -- Inter-cat communication --------------------------------------

    async def signal_between(
        self,
        from_id: str,
        to_id: str,
        to_category: str,
        to_name: str,
        method: str,
        *args: Any,
        **kw: Any,
    ) -> Any:
        """Inter-cat signal communication.

        One cat sends a signal to another cat's organ via the colony.

        Flow:
        1. Validate cross-cat wiring (if cross_wiring is set)
        2. Retrieve target organ from target cat
        3. Directly invoke method on target organ

        Args:
            from_id: Sender cat ID.
            to_id: Receiver cat ID.
            to_category: Target organ category (e.g. "brain").
            to_name: Target organ name (e.g. "hippocampus").
            method: Target method name.
            *args, **kw: Forwarded to target method.

        Returns:
            Return value of target method.

        Raises:
            KeyError: Sender or receiver cat does not exist.
            IllegalNeuralPathError: Cross-cat edge is not allowed.
            OrganNotMountedError: Target organ does not exist.
        """
        # 1. Cross-cat wiring validation
        self._assert_cross_allowed(from_id, to_id)

        # 2. Get target cat
        target_cat = self._cats[to_id]

        # 3. Retrieve target organ
        target_organ = target_cat.organ(to_category, to_name)

        # 4. Invoke method
        fn = getattr(target_organ, method)
        import inspect as _inspect
        result = fn(*args, **kw)
        if _inspect.isawaitable(result):
            result = await result
        return result

    # -- Convenience methods ------------------------------------------

    @property
    def cat_count(self) -> int:
        """Number of cats in the colony."""
        return len(self._cats)

    # -- Shared Memory (v1.1.20) --------------------------------------

    @property
    def memory(self) -> "SharedMemoryPool":
        """Colony-level shared memory pool (lazy-init).

        Usage::

            await colony.memory.remember("用户喜欢 Python 3.12", {"cat": "planner"})
            results = await colony.memory.recall("Python 版本")
        """
        if self._memory_pool is None:
            from meowcat.colony.memory import SharedMemoryPool  # noqa: PLC0415
            self._memory_pool = SharedMemoryPool(self)
        return self._memory_pool

    # -- Collective Growth + Emergence (v1.1.22) -----------------------

    @property
    def growth(self) -> "CollectiveGrowth":
        """Colony-level collective growth (lazy-init).

        Usage::

            await colony.growth.record_anomaly("cat1", "DB schema mismatch")
            await colony.growth.record_correction("cat1", "DROP TABLE",
                                                    correct="DELETE WHERE id=...")
            anomalies = await colony.growth.list_anomalies()
        """
        if self._growth is None:
            from meowcat.biology.growth import CollectiveGrowth  # noqa: PLC0415
            self._growth = CollectiveGrowth(self)
        return self._growth

    @property
    def emergence(self) -> "CollectiveEmergence":
        """Colony-level collective role emergence (lazy-init).

        Usage::

            roles = await colony.emergence.detect_roles()
            await colony.emergence.record_pattern("cat1", "SQL审查",
                                                    evidence="发现3次SQL异常")
        """
        if self._emergence is None:
            from meowcat.biology.roles import CollectiveEmergence  # noqa: PLC0415
            self._emergence = CollectiveEmergence(self)
        return self._emergence


__all__ = ["Colony", "ColonyConfig", "ColonyOwner",
           "ColonyRules", "FederationTransport", "GlobalColonyRegistry"]
