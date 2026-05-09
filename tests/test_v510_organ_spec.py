# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""v0.5.10 — OrganSpec 结构单测 + 聚合函数覆盖。

验证 ORGAN_SPECS 的结构性约束：坐标唯一、protocol 合法、聚合函数
与手工汇总一致、frozen dataclass 不可变。
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from meowcat.anatomy import (
    AMYGDALA,
    ANOMALY_GROWTH,
    BRAINSTEM,
    CEREBELLUM,
    CEREBRUM,
    CORRECTION_GROWTH,
    CORTEX,
    CRYSTALLIZER,
    EARS,
    EFFECTORS,
    EYES,
    FRONTAL,
    HIPPOCAMPUS,
    HYPOTHALAMUS,
    MOUTH,
    PAWS,
    PURR,
    ROLE_EMERGENCE,
    SENSORS,
    TAIL,
    THALAMUS,
    VOICES,
    WHISKERS,
)
from meowcat.biology import (
    BUILTIN_NERVOUS_SYSTEM,
    ORGAN_PROTOCOLS,
    ORGAN_SPECS,
    OrganSpec,
    _aggregate_edges,
)

# -- 结构性约束 --------------------------------------------------

def test_organ_specs_count_matches_organ_protocols() -> None:
    """每条 spec 对应一个 Protocol，数量一致。"""
    assert len(ORGAN_SPECS) == 20
    # v1.0.7: MOUTH/PURR/TAIL now have protocols, count = 20
    assert len(ORGAN_PROTOCOLS) == 20


def test_organ_specs_coords_unique() -> None:
    """每个器官坐标只能出现一次。"""
    coords = [s.coord for s in ORGAN_SPECS]
    assert len(coords) == len(set(coords)), f"duplicate coords: {coords}"


def test_organ_specs_cover_all_known_organs() -> None:
    """ORGAN_SPECS 覆盖所有已知器官坐标。"""
    expected = {
        THALAMUS, HIPPOCAMPUS, CEREBRUM, CEREBELLUM, AMYGDALA,
        FRONTAL, HYPOTHALAMUS, CORTEX, BRAINSTEM,
        EARS, EYES, WHISKERS, PAWS,
        MOUTH, PURR, TAIL,
        ANOMALY_GROWTH, CORRECTION_GROWTH, CRYSTALLIZER, ROLE_EMERGENCE,
    }
    actual = {s.coord for s in ORGAN_SPECS}
    assert actual == expected


def test_organ_specs_frozen() -> None:
    """OrganSpec 是 frozen dataclass，禁止修改。"""
    spec = ORGAN_SPECS[0]
    with pytest.raises(FrozenInstanceError):
        spec.coord = ("brain", "other")  # type: ignore[misc]


def test_organ_specs_default_empty_edges() -> None:
    """OrganSpec 默认 in_edges/out_edges 为空元组。"""
    from meowcat.protocols import OrganProtocol
    spec = OrganSpec(coord=("x", "y"), protocol=OrganProtocol)
    assert spec.in_edges == ()
    assert spec.out_edges == ()


# -- 聚合函数正确性 ----------------------------------------------

def test_aggregate_edges_idempotent() -> None:
    """_aggregate_edges() 多次调用结果一致。"""
    a = _aggregate_edges()
    b = _aggregate_edges()
    assert a == b


def test_aggregate_edges_equals_module_constant() -> None:
    """模块级 BUILTIN_NERVOUS_SYSTEM 等于聚合函数返回值。"""
    assert tuple(BUILTIN_NERVOUS_SYSTEM) == _aggregate_edges()


def test_aggregate_edges_manual_sample() -> None:
    """抽样校验：手动列出每个 spec 的 (src, self) + (self, dst) 边 = 聚合结果。"""
    expected: set[tuple[tuple[str, str], tuple[str, str]]] = set()
    for s in ORGAN_SPECS:
        for src in s.in_edges:
            expected.add((src, s.coord))
        for dst in s.out_edges:
            expected.add((s.coord, dst))
    assert frozenset(BUILTIN_NERVOUS_SYSTEM) == frozenset(expected)


def test_aggregate_edges_sorted() -> None:
    """BUILTIN_NERVOUS_SYSTEM 稳定排序（便于快照比对）。"""
    assert list(BUILTIN_NERVOUS_SYSTEM) == sorted(BUILTIN_NERVOUS_SYSTEM)


# -- Protocol 映射一致性 -----------------------------------------

def test_organ_protocols_derived_from_specs() -> None:
    """ORGAN_PROTOCOLS 与 ORGAN_SPECS 中非 None protocol 完全一致。"""
    expected = {
        s.coord: s.protocol for s in ORGAN_SPECS if s.protocol is not None}
    assert expected == ORGAN_PROTOCOLS


# -- 生物学合理性抽查 --------------------------------------------

def test_cerebellum_reaches_all_effectors() -> None:
    """小脑可达所有效应器（paws/mouth/purr/tail）。"""
    cerebellum_spec = next(s for s in ORGAN_SPECS if s.coord == CEREBELLUM)
    assert set(cerebellum_spec.out_edges) == set(EFFECTORS)


def test_all_sensors_go_to_thalamus() -> None:
    """耳/眼/触须的出边都包含丘脑。v1.0.8 新增应激反射直连杏仁核。"""
    for sensor in SENSORS:
        spec = next(s for s in ORGAN_SPECS if s.coord == sensor)
        assert THALAMUS in spec.out_edges, (
            f"{sensor} out_edges={spec.out_edges} missing THALAMUS"
        )


def test_brainstem_reaches_all_brain_sensor_voice() -> None:
    """脑干作为总调度到所有脑区（除自己）、所有感官、所有嗓音。"""
    spec = next(s for s in ORGAN_SPECS if s.coord == BRAINSTEM)
    # 脑干不连自己
    assert BRAINSTEM not in spec.out_edges
    # 覆盖所有其他脑区
    other_brain = {THALAMUS, HIPPOCAMPUS, CEREBRUM, CEREBELLUM,
                   AMYGDALA, FRONTAL, HYPOTHALAMUS, CORTEX}
    assert other_brain <= set(spec.out_edges)
    # 覆盖所有感官和嗓音
    assert set(SENSORS) <= set(spec.out_edges)
    assert set(VOICES) <= set(spec.out_edges)


def test_paws_has_no_outbound_edge() -> None:
    """PAWS 是纯效应器，没有出边（不会向外主动调用）。"""
    spec = next(s for s in ORGAN_SPECS if s.coord == PAWS)
    assert spec.out_edges == ()


def test_cortex_has_no_outbound_edge() -> None:
    """皮层是只读终点（由 hippocampus/hypothalamus/brainstem 写入）。"""
    spec = next(s for s in ORGAN_SPECS if s.coord == CORTEX)
    assert spec.out_edges == ()


def test_hypothalamus_self_loop_exists() -> None:
    """下丘脑有自环（稳态维护）。"""
    spec = next(s for s in ORGAN_SPECS if s.coord == HYPOTHALAMUS)
    assert HYPOTHALAMUS in spec.out_edges

