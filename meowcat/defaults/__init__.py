"""meowcat 内置默认实现 — 开箱即用的参考实现。

全部零外部依赖（纯 Python dict/list），用于快速原型和测试。
生产环境请替换为 meowagent 或自定义的真实器官实现。
"""

from meowcat.defaults.factory import create_cat
from meowcat.defaults.organs import (
    NoopAmygdala,
    NoopBrainstem,
    NoopCortex,
    NoopEars,
    NoopEyes,
    NoopFrontal,
    NoopHypothalamus,
    NoopMouth,
    NoopPaws,
    NoopPurr,
    NoopTail,
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
    "InMemoryGraphStore", "InMemoryL6Store",
    "InMemoryVectorStore", "InMemorySharedStore",
]
