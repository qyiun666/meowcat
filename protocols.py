"""meowcat 协议层 — 猫的解剖结构蓝图。

全部 typing.Protocol（鸭子类型），零第三方依赖。

v1.0.5: 存储/脑区/感官协议拆分为独立子模块，本文件 re-export 保持兼容。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncIterator, Protocol, runtime_checkable

# v1.0.5: re-export 从子模块，保持 from meowcat import ... 完全兼容
from meowcat.protocols_brain import (
    AmygdalaProtocol,
    BrainStemProtocol,
    CortexProtocol,
    Diagnosable,
    FrontalCortexProtocol,
    GrowthProtocol,
    HippocampusProtocol,
    HypothalamusProtocol,
    LLMBrainProtocol,
    LLMProviderProtocol,
    OrganProtocol,
    ThalamusProtocol,
)
from meowcat.protocols_sense import (
    EarsProtocol,
    EyesProtocol,
    PawsProtocol,
    WhiskersProtocol,
)
from meowcat.protocols_storage import (
    GraphStorageProtocol,
    L6StorageProtocol,
    SharedStorageProtocol,
    VectorStorageProtocol,
)

if TYPE_CHECKING:
    from meowcat.models import (
        CandidateShape,
        ConnectionShape,
        EntityShape,
        EpisodeShape,
        FocusShape,
        KittenCapability,
        LocateResultShape,
        MaintenanceReportShape,
        MergeProposalShape,
        SubTaskShape,
    )

__all__ = [
    "Diagnosable", "OrganProtocol",
    "GraphStorageProtocol", "L6StorageProtocol",
    "VectorStorageProtocol", "SharedStorageProtocol",
    "LLMProviderProtocol",
    "BrainStemProtocol", "HippocampusProtocol", "ThalamusProtocol",
    "LLMBrainProtocol", "AmygdalaProtocol", "FrontalCortexProtocol",
    "HypothalamusProtocol", "CortexProtocol",
    "EarsProtocol", "EyesProtocol", "WhiskersProtocol", "PawsProtocol",
    "GrowthProtocol",
    "StageProtocol", "KittenProtocol",
    "OrchestratorProtocol", "SettingsProtocol", "CatProtocol",
    "AdapterProtocol",
]

# -- Pipeline -----------------------------------------------------


@runtime_checkable
class StageProtocol(Protocol):
    """Pipeline Stage 协议 — 每个 Stage 是一个可插拔的处理步骤。

    **坐标**: 无（Pipeline 层，每个 Stage 实例通过 name 标识，不占用器官坐标）
    **入边**: 由 PipelineRunner 按序驱动，不经 wiring 调用
    **出边**: 通过 yield StageEvent 向 PipelineRunner 输出
    **反射弧**: 无直接反射弧；Stage 内部可通过 ctx 访问 cat 调用 signal()
    **实现方**: 应用层（Pipeline Stage）
    """
    name: str
    async def run(self, ctx: Any) -> AsyncIterator[Any]: ...

# -- 分身猫蓝图 ------------------------------------------------


class KittenProtocol(Protocol):
    """分身猫蓝图 — 纯文档 Protocol（v1.0.1 降级，不再 @runtime_checkable）。

    分身猫 = CatBase(parent_id=..., allowed_organs={...}, forbidden_methods={...})。
    权限由 CatBase 的 ``allowed_organs`` + ``forbidden_methods`` 控制。

    见 ``docs/v0.5.0/design.md`` 十二节。此处保留为文档参考，说明分身猫的
    推荐配置：

    **仅有的器官**: cerebellum, cerebrum, paws, whiskers, amygdala
    **生命周期**: execute → propose_merge → dismiss
    **隔离**: parent_id 只是字符串标识，不持有父猫对象引用

    **实现方**: 应用层（KittenAgent 实现）
    """

    parent_id: str                   # 父猫 cat_id，纯字符串标识
    task: SubTaskShape
    role: str
    workspace: Any
    capability: KittenCapability
    memory_snapshot: dict[str, Any]  # spawn 时注入的只读记忆快照

    # 仅有的器官
    cerebellum: LLMBrainProtocol
    cerebrum: LLMBrainProtocol
    paws: PawsProtocol
    whiskers: WhiskersProtocol
    amygdala: AmygdalaProtocol

    # 生命周期（execute 直接返 MergeProposal，强制回传唯一通道）
    async def execute(self) -> MergeProposalShape: ...
    def propose_merge(self) -> MergeProposalShape: ...
    async def dismiss(self) -> None: ...

# -- 猫本体 -------------------------------------------------------


@runtime_checkable
class OrchestratorProtocol(Protocol):
    """编排器接口 — 6 步编排循环 (plan→dispatch→execute→absorb→revise→fallback)。

    **坐标**: 无（编排器由 Cat 直接持有，不经 wiring 调用）
    **入边**: 由 BrainStem/RouteDecideStage 在判定需编排时触发
    **出边**: 通过 spawn_kitten 创建分身猫，通过 absorb_merge 回收结果
    **反射弧**: 无直接反射弧；编排内部通过 signal 调用 HIPPOCAMPUS 等器官
    **实现方**: 应用层（编排器实现）
    """

    async def orchestrate(self, msg: str) -> Any: ...
    def should_orchestrate(self, msg: str, route: str) -> bool: ...


@runtime_checkable
class SettingsProtocol(Protocol):
    """全局配置接口 — 只暴露 data_dir 给框架层。

    **坐标**: 无（配置层，由 Cat 直接持有）
    **入边**: 由所有器官通过 cat.settings 访问
    **出边**: 无
    **反射弧**: 无
    **实现方**: 应用层（配置实现）
    """
    data_dir: Any


@runtime_checkable
class AdapterProtocol(Protocol):
    """领域适配器 — 定义领域特定的检索权重和实体类型。

    只暴露框架层需要的最小合约：
    - ``name``: 适配器唯一标识
    - ``entity_types``: 该领域的实体类型列表
    - ``locate_weights``: locate() 的检索权重配置

    **坐标**: 无（领域配置，不占用器官坐标）
    **入边**: 应用层初始化和运行时通过 cat.active_adapter 注入
    **出边**: 被 Thalamus.locate() / BrainStem.build_system_prompt() 读取
    **反射弧**: 间接参与 text_dialogue（通过 locate 权重影响路由）
    **实现方**: 应用层（适配器配置）
    """
    name: str
    entity_types: Any
    locate_weights: Any


@runtime_checkable
class CatProtocol(Protocol):
    """猫本体协议 — 一只完整猫的全部对外 API。组合所有脑区+感官+编排能力。

    **坐标**: 无（Cat 是总装类，不占用单一器官坐标；各器官通过 wiring 独立注册）
    **入边**: 外部调用者（CLI、Server、多平台适配器）通过 process_message/perceive_stream 触发
    **出边**: 通过内部器官协调产生回复和行为
    **反射弧**: 持有应用层注册的所有反射弧
    **生命周期**: start() → 事件循环 → shutdown()
    **实现方**: 应用层（Cat 总装类）
    """
    cat_id: str
    settings: Any
    data_dir: Any
    turn: int
    # 脑区
    hippocampus: HippocampusProtocol
    thalamus: ThalamusProtocol
    amygdala: AmygdalaProtocol
    frontal: FrontalCortexProtocol
    hypothalamus: HypothalamusProtocol
    cerebellum: LLMBrainProtocol
    cerebrum: LLMBrainProtocol
    brainstem: BrainStemProtocol
    # 感官
    ears: EarsProtocol
    eyes: EyesProtocol
    whiskers: WhiskersProtocol
    paws: PawsProtocol
    # 编排 / 授权 / 适配器
    orchestrator: OrchestratorProtocol
    approval: Any
    active_adapter: AdapterProtocol | None

    # 神经系统（EventBus）
    async def emit(self, event: str, payload: Any = None) -> None: ...
    def on(self, event: str, handler: Any | None = None) -> Any: ...
    def off(self, event: str, handler: Any) -> bool: ...

    # 对外 API
    async def process_message(self, msg: str) -> str: ...
    async def perceive_stream(
        self, msg: str) -> AsyncIterator[dict[str, str]]: ...

    async def start(self) -> None: ...
    async def shutdown(self) -> None: ...

    # 派生能力（主猫专属，分身猫 Protocol 不包含→框架级防递归）
    async def spawn_kitten(
        self,
        task: SubTaskShape,
        role: str,
        capability: KittenCapability | None = None,
    ) -> KittenProtocol: ...
    async def absorb_merge(self, proposal: MergeProposalShape) -> None: ...
