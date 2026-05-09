# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

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

**v1.1.22**: biology package also contains collective growth (:mod:`meowcat.biology.growth`)
and role emergence (:mod:`meowcat.biology.roles`) modules for colony-level intelligence.

This file has zero third-party dependencies, zero meowagent imports.
"""

from __future__ import annotations

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

# v1.1.22: colony-level collective intelligence (lazy, see __getattr__)
# v1.1.23: cat's private scratchpad (lazy)
# v1.1.24: insight organ + fusion strategies (lazy)
# v1.1.25: Cortex worldview L1 (lazy)
# v1.1.26: active growth (lazy)
# v1.1.27: metacognition L3 (lazy)
# v1.2.0: unified self + three default closed loops (lazy)


# v1.2.15: lazy submodule imports — these names are resolved on first access
# to avoid eager-importing cat_self, pineal_gland, cortex, etc. when only OrganSpec is needed.
_LAZY_BIOLOGY: dict[str, str] = {
    # v1.1.22 colony-level collective intelligence
    "CollectiveGrowth": "meowcat.biology.growth",
    "CollectiveEmergence": "meowcat.biology.growth",
    # v1.1.23 scribble pad
    "ScribblePad": "meowcat.biology.scribble_pad",
    "DefaultScribbleFilter": "meowcat.biology.scribble_pad",
    "DefaultScribbleLogger": "meowcat.biology.scribble_pad",
    "DefaultScribblePersister": "meowcat.biology.scribble_pad",
    # v1.1.24 pineal gland
    "PinealGland": "meowcat.biology.pineal_gland",
    "Insight": "meowcat.biology.pineal_gland",
    "DefaultMerger": "meowcat.biology.pineal_gland",
    "DefaultContradiction": "meowcat.biology.pineal_gland",
    "DefaultInsightFilter": "meowcat.biology.pineal_gland",
    # v1.1.25 cortex worldview L1
    "Cortex": "meowcat.biology.cortex",
    "DefaultRuleExtractor": "meowcat.biology.cortex",
    # v1.1.26 active growth
    "BlindSpotDetector": "meowcat.biology.active_growth",
    "ToolFailureLearner": "meowcat.biology.active_growth",
    "HotPathObserver": "meowcat.biology.active_growth",
    "ActiveGrowthPack": "meowcat.biology.active_growth_pack",
    # v2.0 CatSelf + unified ReflectionLoop
    "CatSelf": "meowcat.biology.cat_self",
    "SelfSnapshot": "meowcat.biology.cat_self",
    "ReflectionLoop": "meowcat.biology.cat_self_loops",
}


def __getattr__(name: str):
    """Lazy-load biology submodules on first access."""
    if name in _LAZY_BIOLOGY:
        import importlib

        mod = importlib.import_module(_LAZY_BIOLOGY[name])
        attr = getattr(mod, name)
        # Cache in module globals so subsequent access is direct
        globals()[name] = attr
        return attr
    raise AttributeError(f"module 'meowcat.biology' has no attribute {name!r}")


# -- Organ spec table re-exported from biology.organ_spec (v1.3.9 T-05) -----------

from meowcat.biology.organ_spec import (  # noqa: E402, F401 — re-export for public API
    BUILTIN_NERVOUS_SYSTEM,
    FORBIDDEN_PATHS,
    ORGAN_PROTOCOLS,
    ORGAN_SPECS,
    OrganSpec,
    _aggregate_edges,
    apply_default_wiring,
)

__all__ = [
    # category constants (re-export from anatomy)
    "BRAIN",
    "SENSE",
    "VOICE",
    "STORAGE",
    "GROWTH",
    # organ coordinates (re-export from anatomy)
    "THALAMUS",
    "HIPPOCAMPUS",
    "CEREBRUM",
    "CEREBELLUM",
    "AMYGDALA",
    "FRONTAL",
    "HYPOTHALAMUS",
    "CORTEX",
    "BRAINSTEM",
    "EARS",
    "EYES",
    "WHISKERS",
    "PAWS",
    "ANOMALY_GROWTH",
    "CORRECTION_GROWTH",
    "CRYSTALLIZER",
    "ROLE_EMERGENCE",
    "MOUTH",
    "PURR",
    "TAIL",
    "SENSORS",
    "VOICES",
    "EFFECTORS",
    "BRAIN_REGIONS",
    # v0.5.10 Organ spec table
    "OrganSpec",
    "ORGAN_SPECS",
    # table + assembly function
    "BUILTIN_NERVOUS_SYSTEM",
    "FORBIDDEN_PATHS",
    "ORGAN_PROTOCOLS",
    "apply_default_wiring",
    # v1.1.22 colony-level collective intelligence
    "CollectiveGrowth",
    "CollectiveEmergence",
    # v1.1.23 scribble pad
    "ScribblePad",
    "DefaultScribbleFilter",
    "DefaultScribbleLogger",
    "DefaultScribblePersister",
    # v1.1.24 pineal gland
    "PinealGland",
    "Insight",
    "DefaultMerger",
    "DefaultContradiction",
    "DefaultInsightFilter",
    # v1.1.25 cortex worldview L1
    "Cortex",
    "DefaultRuleExtractor",
    # v1.1.26 active growth
    "BlindSpotDetector",
    "ToolFailureLearner",
    "HotPathObserver",
    "ActiveGrowthPack",
    # v2.0 CatSelf + unified ReflectionLoop
    "CatSelf",
    "SelfSnapshot",
    "ReflectionLoop",
]
