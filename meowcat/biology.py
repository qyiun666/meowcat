"""meowcat biological default neural pathway table + default reflex arc paths.

Defines the default neuroanatomical structure of a "normal cat". App layer calls
``CatBase.wire_default_nervous_system()`` for one-click assembly.

**Biological anchors**:

- Senses relay through thalamus before entering the brain (basic mammalian principle)
- Brain does not directly connect to limbs — goes brain→cerebellum→muscles (motor cortex→cerebellum)
- Amygdala can bypass the brain and directly trigger effectors (stress reflex)
- Hypothalamus handles steady-state maintenance (decay/cleanup)
- Brainstem acts as the master dispatcher, connecting everything (bulbar crossroads)

**Forbidden edges** take priority over allowed edges:
- ``cerebrum → paws`` : brain does not directly connect to limbs
- ``cerebrum → mouth``: brain does not directly drive vocalization

**v0.5.10 pathway metadata**: each organ's in/out edges are centralized in ``ORGAN_SPECS``
as a single-source table; ``BUILTIN_NERVOUS_SYSTEM`` and ``ORGAN_PROTOCOLS`` are
auto-aggregated from this table. Adding/migrating organs only changes ``ORGAN_SPECS``,
preventing edge list drift.

This file has zero third-party dependencies, zero meowagent imports.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

# Coordinate constants re-exported from anatomy.py (public API paths unchanged)
from meowcat.anatomy import (
    AMYGDALA,
    ANOMALY_GROWTH,
    BRAIN,
    BRAIN_REGIONS,
    BRAINSTEM,
    CEREBELLUM,
    CEREBRUM,
    CORRECTION_GROWTH,
    CORTEX,
    CRYSTALLIZER,
    EARS,
    EFFECTORS,
    EYES,
    FRONTAL,
    GROWTH,
    HIPPOCAMPUS,
    HYPOTHALAMUS,
    ImplementationStyle,
    MOUTH,
    PAWS,
    PURR,
    ROLE_EMERGENCE,
    SENSE,
    SENSORS,
    STORAGE,
    TAIL,
    THALAMUS,
    VOICE,
    VOICES,
    WHISKERS,
)
from meowcat.wiring import Edge, Organ, Wiring

if TYPE_CHECKING:
    pass


# -- Organ spec table (single source of truth) ---------------------------------------

@dataclass(frozen=True)
class OrganSpec:
    """Anatomical spec for a single organ.

    Each record declares one organ:
    - ``coord``: organ coordinate (category, name)
    - ``protocol``: Protocol type for this coordinate (runtime validation)
    - ``in_edges``: inbound — who can call me (combined as ``(src, self) in BUILTIN``)
    - ``out_edges``: outbound — who I can call (combined as ``(self, dst) in BUILTIN``)
    - ``read_methods``: read-only method names declared by this organ (optional, for doc/audit)
    - ``write_methods``: write method names (triggers write permission check)
    - ``write_callers``: organs allowed to call write_methods (empty = write check disabled)
    - ``supported_styles``: 器官支持的实现风格 — 插头类型
      (algorithm / rule / model / hybrid). 开发者任选.

    器官 = 插槽(入口出口Protocol), 实现 = 插头(任选风格), 支持扩展.

    Method-level permissions enforced by ``Nervous.signal()`` after wiring check:
    ``from_organ not in write_callers`` raises ``IllegalNeuralPathError``.

    Adding/migrating organs only needs one record change; ``BUILTIN_NERVOUS_SYSTEM`` and
    ``ORGAN_PROTOCOLS`` sync automatically.
    """

    coord: Organ
    protocol: type
    in_edges: tuple[Organ, ...] = ()
    out_edges: tuple[Organ, ...] = ()
    read_methods: tuple[str, ...] = ()
    write_methods: tuple[str, ...] = ()
    write_callers: tuple[Organ, ...] = ()
    supported_styles: tuple[ImplementationStyle, ...] = ()


def _build_organ_specs() -> tuple[OrganSpec, ...]:
    """Build ORGAN_SPECS (lazy import protocols to avoid circular imports)."""
    from meowcat.protocols import (  # noqa: PLC0415
        AmygdalaProtocol,
        AnomalyGrowthProtocol,
        BrainStemProtocol,
        CorrectionGrowthProtocol,
        CortexProtocol,
        CrystallizerProtocol,
        EarsProtocol,
        EyesProtocol,
        FrontalCortexProtocol,
        HippocampusProtocol,
        HypothalamusProtocol,
        LLMBrainProtocol,
        MouthProtocol,
        OrganProtocol,
        PawsProtocol,
        PurrProtocol,
        RoleEmergenceProtocol,
        TailProtocol,
        ThalamusProtocol,
        WhiskersProtocol,
    )
    return (
        # -- Brain regions ----------------------------------------------
        OrganSpec(
            coord=THALAMUS, protocol=ThalamusProtocol,
            in_edges=SENSORS,                              # sensors → thalamus
            out_edges=(CEREBRUM, BRAINSTEM, AMYGDALA,
                       HIPPOCAMPUS),  # thalamus → cerebrum/brainstem/amygdala/hippocampus
            supported_styles=(
                ImplementationStyle.ALGORITHM, ImplementationStyle.RULE,
                ImplementationStyle.MODEL, ImplementationStyle.HYBRID,
            ),
        ),
        OrganSpec(
            coord=HIPPOCAMPUS, protocol=HippocampusProtocol,
            in_edges=(CEREBRUM, FRONTAL, HYPOTHALAMUS, BRAINSTEM),
            out_edges=(CEREBRUM, CORTEX),
            read_methods=(
                "entities", "episodes",
                "locate", "get_entity", "get_all", "get_by_name",
                "get_related", "stats", "fts_search", "to_dict",
            ),
            write_methods=(
                "remember", "add_entity", "add_episode",
                "connect", "decay", "weaken_connections",
                "cleanup_orphan_connections", "from_dict",
                "record_access", "set_dormant", "append_content",
                "update_importance", "set_last_seen",
            ),
            write_callers=(BRAINSTEM, HYPOTHALAMUS),
            supported_styles=(
                ImplementationStyle.ALGORITHM, ImplementationStyle.MODEL,
                ImplementationStyle.HYBRID,
            ),
        ),
        OrganSpec(
            coord=CEREBRUM, protocol=LLMBrainProtocol,
            in_edges=(THALAMUS, HIPPOCAMPUS, FRONTAL, BRAINSTEM),
            out_edges=(HIPPOCAMPUS, CEREBELLUM, FRONTAL),
            supported_styles=(
                ImplementationStyle.MODEL, ImplementationStyle.HYBRID,
            ),
        ),
        OrganSpec(
            coord=CEREBELLUM, protocol=LLMBrainProtocol,
            in_edges=(CEREBRUM, AMYGDALA, BRAINSTEM),
            out_edges=EFFECTORS,                           # paws/mouth/purr/tail
            supported_styles=(
                ImplementationStyle.MODEL, ImplementationStyle.ALGORITHM,
                ImplementationStyle.HYBRID,
            ),
        ),
        OrganSpec(
            coord=AMYGDALA, protocol=AmygdalaProtocol,
            in_edges=(THALAMUS, BRAINSTEM),
            out_edges=(CEREBELLUM, MOUTH, CEREBRUM,
                       ANOMALY_GROWTH, CORRECTION_GROWTH),
            supported_styles=(
                ImplementationStyle.ALGORITHM, ImplementationStyle.RULE,
                ImplementationStyle.MODEL, ImplementationStyle.HYBRID,
            ),
        ),
        OrganSpec(
            coord=FRONTAL, protocol=FrontalCortexProtocol,
            in_edges=(CEREBRUM, BRAINSTEM),
            out_edges=(CEREBRUM, HIPPOCAMPUS, BRAINSTEM),
            supported_styles=(
                ImplementationStyle.ALGORITHM, ImplementationStyle.MODEL,
                ImplementationStyle.HYBRID,
            ),
        ),
        OrganSpec(
            coord=HYPOTHALAMUS, protocol=HypothalamusProtocol,
            in_edges=(BRAINSTEM,),
            out_edges=(HYPOTHALAMUS, HIPPOCAMPUS,
                       CORTEX),  # includes self-loop
            supported_styles=(
                ImplementationStyle.ALGORITHM, ImplementationStyle.RULE,
            ),
        ),
        OrganSpec(
            coord=CORTEX, protocol=CortexProtocol,
            in_edges=(HIPPOCAMPUS, HYPOTHALAMUS, BRAINSTEM),
            out_edges=(),
            supported_styles=(
                ImplementationStyle.ALGORITHM, ImplementationStyle.MODEL,
                ImplementationStyle.HYBRID,
            ),
        ),
        OrganSpec(
            coord=BRAINSTEM, protocol=BrainStemProtocol,
            in_edges=(THALAMUS,),
            # master dispatch: to all brain regions (except self) / senses / voices; PAWS not included
            # (brainstem→paws edge absent from v0.5.9 golden set, SENSORS excludes PAWS)
            out_edges=(
                THALAMUS, HIPPOCAMPUS, CEREBRUM, CEREBELLUM,
                AMYGDALA, FRONTAL, HYPOTHALAMUS, CORTEX,
                ANOMALY_GROWTH, CORRECTION_GROWTH, CRYSTALLIZER, ROLE_EMERGENCE,
                *SENSORS, *VOICES,
            ),
            supported_styles=(
                ImplementationStyle.ALGORITHM, ImplementationStyle.RULE,
                ImplementationStyle.MODEL, ImplementationStyle.HYBRID,
            ),
        ),
        # -- Senses ----------------------------------------------
        OrganSpec(
            coord=EARS, protocol=EarsProtocol,
            in_edges=(), out_edges=(THALAMUS, AMYGDALA),
            supported_styles=(
                ImplementationStyle.ALGORITHM,
            ),
        ),
        OrganSpec(
            coord=EYES, protocol=EyesProtocol,
            in_edges=(), out_edges=(THALAMUS, AMYGDALA),
            supported_styles=(
                ImplementationStyle.ALGORITHM, ImplementationStyle.MODEL,
                ImplementationStyle.HYBRID,
            ),
        ),
        OrganSpec(
            coord=WHISKERS, protocol=WhiskersProtocol,
            in_edges=(), out_edges=(THALAMUS, AMYGDALA, ANOMALY_GROWTH),
            supported_styles=(
                ImplementationStyle.ALGORITHM, ImplementationStyle.MODEL,
                ImplementationStyle.HYBRID,
            ),
        ),
        # PAWS is an effector: only cerebellum→paws inbound (consistent with v0.5.9)
        OrganSpec(
            coord=PAWS, protocol=PawsProtocol,
            in_edges=(CEREBELLUM,), out_edges=(),
            supported_styles=(
                ImplementationStyle.ALGORITHM, ImplementationStyle.RULE,
                ImplementationStyle.HYBRID,
            ),
        ),
        # -- Voice (v1.0.7 completed Protocols)------------------------------
        OrganSpec(
            coord=MOUTH, protocol=MouthProtocol,
            in_edges=(CEREBELLUM, AMYGDALA, BRAINSTEM), out_edges=(),
            supported_styles=(
                ImplementationStyle.ALGORITHM,
            ),
        ),
        OrganSpec(
            coord=PURR, protocol=PurrProtocol,
            in_edges=(CEREBELLUM, BRAINSTEM), out_edges=(),
            supported_styles=(
                ImplementationStyle.ALGORITHM,
            ),
        ),
        OrganSpec(
            coord=TAIL, protocol=TailProtocol,
            in_edges=(CEREBELLUM, BRAINSTEM), out_edges=(),
            supported_styles=(
                ImplementationStyle.ALGORITHM,
            ),
        ),
        # -- Growth organs (v1.0.8 named protocols)-------------------
        OrganSpec(
            coord=ANOMALY_GROWTH, protocol=AnomalyGrowthProtocol,
            in_edges=(BRAINSTEM, AMYGDALA, WHISKERS),
            out_edges=(HIPPOCAMPUS, CORTEX),
            supported_styles=(
                ImplementationStyle.ALGORITHM, ImplementationStyle.MODEL,
                ImplementationStyle.HYBRID,
            ),
        ),
        OrganSpec(
            coord=CORRECTION_GROWTH, protocol=CorrectionGrowthProtocol,
            in_edges=(BRAINSTEM, AMYGDALA),
            out_edges=(HIPPOCAMPUS, CORTEX),
            supported_styles=(
                ImplementationStyle.ALGORITHM, ImplementationStyle.MODEL,
                ImplementationStyle.HYBRID,
            ),
        ),
        OrganSpec(
            coord=CRYSTALLIZER, protocol=CrystallizerProtocol,
            in_edges=(BRAINSTEM,), out_edges=(),
            supported_styles=(
                ImplementationStyle.ALGORITHM, ImplementationStyle.MODEL,
                ImplementationStyle.HYBRID,
            ),
        ),
        OrganSpec(
            coord=ROLE_EMERGENCE, protocol=RoleEmergenceProtocol,
            in_edges=(BRAINSTEM,), out_edges=(),
            supported_styles=(
                ImplementationStyle.ALGORITHM, ImplementationStyle.MODEL,
                ImplementationStyle.HYBRID,
            ),
        ),
    )


ORGAN_SPECS: Final[tuple[OrganSpec, ...]] = _build_organ_specs()
"""Complete organ anatomical spec table for a "normal cat".

When adding/migrating organs, only change one record in this table;
``BUILTIN_NERVOUS_SYSTEM`` and ``ORGAN_PROTOCOLS`` sync automatically.
"""


# -- Read-only views derived from ORGAN_SPECS --------------------------------

ORGAN_PROTOCOLS: Final[dict[Organ, type]] = {
    s.coord: s.protocol for s in ORGAN_SPECS if s.protocol is not None
}
"""Protocol type for each organ coordinate (aggregated from ORGAN_SPECS).

Read by ``CatBase._assemble()`` during auto-mount;
startup fails immediately if app-layer organ implementation does not satisfy Protocol.
"""


def _aggregate_edges() -> tuple[Edge, ...]:
    """Aggregate all default allowed edges from ORGAN_SPECS (dedup + stable sort)."""
    edges: set[Edge] = set()
    for s in ORGAN_SPECS:
        for src in s.in_edges:
            edges.add((src, s.coord))
        for dst in s.out_edges:
            edges.add((s.coord, dst))
    return tuple(sorted(edges))


BUILTIN_NERVOUS_SYSTEM: Final[tuple[Edge, ...]] = _aggregate_edges()
"""Default allowed edge list for a "normal cat" (aggregated from ORGAN_SPECS)."""


# -- Forbidden edges (engineering guardrails, explicitly hardcoded, not via OrganSpec) ---------------

FORBIDDEN_PATHS: Final[tuple[Edge, ...]] = (
    # cerebrum should not produce side effects. All side effects funneled through cerebellum→effectors,
    # for audit/intercept/mock
    (CEREBRUM, PAWS),
    # cerebrum should not directly drive vocalization. All side effects funneled through cerebellum→effectors
    (CEREBRUM, MOUTH),
    # v1.0.8: cerebrum does not directly connect to growth organs. Growth is a side effect, routed through cerebellum or brainstem
    (CEREBRUM, ANOMALY_GROWTH),
    (CEREBRUM, CORRECTION_GROWTH),
)
"""Default forbidden pathway list (higher priority than allowed edges)."""


# -- Assembly function ----------------------------------------------------

def apply_default_wiring(wiring: Wiring) -> None:
    """Wire the default neuroanatomy onto the wiring.

    Does not freeze; caller (typically ``CatBase.freeze_nervous_system``) decides timing.
    Can be called repeatedly; edge set naturally deduplicates.
    """
    wiring.connect_many(BUILTIN_NERVOUS_SYSTEM)
    wiring.forbid_many(FORBIDDEN_PATHS)


__all__ = [
    # category constants (re-export from anatomy)
    "BRAIN", "SENSE", "VOICE", "STORAGE", "GROWTH",
    # organ coordinates (re-export from anatomy)
    "THALAMUS", "HIPPOCAMPUS", "CEREBRUM", "CEREBELLUM", "AMYGDALA",
    "FRONTAL", "HYPOTHALAMUS", "CORTEX", "BRAINSTEM",
    "EARS", "EYES", "WHISKERS", "PAWS",
    "ANOMALY_GROWTH", "CORRECTION_GROWTH",
    "CRYSTALLIZER", "ROLE_EMERGENCE",
    "MOUTH", "PURR", "TAIL",

    "SENSORS", "VOICES", "EFFECTORS", "BRAIN_REGIONS",
    # v0.5.10 Organ spec table
    "OrganSpec", "ORGAN_SPECS",
    # table + assembly function
    "BUILTIN_NERVOUS_SYSTEM", "FORBIDDEN_PATHS",
    "ORGAN_PROTOCOLS",
    "apply_default_wiring",


]
