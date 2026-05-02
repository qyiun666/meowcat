"""meowcat 脑区协议 — 大脑/小脑/脑干/海马体等神经器官接口。

全部 typing.Protocol（鸭子类型），零第三方依赖。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncIterator, Protocol, runtime_checkable

if TYPE_CHECKING:
    from meowcat.models import LocateResultShape

__all__ = [
    "Diagnosable", "OrganProtocol",
    "BrainStemProtocol", "HippocampusProtocol", "ThalamusProtocol",
    "LLMBrainProtocol", "AmygdalaProtocol", "FrontalCortexProtocol",
    "HypothalamusProtocol", "CortexProtocol",
    "LLMProviderProtocol", "GrowthProtocol",
]

# -- 基础 ---------------------------------------------------------


@runtime_checkable
class Diagnosable(Protocol):
    """器官诊断接口 — 只读快照，返回值必须是纯 dict。

    框架层 probe() 只允许调用此方法；任何写入/副作用操作都不允许。

    **坐标**: 无（基础协议，不占用器官坐标）
    **入边**: 任何已 wire 器官的 probe() 调用均可抵达
    **出边**: 无
    **反射弧**: 无
    **实现方**: 所有器官实现类（需实现 diagnose()）
    """

    def diagnose(self) -> dict[str, Any]: ...


@runtime_checkable
class OrganProtocol(Diagnosable, Protocol):
    """器官基础协议 — 所有器官必须实现 name + diagnose()。

    v0.5.14: OrganProtocol 继承 Diagnosable，强制所有器官可被 probe。

    **坐标**: 无（基础协议，器官通过 wiring 注册时指定坐标）
    **入边**: 通过 wiring 装配的允许边决定
    **出边**: 通过 wiring 装配的允许边决定
    **反射弧**: 取决于应用层定义的反射弧 path
    **实现方**: meowcat/defaults/ 中的 Noop* 类 (默认空实现)
    """

    name: str

# -- LLM ----------------------------------------------------------


@runtime_checkable
class LLMProviderProtocol(Protocol):
    """LLM 统一调用接口（LiteLLM 封装）。

    **坐标**: 无（模型层，不占用器官坐标）
    **入边**: 由 Cerebrum/Cerebellum 直接持有，不经 wiring 调用
    **出边**: 无
    **反射弧**: 无
    **实现方**: 应用层（LLM Provider）
    """

    async def completion(self, messages: list[dict[str, str]], temperature: float | None = None, max_tokens: int |
                         None = None, tools: list[dict[str, Any]] | None = None, tool_choice: str | None = None) -> dict[str, Any]: ...
    async def stream_completion(self, messages: list[dict[str, str]], temperature: float |
                                None = None, max_tokens: int | None = None) -> AsyncIterator[str]: ...

# -- 脑区 ---------------------------------------------------------


@runtime_checkable
class BrainStemProtocol(Protocol):
    """脑干 — 总调度中枢，连接所有脑区和感官。

    v0.5.12: process/process_stream 已删除。
    BrainStem 退化为 Pipeline Stage 的辅助方法提供方，
    不再作为主循环入口。保留 build_system_prompt 和 cancel_current
    作为对外最小合约。

    **坐标**: ``("brain", "brainstem")``
    **入边**: THALAMUS
    **出边**: THALAMUS, HIPPOCAMPUS, CEREBRUM, CEREBELLUM, AMYGDALA, FRONTAL, HYPOTHALAMUS, CORTEX + 全 SENSORS + 全 VOICES
    **反射弧**: text_dialogue (EARS→THALAMUS→BRAINSTEM→CEREBRUM→...)
    **实现方**: 应用层（脑区器官）
    """

    async def build_system_prompt(self, route: str) -> str: ...
    def cancel_current(self) -> bool: ...


@runtime_checkable
class HippocampusProtocol(Protocol):
    """海马体 — 纠缠图记忆编码与检索。

    **坐标**: ``("brain", "hippocampus")``
    **入边**: CEREBRUM, FRONTAL, HYPOTHALAMUS, BRAINSTEM
    **出边**: CEREBRUM, CORTEX
    **反射弧**: 无直接反射弧，通过 BRAINSTEM 间接参与 text_dialogue
    **实现方**: 应用层（脑区器官）
    """
    entities: dict[str, Any]  # EntityShape
    episodes: list[Any]  # EpisodeShape
    async def remember(self, user_msg: str, ai_reply: str,
                       cat_id: str, model: str) -> Any: ...

    def decay(self, now: Any | None = None) -> int: ...
    def add_episode(self, episode: Any) -> None: ...  # EpisodeShape
    def add_entity(self, entity: Any) -> None: ...  # EntityShape
    def fts_search(self, cat_id: str, keywords: str,
                   limit: int) -> list[dict[str, Any]]: ...

    def get_entity(self, entity_id: str) -> Any | None: ...  # EntityShape
    def get_by_name(self, name: str) -> Any | None: ...  # EntityShape
    def get_all(self) -> list[Any]: ...  # list[EntityShape]

    def get_related(
        self, entity_id: str) -> list[Any]: ...  # list[EntityShape]
    def connect(self, from_id: str, to_id: str,
                relation: str, strength: float) -> None: ...

    def weaken_connections(self, entity_id: str, factor: float) -> None: ...
    def cleanup_orphan_connections(self, days_threshold: int = 7) -> int: ...
    def stats(self, session_id: str | None = None) -> dict[str, Any]: ...
    def to_dict(self) -> dict[str, Any]: ...
    def from_dict(self, d: dict[str, Any]) -> None: ...

    # v0.5.26 封装方法（替代裸字段访问）
    def record_access(self, entity_id: str, delta: int = 1) -> None: ...
    def set_dormant(self, entity_id: str, dormant: bool) -> None: ...
    def append_content(self, entity_id: str, text: str,
                       max_total: int | None = None) -> None: ...

    def update_importance(self, entity_id: str, importance: float) -> None: ...
    def set_last_seen(self, entity_id: str, ts: str) -> None: ...


@runtime_checkable
class ThalamusProtocol(Protocol):
    """丘脑 — 感觉中继与路由决策。所有感官输入经此过滤分发到大脑/脑干/杏仁核。

    **坐标**: ``("brain", "thalamus")``
    **入边**: EARS, EYES, WHISKERS (全 SENSORS)
    **出边**: CEREBRUM, BRAINSTEM, AMYGDALA
    **反射弧**: text_dialogue, visual, danger, action_order
    **实现方**: 应用层（脑区器官）
    """

    async def locate(self, msg: str, session_id: str, chroma: Any |
                     None = None, weights: Any | None = None) -> LocateResultShape: ...  # type: ignore[name-defined]  # noqa: F821

    def decide_route(self, **kwargs: Any) -> dict[str, Any]: ...


@runtime_checkable
class LLMBrainProtocol(Protocol):
    """大小脑共用 LLM 协议。Cerebrum/Cerebellum 差异仅在构造参数（模型型号、温度）。

    **坐标** (CEREBRUM): ``("brain", "cerebrum")`` — 入边: THALAMUS, HIPPOCAMPUS, FRONTAL, BRAINSTEM; 出边: HIPPOCAMPUS, CEREBELLUM, FRONTAL
    **坐标** (CEREBELLUM): ``("brain", "cerebellum")`` — 入边: CEREBRUM, AMYGDALA, BRAINSTEM; 出边: EFFECTORS (PAWS, MOUTH, PURR, TAIL)
    **反射弧**: text_dialogue, visual, action_order
    **实现方**: 应用层（脑区器官）
    """
    name: str

    async def generate(self, prompt: str, system_prompt: str | None = None,
                       temperature: float = 0.7, max_tokens: int | None = None) -> str: ...
    async def stream_generate(self, prompt: str, system_prompt: str | None = None,
                              temperature: float = 0.7, max_tokens: int | None = None) -> AsyncIterator[str]: ...

    def reload_config(self) -> None: ...


@runtime_checkable
class AmygdalaProtocol(Protocol):
    """杏仁核 — 否定修正与安全兜底。可绕过大脑直接触发效应器（应激反射）。

    **坐标**: ``("brain", "amygdala")``
    **入边**: THALAMUS, BRAINSTEM
    **出边**: CEREBELLUM, MOUTH
    **反射弧**: danger (EARS→THALAMUS→AMYGDALA→MOUTH), action_order
    **实现方**: 应用层（脑区器官）
    """

    def is_rejection(self, msg: str) -> bool: ...
    def classify_rejection(self, msg: str) -> str: ...
    def parse_correction(self, msg: str) -> tuple[str, str] | None: ...

    async def handle_rejection(
        self, msg: str, last_candidates: list[Any], hippocampus: Any) -> str: ...
    async def handle_correction(
        self, msg: str, hippocampus: Any) -> tuple[str, str] | None: ...

    async def assess_safety(self, user_input: str) -> dict[str, Any]: ...

    @staticmethod
    def assess_tool_risk(
        tool_name: str, params: dict[str, Any]) -> dict[str, Any]: ...

    def tag_emotion(self, episode: dict[str, Any]) -> dict[str, Any]: ...


@runtime_checkable
class FrontalCortexProtocol(Protocol):
    """额叶 — 焦点系统（工作记忆）。话题切换检测、焦点归档与更新。

    **坐标**: ``("brain", "frontal")``
    **入边**: CEREBRUM, BRAINSTEM
    **出边**: CEREBRUM, HIPPOCAMPUS
    **反射弧**: 无直接反射弧
    **实现方**: 应用层（脑区器官）
    """

    def detect_shift(self, msg: str) -> bool: ...
    def is_continue(self, msg: str) -> bool: ...
    def archive_focus(self) -> None: ...
    def update_focus(self, result: Any) -> None: ...
    def save(self, path: Any | None = None) -> None: ...
    def load(self, path: Any | None = None) -> None: ...


@runtime_checkable
class HypothalamusProtocol(Protocol):
    """下丘脑 — 稳态维护。负责记忆衰减、孤岛清理等后台自维护。

    **坐标**: ``("brain", "hypothalamus")``
    **入边**: BRAINSTEM
    **出边**: HYPOTHALAMUS (自环), HIPPOCAMPUS, CORTEX
    **反射弧**: 无直接反射弧
    **实现方**: 应用层（脑区器官）
    """

    async def run_maintenance(
        self, country_code: str | None = None) -> Any: ...

    def decay_memories(self, now: Any | None = None) -> dict[str, Any]: ...
    def compress_long_history(self) -> dict[str, Any]: ...

    def wake_by_name(self, name: str, session_id: str |
                     None = None) -> list[Any]: ...
    def wake_by_keywords(
        self, keywords: list[str], session_id: str | None = None) -> list[Any]: ...


@runtime_checkable
class CortexProtocol(Protocol):
    """大脑皮层 — 四层世界观（axioms/others/values/self）。

    **坐标**: ``("brain", "cortex")``
    **入边**: HIPPOCAMPUS, HYPOTHALAMUS, BRAINSTEM
    **出边**: 无（终端器官，只被读取不主动调用）
    **反射弧**: 无
    **实现方**: 应用层（脑区器官）
    """

    def ingest(self, source: str, layer: str,
               key: str, value: Any) -> None: ...

    def record_weakness(self, kind: str, detail: str) -> None: ...
    def weaknesses(self) -> list[dict[str, Any]]: ...
    def synthesize(self, max_tokens: int = 400) -> str: ...

# -- 生长器官 (Growth) --------------------------------------------


@runtime_checkable
class GrowthProtocol(OrganProtocol, Protocol):
    """生长器官协议 — 闭环 C（自生长回路）的四个器官共用接口。

    框架层只声明协议签名和 wiring，零实现。
    meowagent 应用层实现具体逻辑（AnomalyGrowth / CorrectionGrowth /
    CrystallizationDetector / RoleEmergence）。

    **坐标** (ANOMALY_GROWTH): ``("growth", "anomaly_growth")`` — 入边: BRAINSTEM; 出边: HIPPOCAMPUS, CORTEX
    **坐标** (CORRECTION_GROWTH): ``("growth", "correction_growth")`` — 入边: BRAINSTEM; 出边: HIPPOCAMPUS, CORTEX
    **坐标** (CRYSTALLIZER): ``("growth", "crystallizer")`` — 入边: BRAINSTEM; 出边: 无
    **坐标** (ROLE_EMERGENCE): ``("growth", "role_emergence")`` — 入边: BRAINSTEM; 出边: 无
    **反射弧**: 无直接反射弧；通过 BRAINSTEM 在生长检查时触发
    **实现方**: 应用层（生长器官）
    """

    # record() 是四个生长器官的共同方法，签名因器官而异
    # 框架层不约束参数，只在 wiring 层面校验通路
