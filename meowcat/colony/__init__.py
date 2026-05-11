# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat Colony — Cat container (v2.0 simplified).

Colony manages peer-to-peer collaboration + shared storage for multiple cats.
Cats created in a colony are automatically registered and share storage.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from meowcat.assembly import CatBase
from meowcat.colony.cat_ops import _CatOpsMixin
from meowcat.colony.communication import _CommunicationMixin
from meowcat.colony.config import ColonyConfig, ColonyOwner
from meowcat.colony.namespace import _NamespaceMixin
from meowcat.colony.persona_mgr import _PersonaMixin
from meowcat.colony.rules import ColonyRules
from meowcat.errors import IllegalNeuralPathError
from meowcat.models import ModelConfig
from meowcat.pluggable import Pluggable
from meowcat.storage import SharedStore

if TYPE_CHECKING:
    from meowcat.biology.growth import CollectiveEmergence, CollectiveGrowth
    from meowcat.colony.memory import SharedMemoryPool

logger = logging.getLogger("meowcat.colony")


class Colony(
    Pluggable,
    _NamespaceMixin,
    _CatOpsMixin,
    _CommunicationMixin,
    _PersonaMixin,
):
    """Cat container — manages peer-to-peer collaboration + shared storage.

    Typical usage::

        from meowcat import Colony

        colony = Colony("my-colony", storage=InMemorySharedStore(), name="客服组")
        colony = Colony.default("my-team")  # quick setup with defaults

        # Create cats (auto-register + shared storage)
        cat_a = colony.create_cat(name="analyst")
        cat_b = colony.create_cat(name="executor")

        # Inter-cat communication
        result = await colony.signal_between(
            "01", "02", "brain", "hippocampus", "locate",
            query="hello",
        )

        # Broadcast
        results = await colony.broadcast("health_check")
    """

    def __init__(
        self,
        colony_id: str | None = None,
        storage: SharedStore | None = None,
        *,
        name: str | None = None,
        description: str = "",
        max_cats: int | None = None,
        region: str = "",
        model_shelf: dict[str, ModelConfig] | None = None,
        owner: ColonyOwner | None = None,
        rules: ColonyRules | None = None,
        cross_wiring_allowed: set[tuple[str, str]] | None = None,
        cross_wiring_forbidden: set[tuple[str, str]] | None = None,
    ) -> None:
        """Construct a cat container.

        Args:
            colony_id: Unique identifier for the colony.
                ``None`` = auto-generate (``CALL_SIGN + base36(timestamp)``,
                12 chars).  Pass a string to override.
            storage: Shared storage instance (satisfying SharedStore).
                None = auto-create InMemorySharedStore.
            name: Human-readable colony name. Defaults to colony_id.
            description: Colony description.
            max_cats: Maximum number of cats, None = unlimited.
            region: Deployment region (e.g. "us-east", "cn-beijing").
            model_shelf: Shared model shelf — named model configs cats can pick from.
                None = empty shelf; cats must bring their own LLM.
            owner: Colony owner profile (name/email/language). Defaults to empty.
            rules: Colony rules (safety/approval/rate-limit). Defaults to permissive.
            cross_wiring_allowed: Cross-cat allowlist edges. None = deny all cross-cat signals.
            cross_wiring_forbidden: Cross-cat blocklist edges. Takes priority over allowlist.
        """
        Pluggable.__init__(self)
        if colony_id is None:
            colony_id = Colony._generate_colony_uid()
        self.colony_id = colony_id
        self._name = name or colony_id
        self._description = description
        self._max_cats = max_cats
        self.region = region
        self._colony_uid = colony_id
        self._cat_counter: int = 0
        self._storage = storage  # type: ignore[assignment]
        self._model_shelf: dict[str, ModelConfig] = dict(model_shelf or {})
        self._cats: dict[str, CatBase] = {}
        self._cross_allowed: set[tuple[str, str]
                                 ] = cross_wiring_allowed or set()
        self._cross_forbidden: set[tuple[str, str]
                                   ] = cross_wiring_forbidden or set()
        self._has_cross_wiring = (
            cross_wiring_allowed is not None or cross_wiring_forbidden is not None
        )
        self._owner = owner or ColonyOwner()
        self._rules = rules or ColonyRules()
        self._registered_ns: set[str] = {"owner", "knowledge", "cats", "personas"}
        # -- Shared Memory (lazy) -----------------------------------------
        self._memory_pool: SharedMemoryPool | None = None
        # -- Collective Growth (lazy) -------------------------------------
        self._growth: CollectiveGrowth | None = None
        # -- Collective Emergence (lazy, merged in T-03) ------------------
        self._emergence: CollectiveEmergence | None = None
        # -- Task results (internal) -------------------------------------
        self._task_results: dict[str, Any] = {}

    # -- UID generation -----------------------------------------------

    @staticmethod
    def _base36(n: int) -> str:
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
        from meowcat.constants import CALL_SIGN
        return f"{CALL_SIGN}{Colony._base36(int(time.time()))}"

    def _next_cat_uid(self) -> str:
        self._cat_counter += 1
        return f"{self._cat_counter:02d}"

    # -- Nameplate properties ------------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        old = self._name
        self._name = value
        for _hook, _r in self._run_plugs_sync("on_name_change", old, value):
            pass

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str) -> None:
        self._description = value

    @property
    def max_cats(self) -> int | None:
        return self._max_cats

    @property
    def colony_uid(self) -> str:
        return self._colony_uid

    @property
    def is_full(self) -> bool:  # type: ignore[override]
        if self._max_cats is None:
            return False
        return len(self._cats) >= self._max_cats

    # -- Owner / Rules ---------------------------------------

    @property
    def owner(self) -> ColonyOwner:
        return self._owner

    @owner.setter
    def owner(self, value: ColonyOwner) -> None:
        self._owner = value

    @property
    def rules(self) -> ColonyRules:
        return self._rules

    # -- Model shelf (v2.0) ---------------------------------------

    @property
    def model_shelf(self) -> dict[str, ModelConfig]:
        return dict(self._model_shelf)

    def stock_model(self, name: str, config: ModelConfig) -> None:
        self._model_shelf[name] = config

    def unstock_model(self, name: str) -> bool:
        return self._model_shelf.pop(name, None) is not None

    def pick_model(self, name: str | None = None) -> ModelConfig:
        if name is not None:
            if name not in self._model_shelf:
                raise KeyError(
                    f"Model '{name}' not found on shelf. "
                    f"Available: {list(self._model_shelf.keys())}"
                )
            return self._model_shelf[name]
        if not self._model_shelf:
            raise ValueError(
                f"Model shelf is empty in colony '{self.colony_id}'."
            )
        return next(iter(self._model_shelf.values()))

    # -- Pluggable aliases ---------------------------------------------

    def plug(self, slot: str, handler: Any) -> None:
        self.mount_plug(slot, handler)

    def unplug(self, slot: str, handler: Any | None = None) -> None:
        self.unmount_plug(slot, handler)

    # -- Factory -------------------------------------------------------

    @classmethod
    def default(cls, colony_id: str, **kwargs: Any) -> Colony:
        from meowcat.defaults.stores import InMemorySharedStore

        storage = kwargs.pop("storage", InMemorySharedStore())
        name = kwargs.pop("name", None) or colony_id
        return cls(colony_id, storage=storage, name=name, **kwargs)

    # -- Cross-cat wiring ---------------------------------------------

    def allow_cross(self, from_cat: str, to_cat: str) -> None:
        self._cross_allowed.add((from_cat, to_cat))
        self._has_cross_wiring = True

    def forbid_cross(self, from_cat: str, to_cat: str) -> None:
        self._cross_forbidden.add((from_cat, to_cat))
        self._has_cross_wiring = True

    def _assert_cross_allowed(self, from_id: str, to_id: str) -> None:
        # Forbidden takes priority — always block if edge is in blocklist
        if (from_id, to_id) in self._cross_forbidden:
            raise IllegalNeuralPathError(
                ("colony", from_id),
                ("colony", to_id),
                reason=f"cross-cat signal forbidden: {from_id} → {to_id}",
            )
        # Default-deny: only allow edges explicitly registered in the allowlist
        if (from_id, to_id) not in self._cross_allowed:
            raise IllegalNeuralPathError(
                ("colony", from_id),
                ("colony", to_id),
                reason=f"cross-cat signal not allowed: {from_id} → {to_id}",
            )

    # -- Convenience methods ------------------------------------------

    @property
    def cat_count(self) -> int:
        return len(self._cats)

    # -- Shared Memory --------------------------------------

    @property
    def memory(self):
        if self._memory_pool is None:
            from meowcat.colony.memory import SharedMemoryPool
            self._memory_pool = SharedMemoryPool(self)
        return self._memory_pool

    # -- Collective Growth ---------------------------------------

    @property
    def growth(self) -> CollectiveGrowth:
        if self._growth is None:
            from meowcat.biology.growth import CollectiveGrowth
            self._growth = CollectiveGrowth(self)
        return self._growth

    @property
    def emergence(self) -> CollectiveEmergence:
        if self._emergence is None:
            from meowcat.biology.growth import CollectiveEmergence
            self._emergence = CollectiveEmergence(self)
        return self._emergence


__all__ = [
    "Colony",
    "ColonyConfig",
    "ColonyOwner",
    "ColonyRules",
]
