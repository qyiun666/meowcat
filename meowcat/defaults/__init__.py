"""meowcat built-in default implementations — ready-to-use reference implementations.

All zero external dependencies (pure Python dict/list), for rapid prototyping and testing.
For production, replace with meowagent or custom real organ implementations.
"""
# (c) 2025-2026 Axonant. MIT License.


from meowcat.defaults.factory import create_cat
from meowcat.defaults.organs import (
    NoopAmygdala,
    NoopBrainstem,
    NoopCortex,
    NoopEars,
    NoopEyes,
    NoopFrontal,
    NoopHippocampus,
    NoopHypothalamus,
    NoopMouth,
    NoopPaws,
    NoopPurr,
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
    "NoopEars", "NoopEyes", "NoopMouth", "NoopPaws", "NoopPurr", "NoopTail", "NoopWhiskers",
    "NoopThalamus", "NoopHippocampus",
    "InMemoryGraphStore", "InMemoryL6Store",
    "InMemoryVectorStore", "InMemorySharedStore",
]
