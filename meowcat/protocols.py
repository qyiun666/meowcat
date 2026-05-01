"""meowcat 协议层 — 猫的解剖结构蓝图。

全部 typing.Protocol（鸭子类型），零第三方依赖。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncIterator, Protocol, runtime_checkable

if TYPE_CHECKING:
    from meowcat.models import (
        KittenCapability, MergeProposalShape, SubTaskShape,
    )

# -- 基础 ---------------------------------------------------------


@runtime_checkable
class OrganProtocol(Protocol):
    name: str

# -- 存储 ---------------------------------------------------------


@runtime_checkable
class GraphStorageProtocol(Protocol):
    async def load(self, cat_id: str) -> dict[str, Any]: ...
    async def save(self, cat_id: str, graph_data: dict[str, Any]) -> None: ...


@runtime_checkable
class L6StorageProtocol(Protocol):
    def append(self, cat_id: str, turn: int,
               user_msg: str, ai_reply: str) -> None: ...

    def load_all(self, cat_id: str) -> list[dict[str, Any]]: ...
    def load_recent(self, cat_id: str,
                    n: int = 20) -> list[dict[str, Any]]: ...

    def total_chars(self, cat_id: str) -> int: ...
    def get_stats(self, cat_id: str) -> dict[str, Any]: ...


@runtime_checkable
class VectorStorageProtocol(Protocol):
    def add(self, text: str, metadata: dict[str, Any]) -> str: ...
    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]: ...
    def delete(self, doc_id: str) -> bool: ...


@runtime_checkable
class SharedStorageProtocol(Protocol):
    def load(self) -> dict[str, Any]: ...
    def save(self, data: dict[str, Any]) -> None: ...
    def merge(self, delta: dict[str, Any]) -> dict[str, Any]: ...

# -- LLM ----------------------------------------------------------


@runtime_checkable
class LLMProviderProtocol(Protocol):
    async def completion(self, messages: list[dict[str, str]], temperature: float | None = None, max_tokens: int |
                         None = None, tools: list[dict[str, Any]] | None = None, tool_choice: str | None = None) -> dict[str, Any]: ...
    async def stream_completion(self, messages: list[dict[str, str]], temperature: float |
                                None = None, max_tokens: int | None = None) -> AsyncIterator[str]: ...

# -- 脑区 ---------------------------------------------------------


@runtime_checkable
class BrainStemProtocol(Protocol):
    async def process(self, msg: str) -> str: ...
    async def process_stream(
        self, msg: str) -> AsyncIterator[dict[str, str]]: ...

    def build_system_prompt(self, route: str) -> str: ...
    def cancel_current(self) -> bool: ...


@runtime_checkable
class HippocampusProtocol(Protocol):
    entities: dict[str, Any]
    episodes: list[Any]
    async def remember(self, user_msg: str, ai_reply: str,
                       cat_id: str, model: str) -> Any: ...

    def decay(self, now: Any | None = None) -> int: ...
    def add_episode(self, episode: Any) -> None: ...
    def fts_search(self, cat_id: str, keywords: str,
                   limit: int) -> list[dict[str, Any]]: ...

    def get_entity(self, entity_id: str) -> Any | None: ...
    def get_by_name(self, name: str) -> Any | None: ...
    def get_all(self) -> list[Any]: ...
    def get_related(self, entity_id: str) -> list[Any]: ...
    def connect(self, from_id: str, to_id: str,
                relation: str, strength: float) -> None: ...

    def weaken_connections(self, entity_id: str, factor: float) -> None: ...
    def to_dict(self) -> dict[str, Any]: ...
    def from_dict(self, d: dict[str, Any]) -> None: ...


@runtime_checkable
class ThalamusProtocol(Protocol):
    async def locate(self, msg: str, session_id: str, chroma: Any |
                     None = None, weights: Any | None = None) -> Any: ...

    def _infer_route(self, output: Any) -> str: ...


@runtime_checkable
class LLMBrainProtocol(Protocol):
    """Cerebrum/Cerebellum 共用协议。B/A 模型差异仅在构造参数。"""
    name: str

    async def generate(self, prompt: str, system_prompt: str | None = None,
                       temperature: float = 0.7, max_tokens: int | None = None) -> str: ...
    async def stream_generate(self, prompt: str, system_prompt: str | None = None,
                              temperature: float = 0.7, max_tokens: int | None = None) -> AsyncIterator[str]: ...

    def reload_config(self) -> None: ...


@runtime_checkable
class AmygdalaProtocol(Protocol):
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
    def detect_shift(self, msg: str) -> bool: ...
    def is_continue(self, msg: str) -> bool: ...
    def archive_focus(self) -> None: ...
    def update_focus(self, result: Any) -> None: ...
    def save(self, path: Any | None = None) -> None: ...
    def load(self, path: Any | None = None) -> None: ...


@runtime_checkable
class HypothalamusProtocol(Protocol):
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
    def ingest(self, source: str, layer: str,
               key: str, value: Any) -> None: ...

    def record_weakness(self, kind: str, detail: str) -> None: ...
    def weaknesses(self) -> list[dict[str, Any]]: ...

# -- 感官 ---------------------------------------------------------


@runtime_checkable
class EarsProtocol(Protocol):
    name: str
    async def hear(self, raw_input: str | bytes) -> dict[str, Any]: ...
    def extract_keywords(self, text: str, top_k: int = 5) -> list[str]: ...
    def detect_language(self, text: str) -> str: ...


@runtime_checkable
class EyesProtocol(Protocol):
    name: str

    async def see(self, image_data: bytes,
                  mime_type: str = "image/png") -> dict[str, Any]: ...
    async def scan_screen(
        self, region: tuple[int, int, int, int] | None = None) -> dict[str, Any]: ...

    def describe(self, image_path: str) -> str: ...


@runtime_checkable
class WhiskersProtocol(Protocol):
    name: str
    async def feel_input(self, text: str) -> dict[str, Any]: ...
    async def feel_output(
        self, output: str, expected_schema: dict[str, Any] | None = None) -> dict[str, Any]: ...

    def detect_drift(self, recent_outputs: list[str]) -> dict[str, Any]: ...
    def check_hallucination(
        self, reply: str, session_id: str | None = None) -> dict[str, Any]: ...


@runtime_checkable
class PawsProtocol(Protocol):
    name: str

    async def touch_file(self, path: str, content: str |
                         None = None) -> dict[str, Any]: ...

    async def run_command(self, command: str, **
                          kwargs: Any) -> dict[str, Any]: ...
    async def interact_with_tool(
        self, skill_name: str, params: dict[str, Any]) -> dict[str, Any]: ...

    def get_execution_log(self) -> list[dict[str, Any]]: ...

# -- Pipeline -----------------------------------------------------


@runtime_checkable
class StageProtocol(Protocol):
    name: str
    async def run(self, ctx: Any) -> AsyncIterator[Any]: ...

# -- 分身猫蓝图 ------------------------------------------------


@runtime_checkable
class KittenProtocol(Protocol):
    """分身猫蓝图——有手无嘴，执行专精。

    见 ``docs/v0.5.0/design.md`` 十二节。只暴露 Protocol 层面存在的器官，
    没定义的方法 = 该器官在框架层不存在（如耳朵/嘴巴/海马体）。

    **继承语义**：spawn 时主猫按 capability.inherit_* 重约注入快照到
    ``memory_snapshot``，分身猫只读使用；不共享主猫器官实例（避免状态互扰）。
    """

    parent: CatProtocol              # 主猫强引用（框架级强制分身猫必由主猫建）
    parent_id: str                   # 主猫 cat_id 副本，序列化友好
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
    """编排器接口 — 决定是否并行拆解任务、启动分身猫。"""
    async def orchestrate(self, msg: str) -> Any: ...
    def should_orchestrate(self, msg: str, route: str) -> bool: ...


@runtime_checkable
class SettingsProtocol(Protocol):
    """全局配置接口 — 只暴露 data_dir 给框架层。"""
    data_dir: Any


@runtime_checkable
class CatProtocol(Protocol):
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
    active_adapter: Any

    # 神经系统（EventBus）
    async def emit(self, event: str, payload: Any = None) -> None: ...
    def on(self, event: str, handler: Any | None = None) -> Any: ...
    def off(self, event: str, handler: Any) -> bool: ...

    # 对外 API
    async def process_message(self, msg: str) -> str: ...
    async def perceive_stream(self, msg: str) -> AsyncIterator[dict[str, str]]: ...
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
