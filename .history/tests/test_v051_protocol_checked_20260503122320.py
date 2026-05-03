"""
v0.5.1 Task 1.9d — Protocol @runtime_checkable mount 校验测试
===============================================================

契约类别：
    1. TestMountProtocol     — mount 带 protocol 校验通过/拒绝、不带 protocol 永远通过
    2. TestRuntimeCheckable  — isinstance 对全部 Protocol 有效

参考：docs/v0.5.1/design.md
"""

from __future__ import annotations

import pytest

from meowcat import (
    CatBase,
    OrganProtocol,
    OrganProtocolMismatchError,
    StageProtocol,
)
from meowcat.protocols import (
    AmygdalaProtocol, BrainStemProtocol, CatProtocol, CortexProtocol,
    EarsProtocol, EyesProtocol, FrontalCortexProtocol, GraphStorageProtocol,
    HippocampusProtocol, HypothalamusProtocol, KittenProtocol,
    L6StorageProtocol, LLMBrainProtocol, LLMProviderProtocol,
    PawsProtocol, SharedStorageProtocol, ThalamusProtocol,
    VectorStorageProtocol, WhiskersProtocol,
)


# -- 1. mount 带 protocol 校验 ------------------------------------

class _ValidOrgan:
    """满足 OrganProtocol 的最小对象。"""
    name: str = "valid"

    def diagnose(self) -> dict:  # type: ignore[type-arg]
        return {}


class _InvalidOrgan:
    """不满足 OrganProtocol（缺少 name）。"""
    pass


class _ValidStage:
    """满足 StageProtocol。"""
    name: str = "s1"

    async def run(self, ctx: object) -> None:
        pass


class TestMountProtocol:
    """mount 带 protocol 校验通过/拒绝。"""

    def test_mount_with_matching_protocol_passes(self) -> None:
        cat = CatBase("test")
        cat.mount("brain", "region", _ValidOrgan(), protocol=OrganProtocol)
        assert cat.has_organ("brain", "region")

    def test_mount_with_mismatching_protocol_raises(self) -> None:
        cat = CatBase("test")
        with pytest.raises(OrganProtocolMismatchError) as exc:
            cat.mount("brain", "region", _InvalidOrgan(),
                      protocol=OrganProtocol)
        assert exc.value.category == "brain"
        assert exc.value.name == "region"

    def test_mount_without_protocol_always_passes(self) -> None:
        cat = CatBase("test")
        cat.mount("void", "any", _InvalidOrgan())
        assert cat.has_organ("void", "any")

    def test_mount_with_stage_protocol(self) -> None:
        cat = CatBase("test")
        cat.mount("pipeline", "s1", _ValidStage(), protocol=StageProtocol)
        assert cat.has_organ("pipeline", "s1")


# -- 2. isinstance 对全部 Protocol 有效 -----------------------------

class TestRuntimeCheckable:
    """@runtime_checkable 使 isinstance 可检查所有 Protocol。"""

    def test_organ_protocol_isinstance(self) -> None:
        assert isinstance(_ValidOrgan(), OrganProtocol)
        assert not isinstance(_InvalidOrgan(), OrganProtocol)

    # --- 逐一验证每个 Protocol 在其 dummy 实现上的 isinstance ----

    def test_graph_storage_checkable(self) -> None:
        class Dummy:
            async def load(self, cat_id: str) -> dict: return {}
            async def save(self, cat_id: str, data: dict) -> None: pass
        assert isinstance(Dummy(), GraphStorageProtocol)

    def test_l6_storage_checkable(self) -> None:
        class Dummy:
            def append(self, cat_id: str, turn: int,
                       u: str, a: str) -> None: pass

            def load_all(self, cat_id: str) -> list: return []
            def load_recent(self, cat_id: str, n: int = 20) -> list: return []
            def total_chars(self, cat_id: str) -> int: return 0
            def get_stats(self, cat_id: str) -> dict: return {}
        assert isinstance(Dummy(), L6StorageProtocol)

    def test_vector_storage_checkable(self) -> None:
        class Dummy:
            def add(self, text: str, metadata: dict) -> str: return "id"
            def search(self, query: str, k: int = 5) -> list: return []
            def delete(self, doc_id: str) -> bool: return True
        assert isinstance(Dummy(), VectorStorageProtocol)

    def test_shared_storage_checkable(self) -> None:
        class Dummy:
            def load(self) -> dict: return {}
            def save(self, data: dict) -> None: pass
            def merge(self, delta: dict) -> dict: return {}
        assert isinstance(Dummy(), SharedStorageProtocol)

    def test_llm_provider_checkable(self) -> None:
        class Dummy:
            async def completion(self, messages, temperature=None, max_tokens=None,
                                 tools=None, tool_choice=None) -> dict: return {}
            async def stream_completion(
                self, messages, temperature=None, max_tokens=None): yield ""
        assert isinstance(Dummy(), LLMProviderProtocol)

    def test_brainstem_checkable(self) -> None:
        class Dummy:
            async def process(self, msg: str) -> str: return ""
            async def process_stream(self, msg: str): yield {}
            def build_system_prompt(self, route: str) -> str: return ""
            def cancel_current(self) -> bool: return False
        assert isinstance(Dummy(), BrainStemProtocol)

    def test_hippocampus_checkable(self) -> None:
        class Dummy:
            entities: dict = {}
            episodes: list = []
            async def remember(self, u, a, c, m): pass
            def decay(self, now=None) -> int: return 0
            def add_episode(self, ep) -> None: pass
            def add_entity(self, e) -> None: pass
            def fts_search(self, c, k, l) -> list: return []
            def get_entity(self, eid): pass
            def get_by_name(self, n): pass
            def get_all(self) -> list: return []
            def get_related(self, eid) -> list: return []
            def connect(self, f, t, r, s) -> None: pass
            def weaken_connections(self, eid, f) -> None: pass
            def cleanup_orphan_connections(
                self, days_threshold=7) -> int: return 0

            def stats(self, session_id=None) -> dict: return {}
            def to_dict(self) -> dict: return {}
            def from_dict(self, d) -> None: pass
            # v0.5.26 封装方法
            def record_access(self, eid, delta=1) -> None: pass
            def set_dormant(self, eid, dormant) -> None: pass
            def append_content(self, eid, text, max_total=None) -> None: pass
            def update_importance(self, eid, importance) -> None: pass
            def set_last_seen(self, eid, ts) -> None: pass
            # v1.0.15 长流程 workflow 查询
            def list_active_workflows(self, cat_id) -> list: return []
        assert isinstance(Dummy(), HippocampusProtocol)

    def test_thalamus_checkable(self) -> None:
        class Dummy:
            async def locate(self, msg, session_id,
                             chroma=None, weights=None): pass

            def decide_route(self, **kwargs) -> dict: return {}

            def _infer_route(self, output) -> str: return ""
        assert isinstance(Dummy(), ThalamusProtocol)

    def test_llm_brain_checkable(self) -> None:
        class Dummy:
            name: str = "test"

            async def generate(self, p, sp=None, t=0.7,
                               mt=None) -> str: return ""
            async def stream_generate(
                self, p, sp=None, t=0.7, mt=None): yield ""

            def reload_config(self) -> None: pass
        assert isinstance(Dummy(), LLMBrainProtocol)

    def test_amygdala_checkable(self) -> None:
        class Dummy:
            def is_rejection(self, msg: str) -> bool: return False
            def classify_rejection(self, msg: str) -> str: return ""
            def parse_correction(self, msg: str): pass
            async def handle_rejection(self, msg, lc, h): return ""
            async def handle_correction(self, msg, h): pass
            async def assess_safety(self, msg) -> dict: return {}
            @staticmethod
            def assess_tool_risk(tn, p) -> dict: return {}
            def tag_emotion(self, ep) -> dict: return {}
        assert isinstance(Dummy(), AmygdalaProtocol)

    def test_frontal_checkable(self) -> None:
        class Dummy:
            def detect_shift(self, msg: str) -> bool: return False
            def is_continue(self, msg: str) -> bool: return False
            def archive_focus(self) -> None: pass
            def update_focus(self, result) -> None: pass
            def save(self, path=None) -> None: pass
            def load(self, path=None) -> None: pass
        assert isinstance(Dummy(), FrontalCortexProtocol)

    def test_hypothalamus_checkable(self) -> None:
        class Dummy:
            async def run_maintenance(self, cc=None): pass
            def decay_memories(self, now=None) -> dict: return {}
            def compress_long_history(self) -> dict: return {}
            def wake_by_name(self, n, sid=None) -> list: return []
            def wake_by_keywords(self, kw, sid=None) -> list: return []
        assert isinstance(Dummy(), HypothalamusProtocol)

    def test_cortex_checkable(self) -> None:
        class Dummy:
            def ingest(self, source, layer, key, value) -> None: pass
            def record_weakness(self, kind, detail) -> None: pass
            def weaknesses(self) -> list: return []
            def synthesize(self, max_tokens=400) -> str: return ""
        assert isinstance(Dummy(), CortexProtocol)

    def test_ears_checkable(self) -> None:
        class Dummy:
            name: str = "ears"
            async def hear(self, raw): return {}
            def extract_keywords(self, text, top_k=5) -> list: return []
            def detect_language(self, text) -> str: return ""
            def tag_emotion(self, episode) -> dict: return episode
        assert isinstance(Dummy(), EarsProtocol)

    def test_eyes_checkable(self) -> None:
        class Dummy:
            name: str = "eyes"
            async def see(self, img, mime="image/png") -> dict: return {}
        assert isinstance(Dummy(), EyesProtocol)

    def test_whiskers_checkable(self) -> None:
        class Dummy:
            name: str = "whiskers"
            async def feel_input(self, text) -> dict: return {}
            async def feel_output(self, out, schema=None) -> dict: return {}
            def detect_drift(self, recent) -> dict: return {}
            def check_hallucination(self, reply, sid=None) -> dict: return {}
        assert isinstance(Dummy(), WhiskersProtocol)

    def test_paws_checkable(self) -> None:
        class Dummy:
            name: str = "paws"
            async def execute(self, tool_name, params) -> dict: return {}
            async def touch_file(self, path, content=None) -> dict: return {}
            async def run_command(self, cmd, **kw) -> dict: return {}
            async def interact_with_tool(self, sn, params) -> dict: return {}
        assert isinstance(Dummy(), PawsProtocol)

    def test_stage_checkable(self) -> None:
        assert isinstance(_ValidStage(), StageProtocol)
        # 缺 run 的不满足

        class Bad:
            name: str = "bad"
        assert not isinstance(Bad(), StageProtocol)

    def test_kitten_checkable(self) -> None:
        """v1.0.1: KittenProtocol 降级为纯文档（不再 @runtime_checkable），
        故 isinstance 检测移除。验证 Protocol 仍可 import 且为 Protocol 子类。
        """
        from typing import Protocol
        assert issubclass(KittenProtocol, Protocol)

    def test_cat_protocol_checkable(self) -> None:
        class Dummy:
            cat_id: str = "cat"
            settings: object = None
            data_dir: object = None
            turn: int = 0
            hippocampus: object = None
            thalamus: object = None
            amygdala: object = None
            frontal: object = None
            hypothalamus: object = None
            cerebellum: object = None
            cerebrum: object = None
            brainstem: object = None
            ears: object = None
            eyes: object = None
            whiskers: object = None
            paws: object = None
            orchestrator: object = None
            approval: object = None
            active_adapter: object = None
            async def emit(self, e, p=None) -> None: pass
            def on(self, e, h=None): pass
            def off(self, e, h) -> bool: return False
            async def process_message(self, msg: str) -> str: return msg
            async def perceive_stream(self, msg: str): yield {"content": msg}
            async def start(self) -> None: pass
            async def shutdown(self) -> None: pass
            async def spawn_kitten(self, t, r, c=None): pass
            async def absorb_merge(self, p) -> None: pass
        assert isinstance(Dummy(), CatProtocol)
