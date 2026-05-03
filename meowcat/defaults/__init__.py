"""meowcat built-in default implementations — ready-to-use reference implementations.

All zero external dependencies (pure Python dict/list), for rapid prototyping and testing.
For production, replace with meowagent or custom real organ implementations.
"""
# (c) 2025-2026 Axonant. MIT License.


from meowcat.defaults.factory import create_cat
from meowcat.defaults.organs import (
    NoopAmygdala,
    NoopAnomalyGrowth,
    NoopBrainstem,
    NoopCerebellum,
    NoopCerebrum,
    NoopCorrectionGrowth,
    NoopCortex,
    NoopCrystallizer,
    NoopEars,
    NoopEyes,
    NoopFrontal,
    NoopHippocampus,
    NoopHypothalamus,
    NoopMouth,
    NoopPaws,
    NoopPurr,
    NoopRoleEmergence,
    NoopTail,
    NoopThalamus,
    NoopWhiskers,
)
from meowcat.defaults.stores import (
    InMemoryGraphStore,
    InMemoryL6Store,
    InMemorySharedStore,
    InMemoryVectorStore,
)

__all__ = [
    "create_cat",
    "NoopAmygdala", "NoopBrainstem", "NoopFrontal", "NoopHypothalamus", "NoopCortex",
    "NoopCerebrum", "NoopCerebellum",
    "NoopEars", "NoopEyes", "NoopMouth", "NoopPaws", "NoopPurr", "NoopTail", "NoopWhiskers",
    "NoopThalamus", "NoopHippocampus",
    # v1.0.16 Growth organs
    "NoopAnomalyGrowth", "NoopCorrectionGrowth", "NoopCrystallizer", "NoopRoleEmergence",
    "InMemoryGraphStore", "InMemoryL6Store",
    "InMemoryVectorStore", "InMemorySharedStore",
]
