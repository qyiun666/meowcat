"""meowcat 独立测试: 默认 wiring 表合法性 + 生物常数。

验证:
- BUILTIN_NERVOUS_SYSTEM 所有边两端器官在 BRAIN/SENSE/VOICE 中
- FORBIDDEN_PATHS 禁止脑直连四肢/嘴
- apply_default_wiring 可重复调用且去重

v0.5.21: DEFAULT_REFLEX_PATHS 和 Growth 测试已搬迁到 meowagent 测试。
v1.0.1: 移除 KITTEN_FORBIDDEN_METHODS / apply_kitten_wiring（KittenBase 已删除）。
"""

from __future__ import annotations

from meowcat import biology
from meowcat.biology import (
    BRAIN, SENSE, VOICE, STORAGE, GROWTH,
    ANOMALY_GROWTH, CORRECTION_GROWTH, CRYSTALLIZER, ROLE_EMERGENCE,
    BRAIN_REGIONS, SENSORS, VOICES, EFFECTORS,
    BUILTIN_NERVOUS_SYSTEM, FORBIDDEN_PATHS,
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
