# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat stethoscope — full-body checkup tool.

Iterates all mounted organs, calls ``diagnose()`` to aggregate snapshots.
Only depends on :class:`OrganHost` + :class:`Diagnosable` protocol, zero meowagent imports.

Usage::

    from meowcat.diagnose import Stethoscope

    health = await Stethoscope.probe_all(cat)
    brain = await Stethoscope.probe_category(cat, "brain")
    hippo = await Stethoscope.probe_organ(cat, "brain", "hippocampus")
"""

from __future__ import annotations

from typing import Any

from meowcat.host import OrganHost
from meowcat.wiring import Edge, Organ, Wiring


def render_wiring(
    wiring: Wiring,
    format: str = "mermaid",
    *,
    organs: frozenset[Organ] | None = None,
) -> str:
    """Generate a visual representation of the wiring graph.

    Args:
        wiring: Wiring instance
        format: Output format, ``"mermaid"`` or ``"dot"``
        organs: Known organ set, used to mark isolated nodes (optional)

    Returns:
        Graph description string in mermaid or dot format.
        - Allowed edges: solid arrows
        - Forbidden edges: red dashed
        - Isolated nodes (if organs provided): gray

    Raises:
        ValueError: format is not ``"mermaid"`` or ``"dot"``

    Examples:

        >>> print(render_wiring(cat.wiring))
        >>> print(render_wiring(cat.wiring, format="dot"))
    """
    if format not in ("mermaid", "dot"):
        raise ValueError(f"Unknown format '{format}', expected 'mermaid' or 'dot'")

    allowed = wiring.edges()
    forbidden = wiring.forbids()

    # collect all nodes from edges
    nodes: set[Organ] = set()
    for frm, to in allowed | forbidden:
        nodes.add(frm)
        nodes.add(to)

    # if organs provided, add isolated nodes
    if organs is not None:
        nodes |= organs

    # node → short ID mapping (mermaid/dot need valid identifiers)
    node_ids: dict[Organ, str] = {}
    for i, organ in enumerate(sorted(nodes)):
        node_ids[organ] = f"n{i}"

    # isolated nodes = nodes in organs but not in any edge
    connected: set[Organ] = set()
    for frm, to in allowed | forbidden:
        connected.add(frm)
        connected.add(to)
    isolated = nodes - connected if organs is not None else set()

    if format == "mermaid":
        return _render_mermaid(node_ids, allowed, forbidden, isolated)
    return _render_dot(node_ids, allowed, forbidden, isolated)


def _render_mermaid(
    node_ids: dict[Organ, str],
    allowed: frozenset[Edge],
    forbidden: frozenset[Edge],
    isolated: set[Organ],
) -> str:
    lines = ["graph LR"]

    # node declarations
    for organ, nid in sorted(node_ids.items(), key=lambda x: x[1]):
        label = f"{organ[0]}:{organ[1]}"
        lines.append(f'    {nid}("{label}")')

    # allowed edges
    for _i, (frm, to) in enumerate(sorted(allowed)):
        lines.append(f"    {node_ids[frm]} --> {node_ids[to]}")

    # forbidden edges
    for _i, (frm, to) in enumerate(sorted(forbidden)):
        lines.append(f"    {node_ids[frm]} -.->|✗| {node_ids[to]}")

    # isolated node styles
    for organ in sorted(isolated):
        lines.append(f"    style {node_ids[organ]} fill:#ddd,stroke:#999")

    return "\n".join(lines)


def _render_dot(
    node_ids: dict[Organ, str],
    allowed: frozenset[Edge],
    forbidden: frozenset[Edge],
    isolated: set[Organ],
) -> str:
    lines = ["digraph Wiring {", "    rankdir=LR;"]

    # node declarations
    for organ, nid in sorted(node_ids.items(), key=lambda x: x[1]):
        label = f"{organ[0]}:{organ[1]}"
        # isolated nodes gray
        if organ in isolated:
            lines.append(f'    {nid} [label="{label}", style=filled, fillcolor="#ddd"];')
        else:
            lines.append(f'    {nid} [label="{label}"];')

    # allowed edges
    for frm, to in sorted(allowed):
        lines.append(f"    {node_ids[frm]} -> {node_ids[to]};")

    # forbidden edges
    for frm, to in sorted(forbidden):
        lines.append(f'    {node_ids[frm]} -> {node_ids[to]} [color=red, style=dashed, label="✗"];')

    lines.append("}")
    return "\n".join(lines)


class Stethoscope:
    """Full-body checkup tool -- iterates all mounted organs, calls diagnose() to aggregate."""

    @staticmethod
    async def probe_all(cat) -> dict[str, dict[str, Any]]:
        """Iterate all mounted organs, returns ``{organ_key: diagnose_snapshot}``.

        Args:
            cat: ``CatBase`` or instance with ``_host`` attribute

        Returns:
            ``{"brain:hippocampus": {...}, "sense:ears": {...}, ...}``
            organs that fail diagnosis get ``{"error": str(exc)}``
        """
        host: OrganHost = cat.host
        result: dict[str, dict[str, Any]] = {}
        for category, name in host.list_all_organs():
            key = f"{category}:{name}"
            try:
                result[key] = await cat.probe((category, name))
            except Exception as e:
                result[key] = {"error": str(e)}
        return result

    @staticmethod
    async def probe_category(cat, category: str) -> dict[str, dict[str, Any]]:
        """Probe by category: only ``brain`` / ``sense`` / ``voice`` / ``growth``.

        Args:
            cat: ``CatBase`` instance
            category: organ category name

        Returns:
            ``{"hippocampus": {...}, "cerebrum": {...}}`` (category prefix omitted)
        """
        host: OrganHost = cat.host
        result: dict[str, dict[str, Any]] = {}
        for cat_name, _instance in host.organs(category).items():
            key = cat_name  # omit category prefix
            try:
                result[key] = await cat.probe((category, cat_name))
            except Exception as e:
                result[key] = {"error": str(e)}
        return result

    @staticmethod
    async def probe_organ(cat, category: str, name: str) -> dict[str, Any]:
        """Probe a single organ.

        Args:
            cat: ``CatBase`` instance
            category: organ category name
            name: organ name

        Returns:
            single organ ``diagnose()`` dict snapshot
        """
        return await cat.probe((category, name))


__all__ = ["Stethoscope", "render_wiring"]
