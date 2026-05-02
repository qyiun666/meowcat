"""v0.5.10 — 黄金集合等价性校验。

从 v0.5.9 的 ``_make_default_allowed()`` 一次性导出的边集合固化到本文件，
作为 v0.5.10 重构后 ``BUILTIN_NERVOUS_SYSTEM`` 必须精确匹配的"焊点"。

任何对 ``ORGAN_SPECS`` 的调整，如果改变了默认 wiring 形状，都会在此测试
立刻暴露——由开发者明确决定是接受并更新黄金集合，还是回退。
"""

from __future__ import annotations

from meowcat.biology import (
    BUILTIN_NERVOUS_SYSTEM,
    FORBIDDEN_PATHS,
    ORGAN_PROTOCOLS,
)

# -- v0.5.9 黄金边集合 -----------------------------------------

GOLDEN_BUILTIN_V059: frozenset[tuple[tuple[str, str], tuple[str, str]]] = frozenset([
    # amygdala 出边
    (("brain", "amygdala"), ("brain", "cerebellum")),
    (("brain", "amygdala"), ("brain", "cerebrum")),
    (("brain", "amygdala"), ("voice", "mouth")),
    # brainstem 出边（总调度）
    (("brain", "brainstem"), ("brain", "amygdala")),
    (("brain", "brainstem"), ("brain", "cerebellum")),
    (("brain", "brainstem"), ("brain", "cerebrum")),
    (("brain", "brainstem"), ("brain", "cortex")),
    (("brain", "brainstem"), ("brain", "frontal")),
    (("brain", "brainstem"), ("brain", "hippocampus")),
    (("brain", "brainstem"), ("brain", "hypothalamus")),
    (("brain", "brainstem"), ("brain", "thalamus")),
    # v0.5.29: growth organ edges
    (("brain", "brainstem"), ("growth", "anomaly_growth")),
    (("brain", "brainstem"), ("growth", "correction_growth")),
    (("brain", "brainstem"), ("growth", "crystallizer")),
    (("brain", "brainstem"), ("growth", "role_emergence")),
    (("brain", "brainstem"), ("sense", "ears")),
    (("brain", "brainstem"), ("sense", "eyes")),
    (("brain", "brainstem"), ("sense", "whiskers")),
    (("brain", "brainstem"), ("voice", "mouth")),
    (("brain", "brainstem"), ("voice", "purr")),
    (("brain", "brainstem"), ("voice", "tail")),
    # cerebellum 出边（到效应器）
    (("brain", "cerebellum"), ("sense", "paws")),
    (("brain", "cerebellum"), ("voice", "mouth")),
    (("brain", "cerebellum"), ("voice", "purr")),
    (("brain", "cerebellum"), ("voice", "tail")),
    # cerebrum 出边
    (("brain", "cerebrum"), ("brain", "cerebellum")),
    (("brain", "cerebrum"), ("brain", "frontal")),
    (("brain", "cerebrum"), ("brain", "hippocampus")),
    # frontal 出边
    (("brain", "frontal"), ("brain", "cerebrum")),
    (("brain", "frontal"), ("brain", "hippocampus")),
    # v0.5.26: frontal → brainstem 中继通道
    (("brain", "frontal"), ("brain", "brainstem")),
    # hippocampus 出边
    (("brain", "hippocampus"), ("brain", "cerebrum")),
    (("brain", "hippocampus"), ("brain", "cortex")),
    # hypothalamus 出边（含自环）
    (("brain", "hypothalamus"), ("brain", "cortex")),
    (("brain", "hypothalamus"), ("brain", "hippocampus")),
    (("brain", "hypothalamus"), ("brain", "hypothalamus")),
    # thalamus 出边
    (("brain", "thalamus"), ("brain", "amygdala")),
    (("brain", "thalamus"), ("brain", "brainstem")),
    (("brain", "thalamus"), ("brain", "cerebrum")),
    (("brain", "thalamus"), ("brain", "hippocampus")),
    # v0.5.29: growth organ out-edges
    (("growth", "anomaly_growth"), ("brain", "cortex")),
    (("growth", "anomaly_growth"), ("brain", "hippocampus")),
    (("growth", "correction_growth"), ("brain", "cortex")),
    (("growth", "correction_growth"), ("brain", "hippocampus")),
    # 感官入边（→丘脑）
    (("sense", "ears"), ("brain", "thalamus")),
    (("sense", "eyes"), ("brain", "thalamus")),
    (("sense", "whiskers"), ("brain", "thalamus")),
])

GOLDEN_FORBIDDEN_V059: frozenset[tuple[tuple[str, str], tuple[str, str]]] = frozenset([
    (("brain", "cerebrum"), ("sense", "paws")),
    (("brain", "cerebrum"), ("voice", "mouth")),
])

GOLDEN_ORGAN_PROTOCOLS_V059: dict[tuple[str, str], str] = {
    ("brain", "amygdala"): "AmygdalaProtocol",
    ("brain", "brainstem"): "BrainStemProtocol",
    ("brain", "cerebellum"): "LLMBrainProtocol",
    ("brain", "cerebrum"): "LLMBrainProtocol",
    ("brain", "cortex"): "CortexProtocol",
    ("brain", "frontal"): "FrontalCortexProtocol",
    ("brain", "hippocampus"): "HippocampusProtocol",
    ("brain", "hypothalamus"): "HypothalamusProtocol",
    ("brain", "thalamus"): "ThalamusProtocol",
    # v0.5.29: growth organ protocols
    ("growth", "anomaly_growth"): "GrowthProtocol",
    ("growth", "correction_growth"): "GrowthProtocol",
    ("growth", "crystallizer"): "GrowthProtocol",
    ("growth", "role_emergence"): "GrowthProtocol",
    ("sense", "ears"): "EarsProtocol",
    ("sense", "eyes"): "EyesProtocol",
    ("sense", "paws"): "PawsProtocol",
    ("sense", "whiskers"): "WhiskersProtocol",
}


# -- 等价性断言 --------------------------------------------------

def test_builtin_nervous_system_matches_v059_golden() -> None:
    """v0.5.10 聚合出的边集合必须精确等于 v0.5.9 手写的边集合。"""
    actual = frozenset(BUILTIN_NERVOUS_SYSTEM)
    missing = GOLDEN_BUILTIN_V059 - actual
    extra = actual - GOLDEN_BUILTIN_V059
    assert not missing, f"missing edges from v0.5.9 golden: {sorted(missing)}"
    assert not extra, f"extra edges not in v0.5.9 golden: {sorted(extra)}"
    assert actual == GOLDEN_BUILTIN_V059


def test_forbidden_paths_unchanged_from_v059() -> None:
    """FORBIDDEN_PATHS 保持与 v0.5.9 完全一致。"""
    assert frozenset(FORBIDDEN_PATHS) == GOLDEN_FORBIDDEN_V059


def test_organ_protocols_unchanged_from_v059() -> None:
    """ORGAN_PROTOCOLS 的 coord → Protocol 映射与 v0.5.9 完全一致。"""
    actual = {coord: proto.__name__ for coord,
              proto in ORGAN_PROTOCOLS.items()}
    assert actual == GOLDEN_ORGAN_PROTOCOLS_V059


def test_builtin_nervous_system_size_is_47() -> None:
    """v0.5.29: 47 条（新增 4 条 growth organ 入边 + 4 条出边），变化即信号。"""
    assert len(BUILTIN_NERVOUS_SYSTEM) == 47


def test_forbidden_paths_size_is_2() -> None:
    """v0.5.9 → v0.5.10 禁止边固定 2 条，变化即信号。"""
    assert len(FORBIDDEN_PATHS) == 2
