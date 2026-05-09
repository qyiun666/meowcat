# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat 独立测试: 所有 Protocol 可 import + isinstance 校验。

验证:
- 每个 @runtime_checkable Protocol 都能正常 import
- Noop* 桩满足对应 Protocol
- CatProtocol 包含 v0.2.0 新增 API（turn、process_message 等）
"""

from __future__ import annotations

import pytest

from meowcat.defaults.organs import (
    NoopAmygdala,
    NoopAnomalyGrowth,
    NoopCerebellum,
    NoopCerebrum,
    NoopCorrectionGrowth,
    NoopCortex,
    NoopCrystallizer,
    NoopEars,
    NoopEyes,
    NoopFrontal,
    NoopHypothalamus,
    NoopMouth,
    NoopPurr,
    NoopRoleEmergence,
    NoopTail,
    NoopWhiskers,
)
from meowcat.defaults.stores import InMemoryGraphStore
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


class TestNoopSatisfiesProtocol:
    """每个 Noop* 桩满足对应 Protocol 的 isinstance 校验。"""

    def test_noop_amygdala(self) -> None:
        a = NoopAmygdala()
        assert isinstance(a, AmygdalaProtocol)
        assert a.is_rejection("hello") is False
        assert a.classify_rejection("hello") == "none"
        assert a.parse_correction("hello") is None

    @pytest.mark.anyio
    async def test_noop_frontal(self) -> None:
        f = NoopFrontal()
        assert isinstance(f, FrontalCortexProtocol)
        assert await f.detect_shift("hello") is False
        assert await f.is_continue("hello") is False

    def test_noop_hypothalamus(self) -> None:
        h = NoopHypothalamus()
        assert isinstance(h, HypothalamusProtocol)

    def test_noop_cortex(self) -> None:
        c = NoopCortex()
        assert isinstance(c, CortexProtocol)

    @pytest.mark.anyio
    async def test_noop_ears(self) -> None:
        e = NoopEars()
        assert isinstance(e, EarsProtocol)
        assert e.extract_keywords("hello") == ["hello"]
        assert e.detect_language("hello") == "en"

    def test_noop_eyes(self) -> None:
        e = NoopEyes()
        assert isinstance(e, EyesProtocol)

    def test_noop_mouth(self) -> None:
        m = NoopMouth()
        assert isinstance(m, OrganProtocol)

    def test_noop_purr(self) -> None:
        p = NoopPurr()
        assert isinstance(p, OrganProtocol)

    def test_noop_tail(self) -> None:
        t = NoopTail()
        assert isinstance(t, OrganProtocol)

    def test_noop_whiskers(self) -> None:
        w = NoopWhiskers()
        assert isinstance(w, WhiskersProtocol)

    # -- v1.0.16: Growth + LLM organs ----------------------------------

    def test_noop_cerebrum(self) -> None:
        c = NoopCerebrum()
        assert isinstance(c, LLMBrainProtocol)
        assert c.name == "noop_cerebrum"
        assert c.diagnose() == {}
        c.reload_config()  # no-op

    def test_noop_cerebellum(self) -> None:
        c = NoopCerebellum()
        assert isinstance(c, LLMBrainProtocol)
        assert c.name == "noop_cerebellum"

    @pytest.mark.anyio
    async def test_noop_anomaly_growth(self) -> None:
        a = NoopAnomalyGrowth()
        assert isinstance(a, AnomalyGrowthProtocol)
        assert a.name == "noop_anomaly_growth"
        result = await a.record("drift", "snippet", 0.9)
        assert isinstance(result, dict)

    @pytest.mark.anyio
    async def test_noop_correction_growth(self) -> None:
        c = NoopCorrectionGrowth()
        assert isinstance(c, CorrectionGrowthProtocol)
        result = await c.record("wrong", "correct", session_id="s1")
        assert isinstance(result, dict)

    @pytest.mark.anyio
    async def test_noop_crystallizer(self) -> None:
        c = NoopCrystallizer()
        assert isinstance(c, CrystallizerProtocol)
        assert await c.crystallize("my_skill", 3) is False
        assert await c.hotspots(2) == []

    @pytest.mark.anyio
    async def test_noop_role_emergence(self) -> None:
        r = NoopRoleEmergence()
        assert isinstance(r, RoleEmergenceProtocol)
        result = await r.record("pattern_x", "evidence_y")
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
