"""meowcat 三大闭环事件名常量表。

对应 ``docs/架构/00-架构全景-闭环模块链路总图.md`` 定义的三大闭环：

- **闭环 A（记→找→给 核心回路）**：每轮对话的定位/路由/记忆/压缩钩子
- **闭环 B（编排）**：TaskOrchestrator 的开始/结束钩子
- **闭环 C（生长结晶）**：异常/校正/结晶/角色涌现钩子

另外附带 :class:`Lifecycle` 记录 Cat 本身的开合机事件。

**纪律**：本文件只定义字符串常量，不含业务实现，零第三方依赖。
"""

from __future__ import annotations

from typing import Final


# -- 闭环 A：记→找→给 核心回路 ----------------------------------

class LocateEvent:
    """丘脑检索（找）相关钩子。"""

    PRE: Final[str] = "locate.pre"
    """在 Thalamus.locate() 执行前触发，载荷 ``{msg, session_id}``。"""

    POST: Final[str] = "locate.post"
    """Thalamus.locate() 返回后触发，载荷 ``{msg, result}``。"""

    ROUTE_DECIDED: Final[str] = "route.decided"
    """路由判定完成触发，载荷 ``{route, confidence}``。"""


class RememberEvent:
    """海马体写入（记）+ 下丘脑压缩相关钩子。"""

    PRE: Final[str] = "remember.pre"
    POST: Final[str] = "remember.post"

    COMPRESS_PRE: Final[str] = "compress.pre"
    COMPRESS_POST: Final[str] = "compress.post"


# -- 闭环 B：编排 -----------------------------------------------

class OrchestrateEvent:
    """TaskOrchestrator 相关钩子。"""

    START: Final[str] = "orchestrate.start"
    """载荷 ``{orchestration_id, plan}``。"""

    END: Final[str] = "orchestrate.end"
    """载荷 ``{orchestration_id, report}``。"""


# -- 闭环 C：生长结晶 -------------------------------------------

class GrowthEvent:
    """异常/校正/结晶/角色涌现钩子。"""

    ANOMALY: Final[str] = "growth.anomaly"
    CORRECTION: Final[str] = "growth.correction"
    CRYSTALLIZE: Final[str] = "crystallize.emit"
    ROLE_EMERGE: Final[str] = "role.emerge"


# -- 生命周期 ---------------------------------------------------

class Lifecycle:
    """Cat 本体的开合机事件。"""

    START: Final[str] = "lifecycle.start"
    SHUTDOWN: Final[str] = "lifecycle.shutdown"

    # v0.5.1 感知入口生命周期
    PERCEIVE_START: Final[str] = "lifecycle.perceive_start"
    """``cat.perceive(input)`` 开始，载荷 ``{input, reflex_name}``。"""

    PERCEIVE_END: Final[str] = "lifecycle.perceive_end"
    """``cat.perceive(input)`` 结束，载荷 ``{reflex_name, reply}``。"""


# -- 神经突触 ---------------------------------------------------

class NerveEvent:
    """``cat.signal()`` 调度时触发的神经电位事件。"""

    SIGNAL: Final[str] = "nerve.signal"
    """每次合法 signal 调用都广播，载荷 ``{from, to, method}``。

    违法调用直接抛 :class:`IllegalNeuralPathError`，不发此事件。"""


# -- 分身猫生命周期 -----------------------------------------

class KittenEvent:
    """分身猫派生/执行/回收钩子。见 design.md 十二节 12.9。"""

    SPAWNED: Final[str] = "kitten.spawned"
    """分身猫被派生，载荷 ``{kitten_id, parent_id, task, role}``。"""

    EXECUTING: Final[str] = "kitten.executing"
    """分身猫开始执行，载荷 ``{kitten_id, task_id}``。"""

    COMPLETED: Final[str] = "kitten.completed"
    """分身猫完成任务，载荷 ``{kitten_id, result}``。"""

    STUCK: Final[str] = "kitten.stuck"
    """分身猫卡住，载荷 ``{kitten_id, error_detail}``。"""

    DISMISSED: Final[str] = "kitten.dismissed"
    """分身猫被回收，载荷 ``{kitten_id}``。"""

    MERGE_ABSORBED: Final[str] = "kitten.merge_absorbed"
    """主猫吸收了 MergeProposal，载荷 ``{kitten_id, proposal}``。"""


# -- 汇总（便于 CI / 文档自动生成） --------------------------

ALL_EVENTS: Final[tuple[str, ...]] = (
    # 闭环 A
    LocateEvent.PRE, LocateEvent.POST, LocateEvent.ROUTE_DECIDED,
    RememberEvent.PRE, RememberEvent.POST,
    RememberEvent.COMPRESS_PRE, RememberEvent.COMPRESS_POST,
    # 闭环 B
    OrchestrateEvent.START, OrchestrateEvent.END,
    # 闭环 C
    GrowthEvent.ANOMALY, GrowthEvent.CORRECTION,
    GrowthEvent.CRYSTALLIZE, GrowthEvent.ROLE_EMERGE,
    # Lifecycle
    Lifecycle.START, Lifecycle.SHUTDOWN,
    Lifecycle.PERCEIVE_START, Lifecycle.PERCEIVE_END,
    # 神经突触
    NerveEvent.SIGNAL,
    # 分身猫
    KittenEvent.SPAWNED, KittenEvent.EXECUTING, KittenEvent.COMPLETED,
    KittenEvent.STUCK, KittenEvent.DISMISSED, KittenEvent.MERGE_ABSORBED,
)

__all__ = [
    "LocateEvent", "RememberEvent",
    "OrchestrateEvent", "GrowthEvent", "Lifecycle",
    "NerveEvent",
    "KittenEvent", "ALL_EVENTS",
]
