# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat 独立测试: 默认 wiring 表合法性 + 生物常数。

验证:
- BUILTIN_NERVOUS_SYSTEM 所有边两端器官在 BRAIN/SENSE/VOICE 中
- FORBIDDEN_PATHS 禁止脑直连四肢/嘴
- apply_default_wiring 可重复调用且去重

v0.5.21: DEFAULT_REFLEX_PATHS 和 Growth 测试已搬迁到 meowagent 测试。
v1.0.1: 移除 KITTEN_FORBIDDEN_METHODS / apply_kitten_wiring（KittenBase 已删除）。
"""

from __future__ import annotations

import pytest

from meowcat import biology
from meowcat.biology import (
    ANOMALY_GROWTH,
    BRAIN,
    BRAIN_REGIONS,
    BUILTIN_NERVOUS_SYSTEM,
    CORRECTION_GROWTH,
    CRYSTALLIZER,
    EFFECTORS,
    FORBIDDEN_PATHS,
    ROLE_EMERGENCE,
    SENSE,
    SENSORS,
    STORAGE,
    VOICE,
    VOICES,
    apply_default_wiring,
)
from meowcat.wiring import Wiring

_ALL_KNOWN = {*BRAIN_REGIONS, *SENSORS, *VOICES, *EFFECTORS,
              ANOMALY_GROWTH, CORRECTION_GROWTH, CRYSTALLIZER, ROLE_EMERGENCE}


class TestBiologyConstants:
    """生物常数不空、不重复。"""

    def test_brain_regions_not_empty(self) -> None:
        assert len(BRAIN_REGIONS) > 0

    def test_sensors_not_empty(self) -> None:
        assert len(SENSORS) > 0

    def test_voices_not_empty(self) -> None:
        assert len(VOICES) > 0

    def test_category_constants_are_strings(self) -> None:
        assert BRAIN == "brain"
        assert SENSE == "sense"
        assert VOICE == "voice"
        assert STORAGE == "storage"


class TestBuiltinNervousSystem:
    """BUILTIN_NERVOUS_SYSTEM 合法性。"""

    def test_all_edges_have_known_nodes(self) -> None:
        for frm, to in BUILTIN_NERVOUS_SYSTEM:
            assert frm in _ALL_KNOWN, f"Unknown from_organ: {frm}"
            assert to in _ALL_KNOWN, f"Unknown to_organ: {to}"

    def test_sensory_to_thalamus_exists(self) -> None:
        """所有感官 → 丘脑 的边必须存在。"""
        edges = set(BUILTIN_NERVOUS_SYSTEM)
        for sensor in SENSORS:
            assert (sensor, biology.THALAMUS) in edges, \
                f"Missing: {sensor} → thalamus"

    def test_cerebrum_to_paws_forbidden(self) -> None:
        """cerebrum→paws 必须在 FORBIDDEN_PATHS 中。"""
        assert (biology.CEREBRUM, biology.PAWS) in set(FORBIDDEN_PATHS)

    def test_cerebrum_to_mouth_forbidden(self) -> None:
        """cerebrum→mouth 必须在 FORBIDDEN_PATHS 中。"""
        assert (biology.CEREBRUM, biology.MOUTH) in set(FORBIDDEN_PATHS)

    def test_brainstem_to_all_exists(self) -> None:
        """脑干 → 所有脑区/感官/嗓音（除自己）的边必须存在。"""
        edges = set(BUILTIN_NERVOUS_SYSTEM)
        for target in (*BRAIN_REGIONS, *SENSORS, *VOICES):
            if target == biology.BRAINSTEM:
                continue
            assert (biology.BRAINSTEM, target) in edges, \
                f"Missing: brainstem → {target}"


class TestApplyDefaultWiring:
    """apply_default_wiring 正确装配。"""

    def test_apply_adds_edges(self) -> None:
        w = Wiring()
        apply_default_wiring(w)
        assert len(w.edges()) > 0
        assert len(w.forbids()) > 0

    def test_apply_is_idempotent(self) -> None:
        w = Wiring()
        apply_default_wiring(w)
        before_edges = len(w.edges())
        before_forbids = len(w.forbids())
        apply_default_wiring(w)
        assert len(w.edges()) == before_edges  # set 天然去重
        assert len(w.forbids()) == before_forbids

    def test_apply_does_not_freeze(self) -> None:
        w = Wiring()
        apply_default_wiring(w)
        assert not w.frozen


# -- from v0.5.1: 补充器官坐标 / 默认 wiring 契约测试 -----------


class TestOrganCoordinates:
    """v0.5.1: 器官坐标非空 str、分类正确、不悬空。"""

    @pytest.mark.parametrize("organ", [
        biology.THALAMUS, biology.HIPPOCAMPUS, biology.CEREBRUM,
        biology.CEREBELLUM, biology.AMYGDALA,
        biology.FRONTAL, biology.HYPOTHALAMUS, biology.CORTEX,
        biology.BRAINSTEM,
        biology.EARS, biology.EYES, biology.WHISKERS, biology.PAWS,
        biology.MOUTH, biology.PURR, biology.TAIL,
    ])
    def test_organ_tuple_non_empty_strings(self, organ) -> None:
        assert isinstance(organ, tuple)
        assert len(organ) == 2
        assert isinstance(organ[0], str) and len(organ[0]) > 0
        assert isinstance(organ[1], str) and len(organ[1]) > 0

    def test_brain_regions_contains_all_brain_organs(self) -> None:
        brain_organs = {
            biology.THALAMUS, biology.HIPPOCAMPUS, biology.CEREBRUM,
            biology.CEREBELLUM,
            biology.AMYGDALA, biology.FRONTAL, biology.HYPOTHALAMUS,
            biology.CORTEX, biology.BRAINSTEM,
        }
        assert set(biology.BRAIN_REGIONS) == brain_organs

    def test_sensors_contains_ears_eyes_whiskers(self) -> None:
        assert set(biology.SENSORS) == {
            biology.EARS, biology.EYES, biology.WHISKERS}

    def test_voices_contains_mouth_purr_tail(self) -> None:
        assert set(biology.VOICES) == {
            biology.MOUTH, biology.PURR, biology.TAIL}

    def test_effectors_contains_paws_mouth_purr_tail(self) -> None:
        assert set(biology.EFFECTORS) == {
            biology.PAWS, biology.MOUTH, biology.PURR, biology.TAIL,
        }


class TestDefaultWiring:
    """v0.5.1: BUILTIN_NERVOUS_SYSTEM / FORBIDDEN_PATHS / apply_default_wiring。"""

    def test_builtin_nervous_system_not_empty(self) -> None:
        assert len(biology.BUILTIN_NERVOUS_SYSTEM) > 0

    def test_builtin_edges_are_valid_pairs(self) -> None:
        for frm, to in biology.BUILTIN_NERVOUS_SYSTEM:
            assert isinstance(frm, tuple) and len(frm) == 2
            assert isinstance(to, tuple) and len(to) == 2
            assert frm[0] and frm[1] and to[0] and to[1]

    def test_forbidden_paths_not_empty(self) -> None:
        assert len(biology.FORBIDDEN_PATHS) > 0

    def test_apply_default_wiring(self) -> None:
        w = Wiring()
        biology.apply_default_wiring(w)

        # 感官 → 丘脑 连通
        assert w.is_allowed(biology.EARS, biology.THALAMUS)
        assert w.is_allowed(biology.EYES, biology.THALAMUS)

        # 海马 ↔ 大脑 双向
        assert w.is_allowed(biology.HIPPOCAMPUS, biology.CEREBRUM)
        assert w.is_allowed(biology.CEREBRUM, biology.HIPPOCAMPUS)

        # 大脑 → 小脑 → paws
        assert w.is_allowed(biology.CEREBRUM, biology.CEREBELLUM)
        assert w.is_allowed(biology.CEREBELLUM, biology.PAWS)

        # 禁止：大脑不直连四肢/嘴
        assert not w.is_allowed(biology.CEREBRUM, biology.PAWS)
        assert not w.is_allowed(biology.CEREBRUM, biology.MOUTH)

        # 脑干可到各处脑区
        assert w.is_allowed(biology.BRAINSTEM, biology.THALAMUS)
        assert w.is_allowed(biology.BRAINSTEM, biology.CEREBELLUM)

    def test_forbidden_overrides_allowed_in_default(self) -> None:
        w = Wiring()
        w.connect(biology.CEREBRUM, biology.PAWS)
        w.forbid(biology.CEREBRUM, biology.PAWS)
        assert not w.is_allowed(biology.CEREBRUM, biology.PAWS)

    def test_apply_default_wiring_is_idempotent(self) -> None:
        w = Wiring()
        biology.apply_default_wiring(w)
        allowed_before = len(w.edges())
        biology.apply_default_wiring(w)
        assert len(w.edges()) == allowed_before  # set 去重
