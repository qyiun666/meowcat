# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat 独立测试: 所有 Protocol 可 import + isinstance 校验。

验证:
- 每个 @runtime_checkable Protocol 都能正常 import
- Default* 桩满足对应 Protocol
- CatProtocol 包含 v0.2.0 新增 API（turn、process_message 等）
"""

from __future__ import annotations

import pytest

from meowcat import OrganProtocolMismatchError
from meowcat.defaults.organs import (
    DefaultAmygdala,
    DefaultAnomalyGrowth,
    DefaultCerebellum,
    DefaultCerebrum,
    DefaultCorrectionGrowth,
    DefaultCortex,
    DefaultCrystallizer,
    DefaultEars,
    DefaultEyes,
    DefaultFrontal,
    DefaultHypothalamus,
    DefaultMouth,
    DefaultPurr,
    DefaultRoleEmergence,
    DefaultTail,
    DefaultWhiskers,
)
from meowcat.defaults.stores import InMemoryGraphStore
from meowcat.testing import make_cat
from meowcat.protocols import (
    AmygdalaProtocol,
    AnomalyGrowthProtocol,
    BrainStemProtocol,
    CatProtocol,
    CorrectionGrowthProtocol,
    CortexProtocol,
    CrystallizerProtocol,
    EarsProtocol,
    EyesProtocol,
    FrontalCortexProtocol,
    GraphStorageProtocol,
    HippocampusProtocol,
    HypothalamusProtocol,
    KittenProtocol,
    LLMBrainProtocol,
    LLMProviderProtocol,
    OrchestratorProtocol,
    OrganProtocol,
    PawsProtocol,
    RoleEmergenceProtocol,
    SettingsProtocol,
    SharedStorageProtocol,
    StageProtocol,
    ThalamusProtocol,
    VectorStorageProtocol,
    WhiskersProtocol,
)


class TestProtocolImport:
    """所有 Protocol 可 import 且是 Protocol 类型。"""

    def test_all_protocols_importable(self) -> None:
        protocols = [
            OrganProtocol, GraphStorageProtocol,
            VectorStorageProtocol, SharedStorageProtocol,
            LLMProviderProtocol, BrainStemProtocol, HippocampusProtocol,
            ThalamusProtocol, LLMBrainProtocol, AmygdalaProtocol,
            FrontalCortexProtocol, HypothalamusProtocol, CortexProtocol,
            EarsProtocol, EyesProtocol, WhiskersProtocol, PawsProtocol,
            StageProtocol, KittenProtocol, OrchestratorProtocol,
            SettingsProtocol, CatProtocol,
            AnomalyGrowthProtocol, CorrectionGrowthProtocol,
            CrystallizerProtocol, RoleEmergenceProtocol,
        ]
        for p in protocols:
            assert p is not None, f"Failed to import {p}"

    def test_cat_protocol_has_turn(self) -> None:
        """v0.2.0: CatProtocol 必须声明 turn 属性。"""
        import typing
        hints = typing.get_type_hints(CatProtocol)
        assert "turn" in hints, "CatProtocol missing 'turn'"

    def test_cat_protocol_has_process_message(self) -> None:
        """v0.2.0: CatProtocol 必须声明 process_message。"""
        assert hasattr(CatProtocol, "process_message"), \
            "CatProtocol missing process_message"

    def test_cat_protocol_has_start_shutdown(self) -> None:
        """CatProtocol 必须声明 start / shutdown。"""
        assert hasattr(CatProtocol, "start"), "CatProtocol missing start"
        assert hasattr(CatProtocol, "shutdown"), "CatProtocol missing shutdown"

    def test_cat_protocol_has_perceive_stream(self) -> None:
        """CatProtocol 必须声明 perceive_stream。"""
        assert hasattr(CatProtocol, "perceive_stream"), \
            "CatProtocol missing perceive_stream"


class TestDefaultSatisfiesProtocol:
    """每个 Default* 桩满足对应 Protocol 的 isinstance 校验。"""

    def test_noop_amygdala(self) -> None:
        a = DefaultAmygdala()
        assert isinstance(a, AmygdalaProtocol)
        assert a.is_rejection("hello") is False
        assert a.classify_rejection("hello") == "none"
        assert a.parse_correction("hello") is None

    def test_noop_frontal(self) -> None:
        f = DefaultFrontal()
        assert isinstance(f, FrontalCortexProtocol)
        assert f.detect_shift("hello") is True
        assert f.is_continue("hello") is False

    def test_noop_hypothalamus(self) -> None:
        h = DefaultHypothalamus()
        assert isinstance(h, HypothalamusProtocol)

    def test_noop_cortex(self) -> None:
        c = DefaultCortex()
        assert isinstance(c, CortexProtocol)

    @pytest.mark.anyio
    async def test_noop_ears(self) -> None:
        e = DefaultEars()
        assert isinstance(e, EarsProtocol)
        assert e.extract_keywords("hello") == ["hello"]
        assert e.detect_language("hello") == "en"

    def test_noop_eyes(self) -> None:
        e = DefaultEyes()
        assert isinstance(e, EyesProtocol)

    def test_noop_mouth(self) -> None:
        m = DefaultMouth()
        assert isinstance(m, OrganProtocol)

    def test_noop_purr(self) -> None:
        p = DefaultPurr()
        assert isinstance(p, OrganProtocol)

    def test_noop_tail(self) -> None:
        t = DefaultTail()
        assert isinstance(t, OrganProtocol)

    def test_noop_whiskers(self) -> None:
        w = DefaultWhiskers()
        assert isinstance(w, WhiskersProtocol)

    # -- v1.0.16: Growth + LLM organs ----------------------------------

    def test_noop_cerebrum(self) -> None:
        c = DefaultCerebrum()
        assert isinstance(c, LLMBrainProtocol)
        assert c.name == "renovated_cerebrum"
        assert c.diagnose() == {
            "model": "renovated",
            "has_llm": False,
            "prompt_preset": "none",
            "organ_prompt": False,
        }
        c.reload_config()  # no-op

    def test_noop_cerebellum(self) -> None:
        c = DefaultCerebellum()
        assert isinstance(c, LLMBrainProtocol)
        assert c.name == "renovated_cerebellum"

    def test_noop_anomaly_growth(self) -> None:
        a = DefaultAnomalyGrowth()
        assert isinstance(a, AnomalyGrowthProtocol)
        assert a.name == "renovated_anomaly_growth"
        result = a.record("drift", "snippet", 0.9)
        assert isinstance(result, dict)

    def test_noop_correction_growth(self) -> None:
        c = DefaultCorrectionGrowth()
        assert isinstance(c, CorrectionGrowthProtocol)
        result = c.record("wrong", "correct", session_id="s1")
        assert isinstance(result, dict)

    def test_noop_crystallizer(self) -> None:
        c = DefaultCrystallizer()
        assert isinstance(c, CrystallizerProtocol)
        assert c.crystallize("my_skill", 1) is False
        assert c.crystallize("my_skill", 4) is True
        assert c.hotspots(3) == [("my_skill", 5)]

    def test_noop_role_emergence(self) -> None:
        r = DefaultRoleEmergence()
        assert isinstance(r, RoleEmergenceProtocol)
        result = r.record("pattern_x", "evidence_y")
        assert isinstance(result, dict)


class TestInMemoryStores:
    """InMemory 存储满足对应 Protocol。"""

    def test_inmemory_graph_store(self) -> None:
        import anyio
        s = InMemoryGraphStore()
        assert isinstance(s, GraphStorageProtocol)

        async def _test() -> None:
            await s.save("cat1", {"entities": {}})
            data = await s.load("cat1")
            assert data == {"entities": {}}

        anyio.run(_test)


class TestProtocolRuntimeCheckable:
    """@runtime_checkable 装饰器在运行时生效。"""

    def test_organ_protocol_name_check(self) -> None:
        class HasName:
            name = "test"

            def diagnose(self) -> dict:  # type: ignore[type-arg]
                return {}
        assert isinstance(HasName(), OrganProtocol)

    def test_organ_protocol_no_name_fails(self) -> None:
        class NoName:
            pass
        assert not isinstance(NoName(), OrganProtocol)


# -- from v0.5.1: 补充 mount protocol 校验 / isinstance 契约测试 -


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
    """v0.5.1: mount 带 protocol 校验通过/拒绝。"""

    def test_mount_with_matching_protocol_passes(self) -> None:
        cat = make_cat("test")
        cat.mount("brain", "region", _ValidOrgan(), protocol=OrganProtocol)
        assert cat.has_organ("brain", "region")

    def test_mount_with_mismatching_protocol_raises(self) -> None:
        cat = make_cat("test")
        with pytest.raises(OrganProtocolMismatchError) as exc:
            cat.mount("brain", "region", _InvalidOrgan(),
                      protocol=OrganProtocol)
        assert exc.value.category == "brain"
        assert exc.value.name == "region"

    def test_mount_without_protocol_always_passes(self) -> None:
        cat = make_cat("test")
        cat.mount("void", "any", _InvalidOrgan())
        assert cat.has_organ("void", "any")

    def test_mount_with_stage_protocol(self) -> None:
        cat = make_cat("test")
        cat.mount("pipeline", "s1", _ValidStage(), protocol=StageProtocol)
        assert cat.has_organ("pipeline", "s1")


class TestRuntimeCheckable:
    """v0.5.1: @runtime_checkable 使 isinstance 可检查所有 Protocol。"""

    def test_organ_protocol_isinstance(self) -> None:
        assert isinstance(_ValidOrgan(), OrganProtocol)
        assert not isinstance(_InvalidOrgan(), OrganProtocol)

    # --- 逐一验证每个 Protocol 在其 dummy 实现上的 isinstance ----

    def test_graph_storage_checkable(self) -> None:
        class Dummy:
            async def load(self, cat_uid: str) -> dict: return {}
            async def save(self, cat_uid: str, data: dict) -> None: pass
        assert isinstance(Dummy(), GraphStorageProtocol)

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
            inject_cat_self: bool = True
            async def process(self, msg: str) -> str: return ""
            async def process_stream(self, msg: str): yield {}
            def build_system_prompt(
                self, organ: str, route: str, cat_self_snapshot=None) -> str: return ""

            def cancel_current(self) -> bool: return False
        assert isinstance(Dummy(), BrainStemProtocol)

    def test_hippocampus_checkable(self) -> None:
        class Dummy:
            entities: dict = {}
            episodes: list = []
            async def remember(self, u, a, c, m): pass
            def decay(self, now=None) -> int: return 0
            def add_episode(self, ep) -> str: return ""
            def get_episode(self, eid): pass
            def get_episodes(self, ids) -> list: return []
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
            def record_access(self, eid, delta=1) -> None: pass
            def set_dormant(self, eid, dormant) -> None: pass
            def append_content(self, eid, text, max_total=None) -> None: pass
            def update_importance(self, eid, importance) -> None: pass
            def set_last_seen(self, eid, ts) -> None: pass
            def list_active_workflows(self, cat_uid) -> list: return []
            def set_colony_memory(self, memory_pool) -> None: pass
            def snapshot(self, *topics, scope="colony") -> dict: return {}
            def locate(self, query, scope="self") -> list: return []
            def get_tree(self, entity_id): return None
            def build_tree(self, entity_id, root): return 0
            def delete_tree(self, entity_id) -> None: pass
            def search_tree(self, entity_id, keyword, limit=5): return []
            def query_subtree(self, entity_id, node_id, max_depth=2): return []
            def check_stale(self, entity_id): return []
        assert isinstance(Dummy(), HippocampusProtocol)

    def test_thalamus_checkable(self) -> None:
        class Dummy:
            async def hear(self, raw_input: str | bytes) -> dict: return {}
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
            def fast_pass(self, msg: str) -> dict: return None
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
            def detect_blind_spot(self, queries, known=None) -> list: return []
        assert isinstance(Dummy(), WhiskersProtocol)

    def test_paws_checkable(self) -> None:
        class Dummy:
            name: str = "paws"
            async def execute(self, tool_name, params) -> dict: return {}
            def on_tool_failure(self, tool, params, error,
                                elapsed=0) -> dict: return {}

            async def touch_file(self, path, content=None) -> dict: return {}
            async def run_command(self, cmd, **kw) -> dict: return {}
            async def interact_with_tool(self, sn, params) -> dict: return {}
        assert isinstance(Dummy(), PawsProtocol)

    def test_stage_checkable(self) -> None:
        assert isinstance(_ValidStage(), StageProtocol)

        class Bad:
            name: str = "bad"
        assert not isinstance(Bad(), StageProtocol)

    def test_kitten_checkable(self) -> None:
        """KittenProtocol 降级为纯文档，isinstance 检测移除。"""
        from typing import Protocol
        assert issubclass(KittenProtocol, Protocol)

    def test_cat_protocol_checkable(self) -> None:
        class Dummy:
            cat_uid: str = "cat"
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
