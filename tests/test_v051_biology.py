"""
v0.5.1 Task 1.9e — biology 默认神经通路表契约测试
====================================================

契约类别：
    1. TestOrganCoordinates — 器官坐标完整性（非空、去重）
    2. TestDefaultWiring    — BUILTIN_NERVOUS_SYSTEM + FORBIDDEN_PATHS + apply_default_wiring

v0.5.21: TestDefaultReflexes 已搬迁到 meowagent 测试。

参考：docs/v0.5.1/design.md
"""

from __future__ import annotations

import pytest

from meowcat.biology import (
    AMYGDALA, BRAIN_REGIONS, BRAINSTEM, BUILTIN_NERVOUS_SYSTEM,
    CEREBELLUM, CEREBRUM, CORTEX,
    EARS, EFFECTORS, EYES, FORBIDDEN_PATHS, FRONTAL,
    HIPPOCAMPUS, HYPOTHALAMUS, MOUTH, PAWS, PURR, SENSORS,
    TAIL, THALAMUS, VOICES, WHISKERS,
    apply_default_wiring,
)
from meowcat.wiring import Wiring


# -- 1. 器官坐标 ---------------------------------------------------

class TestOrganCoordinates:
    """器官坐标非空 str、分类正确、不悬空。"""

    @pytest.mark.parametrize("organ", [
        THALAMUS, HIPPOCAMPUS, CEREBRUM, CEREBELLUM, AMYGDALA,
        FRONTAL, HYPOTHALAMUS, CORTEX, BRAINSTEM,
        EARS, EYES, WHISKERS, PAWS,
        MOUTH, PURR, TAIL,
    ])
    def test_organ_tuple_non_empty_strings(self, organ) -> None:
        assert isinstance(organ, tuple)
        assert len(organ) == 2
        assert isinstance(organ[0], str) and len(organ[0]) > 0
        assert isinstance(organ[1], str) and len(organ[1]) > 0

    def test_brain_regions_contains_all_brain_organs(self) -> None:
        brain_organs = {
            THALAMUS, HIPPOCAMPUS, CEREBRUM, CEREBELLUM,
            AMYGDALA, FRONTAL, HYPOTHALAMUS, CORTEX, BRAINSTEM,
        }
        assert set(BRAIN_REGIONS) == brain_organs

    def test_sensors_contains_ears_eyes_whiskers(self) -> None:
        assert set(SENSORS) == {EARS, EYES, WHISKERS}

    def test_voices_contains_mouth_purr_tail(self) -> None:
        assert set(VOICES) == {MOUTH, PURR, TAIL}

    def test_effectors_contains_paws_mouth_purr_tail(self) -> None:
        assert set(EFFECTORS) == {PAWS, MOUTH, PURR, TAIL}


# -- 2. 默认 wiring ------------------------------------------------

class TestDefaultWiring:
    """BUILTIN_NERVOUS_SYSTEM / FORBIDDEN_PATHS / apply_default_wiring。"""

    def test_builtin_nervous_system_not_empty(self) -> None:
        assert len(BUILTIN_NERVOUS_SYSTEM) > 0

    def test_builtin_edges_are_valid_pairs(self) -> None:
        for frm, to in BUILTIN_NERVOUS_SYSTEM:
            assert isinstance(frm, tuple) and len(frm) == 2
            assert isinstance(to, tuple) and len(to) == 2
            assert frm[0] and frm[1] and to[0] and to[1]

    def test_forbidden_paths_not_empty(self) -> None:
        assert len(FORBIDDEN_PATHS) > 0

    def test_apply_default_wiring(self) -> None:
        w = Wiring()
        apply_default_wiring(w)

        # 感官 → 丘脑 连通
        assert w.is_allowed(EARS, THALAMUS)
        assert w.is_allowed(EYES, THALAMUS)

        # 海马 ↔ 大脑 双向
        assert w.is_allowed(HIPPOCAMPUS, CEREBRUM)
        assert w.is_allowed(CEREBRUM, HIPPOCAMPUS)

        # 大脑 → 小脑 → paws
        assert w.is_allowed(CEREBRUM, CEREBELLUM)
        assert w.is_allowed(CEREBELLUM, PAWS)

        # 禁止：大脑不直连四肢/嘴
        assert not w.is_allowed(CEREBRUM, PAWS)
        assert not w.is_allowed(CEREBRUM, MOUTH)

        # 脑干可到各处脑区
        assert w.is_allowed(BRAINSTEM, THALAMUS)
        assert w.is_allowed(BRAINSTEM, CEREBELLUM)

    def test_forbidden_overrides_allowed_in_default(self) -> None:
        """即使默认表中 cerebrum→paws 在允许集之外，forbid 优先级更高。"""
        w = Wiring()
        # 手工 connect 一条"本不允许"的 + forbid 它，验证 forbid 优先
        w.connect(CEREBRUM, PAWS)
        w.forbid(CEREBRUM, PAWS)
        assert not w.is_allowed(CEREBRUM, PAWS)

    def test_apply_default_wiring_is_idempotent(self) -> None:
        w = Wiring()
        apply_default_wiring(w)
        allowed_before = len(w.edges())
        apply_default_wiring(w)
        assert len(w.edges()) == allowed_before  # set 去重
