"""meowcat 内置默认实现 — 开箱即用的参考实现。

全部零外部依赖（纯 Python dict/list），用于快速原型和测试。
生产环境请替换为 meowagent 或自定义的真实器官实现。
"""

from meowcat.defaults.factory import create_cat
from meowcat.defaults.organs import (
    NoopAmygdala,
    NoopCortex,
    NoopEars,
    NoopEyes,
    NoopFrontal,
    NoopHypothalamus,
    NoopMouth,
    NoopPurr,
    NoopTail,
    NoopWhiskers,
)
from meowcat.defaults.stores import InMemoryGraphStore, InMemoryL6Store

__all__ = [
    "create_cat",
    "NoopAmygdala", "NoopFrontal", "NoopHypothalamus", "NoopCortex",
    "NoopEars", "NoopEyes", "NoopMouth", "NoopPurr", "NoopTail", "NoopWhiskers",
    "InMemoryGraphStore", "InMemoryL6Store",
]
