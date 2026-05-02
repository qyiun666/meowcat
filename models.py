"""meowcat 数据模型 — pydantic BaseModel 形状。

零 ORM、零业务逻辑。具体实现类留在 meowagent。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from meowcat.protocols import BrainStemProtocol

__all__ = [
    "EntityShape", "ConnectionShape", "EpisodeShape", "FocusShape",
    "SubTaskShape", "TaskResultShape", "OrchestratorReportShape",
    "MaintenanceReportShape", "CandidateShape", "LocateResultShape",
    "StageEvent", "PipelineContext", "LoopEvent",
    "MergeProposalShape", "KittenCapability",
]

# -- 脑区形状 -----------------------------------------------------


class EntityShape(BaseModel):
    """纠缠图实体。"""
    id: str
    session_id: str
    name: str
    type: str = "topic"
    content: str = ""
    source: str = "user_stated"
    importance: float = 0.5
    emotion: float = 0.0
    protection: str = "normal"
    last_seen: str = ""
    access_count: int = 0
    is_dormant: bool = False
    is_corrected: bool = False
    corrected_to: str = ""
    l6_indices: list[int] = Field(default_factory=list)


class ConnectionShape(BaseModel):
    """纠缠图连接。"""
    id: str
    from_id: str
    to_id: str
    relation: str = ""
    strength: float = 0.5
    confidence: float = 0.5
    source: str = "inferred"
    co_occurrence: int = 1
    session_ids: list[str] = Field(default_factory=list)


class EpisodeShape(BaseModel):
    """纠缠图事件。"""
    id: str
    session_id: str = ""
    time: str = ""
    type: str = "chat"
    summary: str = ""
    entity_ids: list[str] = Field(default_factory=list)
    turn: int = 0
    is_confirmed: bool = False


class FocusShape(BaseModel):
    """工作记忆焦点。"""
    entity_id: str | None = None
    topic_ids: list[str] = Field(default_factory=list)
    turn_count: int = 0
    last_action: str = ""
    summary: str = ""
    context_snapshot: str = ""

# -- Worker / 编排 ------------------------------------------------


class SubTaskShape(BaseModel):
    """子任务定义。"""
    task_id: str
    role: str
    prompt: str
    dependencies: list[str] = Field(default_factory=list)
    status: str = "pending"
    context_keys: list[str] = Field(default_factory=list)


class TaskResultShape(BaseModel):
    """子任务执行结果。"""
    task_id: str
    role: str
    success: bool
    output: str = ""
    error: str | None = None
    duration: float = 0.0
    artifacts: dict[str, Any] = Field(default_factory=dict)


class OrchestratorReportShape(BaseModel):
    """编排器完整报告。"""
    subtasks: list[SubTaskShape] = Field(default_factory=list)
    results: list[TaskResultShape] = Field(default_factory=list)
    synthesis: str = ""
    total_duration: float = 0.0
    workers_spawned: int = 0
    workers_succeeded: int = 0
    workers_failed: int = 0
    orchestration_id: str | None = None
    status: str = "completed"

# -- 维护 / 定位 --------------------------------------------------


class MaintenanceReportShape(BaseModel):
    """稳态维护报告。"""
    decayed: int = 0
    orphans_cleaned: int = 0
    woke: int = 0
    suggestions: list[str] = Field(default_factory=list)


class CandidateShape(BaseModel):
    """检索候选结果。entity 具体类型在 meowagent。"""
    entity: EntityShape
    weight: float
    match_type: str


class LocateResultShape(BaseModel):
    """检索定位结果（原 AlgorithmOutput，纯数据）。"""
    candidates: list[CandidateShape] = Field(default_factory=list)
    confidence: float = 0.0
    match_type: str = "none"
    is_ambiguous: bool = False

# -- Pipeline / 事件 ----------------------------------------------


_EventKind = Literal["thinking", "output", "short_circuit"]


class StageEvent(BaseModel):
    """Stage 产出的统一事件。"""
    kind: _EventKind
    content: str = ""
    reply: str | None = None

    @classmethod
    def thinking(cls, step: str) -> StageEvent:
        return cls(kind="thinking", content=step)

    @classmethod
    def output(cls, token: str) -> StageEvent:
        return cls(kind="output", content=token)

    @classmethod
    def short_circuit(cls, reply: str) -> StageEvent:
        return cls(kind="short_circuit", content="", reply=reply)

# -- 伴生 BaseModel -----------------------------------------------


class PipelineContext(BaseModel):
    """跨 Stage 共享状态。"""
    model_config = {"arbitrary_types_allowed": True}

    msg: str
    brainstem: BrainStemProtocol  # BrainStemProtocol at runtime
    l6_history: str | None = None
    locate_result: LocateResultShape | None = None
    route: str | None = None
    context_text: str = ""
    prompt: str = ""
    system: str = ""
    reply: str = ""
    short_circuited: bool = False
    final_reply: str | None = None
    extras: dict[str, Any] = Field(default_factory=dict)


class LoopEvent(BaseModel):
    """EventBus 载荷。"""
    event: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""

# -- 分身猫 ---------------------------------------------------------


class MergeProposalShape(BaseModel):
    """分身猫回传主猫的唯一通道。

    分身猫不做决策，只上报；主猫拿到 MergeProposal 后决断
    是否写海马体/纽缠图/触发生长/结晶/角色涌现。见 design.md 十二节 12.6。
    """
    kitten_id: str
    parent_id: str                      # 主猫 cat_id，absorb_merge 时校验防假冒
    task_id: str
    status: str = "completed"  # completed / stuck / partial
    result: str = ""
    new_entities: list[dict[str, Any]] = Field(default_factory=list)
    updated_entities: list[dict[str, Any]] = Field(default_factory=list)
    tool_path: list[dict[str, Any]] = Field(default_factory=list)
    anomaly_hits: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    error_detail: str = ""


class KittenCapability(BaseModel):
    """分身猫能力配置。用户可自定义各器官开关 + 记忆继承范围。

    **铁律**（不可触碰，强制打回）：

    1. ``can_spawn = False``——分身猫不能再建猫
    2. ``can_promote = False``——分身猫不能当主猫
    3. ``has_paws = True``——分身猫就是“手”，没 paws 不是分身猫
    4. 实例必由主猫 spawn_kitten 创建（parent 引用在 Protocol 层强制）

    **最低保障**：``has_cerebrum`` 和 ``has_cerebellum`` 至少一个为 True，
    否则构造时 raise ValueError（无脑的猫不能干活，不能静默修正）。

    **继承语义**：继承的是主猫的 **记忆/状态快照**，不是器官实例。
    主猫专属的管理能力（spawn/absorb/orchestrate）不可继承。

    见 design.md 十二节 12.10。
    """

    # ━━ 铁律（不可触碰）━━
    can_spawn: bool = False
    can_promote: bool = False

    # ━━ 脑区（用户可配，至少一个）━━
    has_cerebrum: bool = True
    has_cerebellum: bool = True
    has_hippocampus: bool = False
    has_thalamus: bool = False
    has_frontal: bool = False
    has_amygdala: bool = True
    has_cortex: bool = False
    has_hypothalamus: bool = False

    # ━━ 感官（用户可配）━━
    has_ears: bool = False
    has_eyes: bool = False
    has_whiskers: bool = True
    has_paws: bool = True            # 铁律：强制打回 True

    # ━━ 输出（用户可配）━━
    has_mouth: bool = False
    has_purr: bool = False
    has_tail: bool = False

    # ━━ 编排（用户可配）━━
    can_remember: bool = False
    can_grow: bool = False

    # ━━ 记忆继承（从主猫继承状态，可全可半）━━
    inherit_memory: Literal["none", "partial", "full"] = "none"
    inherit_entity_ids: list[str] = Field(default_factory=list)  # partial 时指定
    inherit_l6_recent: int = 0       # 继承最近 N 条 L6 历史
    inherit_focus: bool = False      # 是否继承主猫当前焦点

    def model_post_init(self, __context: Any) -> None:
        """铁律静默强制 + 最低保障硬报错。"""
        object.__setattr__(self, "can_spawn", False)
        object.__setattr__(self, "can_promote", False)
        object.__setattr__(self, "has_paws", True)
        if not (self.has_cerebrum or self.has_cerebellum):
            raise ValueError(
                "KittenCapability: 至少需一个脑（cerebrum 或 cerebellum），分身猫不能无脑"
            )
