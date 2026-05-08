# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat neural pathway graph (Wiring) — cat's neuroanatomical constraints.

Wiring is a **directed graph + blocklist** declaring which inter-organ calls are legal.
``CatBase.signal(from, to, method, ...)`` consults this graph before dispatching;
illegal calls raise :class:`IllegalNeuralPathError`.

Design points:

- **Node** = ``(category, name)`` pair, e.g. ``("brain", "cerebellum")``
- **Edge** = allows A to call B (direction-sensitive; bidirectional needs two edges)
- **Blocklist** takes priority over allowlist: even with connect, a forbid hit immediately denies
- **Freeze** after freeze, any write raises :class:`MeowCatError`, preventing runtime tampering

This file has zero third-party dependencies, pure stdlib.
"""

from __future__ import annotations

from collections.abc import Iterable

from meowcat.errors import IllegalNeuralPathError, MeowCatError

# (category, name) e.g. ("brain","cerebellum"), ("sense","paws")
Organ = tuple[str, str]
Edge = tuple[Organ, Organ]


class Wiring:
    """Neural pathway directed graph (with blocklist).

    Typical usage::

        w = Wiring()
        w.connect(("brain", "cerebellum"), ("sense", "paws"))
        w.forbid(("brain", "cerebrum"), ("sense", "paws"))
        w.freeze()
        assert w.is_allowed(("brain", "cerebellum"), ("sense", "paws"))
        w.assert_allowed(("brain", "cerebrum"), ("sense", "paws"))
        # raises IllegalNeuralPathError
    """

    def __init__(self) -> None:
        self._allowed: set[Edge] = set()
        self._forbidden: set[Edge] = set()
        self._frozen: bool = False
        # v1.2.15: organ→edges reverse index for O(1) is_organ_wired lookup
        self._organ_index: dict[Organ, set[Edge]] = {}

    # -- Write API ------------------------------------------------------

    def connect(self, from_organ: Organ, to_organ: Organ) -> None:
        """Declare an "allow from→to" pathway.

        Repeated connect is idempotent. If the edge is already blocklisted, the current
        implementation does **not error** — it only records the allowlist entry;
        queries always honor the blocklist (permanently denied).
        """
        self._ensure_mutable()
        _validate_organ(from_organ, "from_organ")
        _validate_organ(to_organ, "to_organ")
        edge: Edge = (from_organ, to_organ)
        self._allowed.add(edge)
        self._organ_index.setdefault(from_organ, set()).add(edge)
        self._organ_index.setdefault(to_organ, set()).add(edge)

    def forbid(self, from_organ: Organ, to_organ: Organ) -> None:
        """Declare a "forbid from→to" pathway. Takes priority over connect."""
        self._ensure_mutable()
        _validate_organ(from_organ, "from_organ")
        _validate_organ(to_organ, "to_organ")
        edge: Edge = (from_organ, to_organ)
        self._forbidden.add(edge)
        # edge stays in _organ_index (it tracks allowed edges), is_organ_wired filters by forbidden

    def freeze(self) -> None:
        """Freeze the graph. Subsequent connect / forbid raise :class:`MeowCatError`."""
        self._frozen = True

    # -- Query API ----------------------------------------------------

    def is_allowed(self, from_organ: Organ, to_organ: Organ) -> bool:
        """Can A call B? Blocklist > allowlist."""
        edge: Edge = (from_organ, to_organ)
        if edge in self._forbidden:
            return False
        return edge in self._allowed

    def assert_allowed(
        self,
        from_organ: Organ,
        to_organ: Organ,
    ) -> None:
        """Raise :class:`IllegalNeuralPathError` if not allowed."""
        edge: Edge = (from_organ, to_organ)
        if edge in self._forbidden:
            raise IllegalNeuralPathError(
                from_organ,
                to_organ,
                reason="forbidden by wiring",
            )
        if edge not in self._allowed:
            raise IllegalNeuralPathError(
                from_organ,
                to_organ,
                reason="not connected in wiring",
            )

    @property
    def frozen(self) -> bool:
        """Whether wiring is frozen."""
        return self._frozen

    # -- Introspection (read-only) -----------------------------------------------

    def edges(self) -> frozenset[Edge]:
        """Immutable snapshot of all currently allowed edges."""
        return frozenset(self._allowed)

    def forbids(self) -> frozenset[Edge]:
        """Immutable snapshot of all currently forbidden edges."""
        return frozenset(self._forbidden)

    def is_organ_wired(self, organ: Organ) -> bool:
        """Whether the organ appears in any allowed edge (as source or target)."""
        edges = self._organ_index.get(organ)
        if not edges:
            return False
        return any(e not in self._forbidden for e in edges)

    def snapshot(self) -> WiringSnapshot:
        """Return an immutable view of the current graph, for frozen reads during reflex execution."""
        return WiringSnapshot(
            allowed=frozenset(self._allowed),
            forbidden=frozenset(self._forbidden),
        )

    # -- Convenience methods ----------------------------------------------------

    def connect_many(self, edges: Iterable[Edge]) -> None:
        """Batch register allowed edges."""
        for frm, to in edges:
            self.connect(frm, to)

    def forbid_many(self, edges: Iterable[Edge]) -> None:
        """Batch register forbidden edges."""
        for frm, to in edges:
            self.forbid(frm, to)

    # -- Internal --------------------------------------------------------

    def _ensure_mutable(self) -> None:
        if self._frozen:
            raise MeowCatError(
                "Wiring is frozen; call freeze() happens only after assembly",
            )


class WiringSnapshot:
    """Immutable snapshot of Wiring (read-only view)."""

    __slots__ = ("_allowed", "_forbidden")

    def __init__(
        self,
        allowed: frozenset[Edge],
        forbidden: frozenset[Edge],
    ) -> None:
        self._allowed = allowed
        self._forbidden = forbidden

    def is_allowed(self, from_organ: Organ, to_organ: Organ) -> bool:
        edge: Edge = (from_organ, to_organ)
        if edge in self._forbidden:
            return False
        return edge in self._allowed

    @property
    def allowed(self) -> frozenset[Edge]:
        return self._allowed

    @property
    def forbidden(self) -> frozenset[Edge]:
        return self._forbidden


def _validate_organ(organ: Organ, label: str) -> None:
    """Assert organ is a ``(str, str)`` pair."""
    if (
        not isinstance(organ, tuple)
        or len(organ) != 2
        or not all(isinstance(x, str) and x for x in organ)
    ):
        raise ValueError(
            f"{label} must be (category:str, name:str), got {organ!r}",
        )


__all__ = ["Wiring", "WiringSnapshot", "Organ", "Edge"]
