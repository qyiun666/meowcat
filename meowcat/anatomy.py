"""meowcat anatomical coordinates — single source of truth for organ positions.

This module only defines "what organs are called and what category they belong to",
with zero business semantics, zero dependencies (only imports ``Organ`` type alias).
Both biology.py and protocols.py import coordinate constants from here,
breaking the biology ↔ protocols circular dependency.

This file has zero third-party dependencies, zero meowagent imports.
"""
# (c) 2025-2026 Axonant. MIT License.


from __future__ import annotations

from enum import Enum
from typing import Final

from meowcat.wiring import Organ


class ImplementationStyle(str, Enum):
    """器官内部实现风格 — 插头类型.

    - ALGORITHM: 纯算法 (正则, 字典查找, 字符串处理)
    - RULE:      声明式规则 (黑白名单, 阈值触发)
    - MODEL:     ML模型 (LLM, 分类器, 嵌入)
    - HYBRID:    混合 (算法 + 模型组合)

    器官 = 插槽 (入口出口 Protocol), 实现 = 插头 (任选风格).
    """
    ALGORITHM = "algorithm"
    RULE = "rule"
    MODEL = "model"
    HYBRID = "hybrid"

# -- Node category constants -----------------------------------------------

BRAIN: Final[str] = "brain"
SENSE: Final[str] = "sense"
VOICE: Final[str] = "voice"
STORAGE: Final[str] = "storage"
GROWTH: Final[str] = "growth"

# -- Brain region coordinates ---------------------------------------------------

THALAMUS: Final[Organ] = (BRAIN, "thalamus")
HIPPOCAMPUS: Final[Organ] = (BRAIN, "hippocampus")
CEREBRUM: Final[Organ] = (BRAIN, "cerebrum")
CEREBELLUM: Final[Organ] = (BRAIN, "cerebellum")
AMYGDALA: Final[Organ] = (BRAIN, "amygdala")
FRONTAL: Final[Organ] = (BRAIN, "frontal")
HYPOTHALAMUS: Final[Organ] = (BRAIN, "hypothalamus")
CORTEX: Final[Organ] = (BRAIN, "cortex")
BRAINSTEM: Final[Organ] = (BRAIN, "brainstem")

# -- Sense coordinates ---------------------------------------------------

EARS: Final[Organ] = (SENSE, "ears")
EYES: Final[Organ] = (SENSE, "eyes")
WHISKERS: Final[Organ] = (SENSE, "whiskers")
PAWS: Final[Organ] = (SENSE, "paws")

# -- Voice coordinates ---------------------------------------------------

MOUTH: Final[Organ] = (VOICE, "mouth")
PURR: Final[Organ] = (VOICE, "purr")
TAIL: Final[Organ] = (VOICE, "tail")

# -- Growth coordinates (v0.5.15 Loop C)-----------------------------------

ANOMALY_GROWTH: Final[Organ] = (GROWTH, "anomaly_growth")
CORRECTION_GROWTH: Final[Organ] = (GROWTH, "correction_growth")
CRYSTALLIZER: Final[Organ] = (GROWTH, "crystallizer")
ROLE_EMERGENCE: Final[Organ] = (GROWTH, "role_emergence")

# -- Aggregate tuples ---------------------------------------------------
#
# SENSORS are "sensory input organs" (ears/eyes/whiskers); PAWS, though in the
# sense category, is an execution output (EFFECTORS) and not included in SENSORS.
# This semantic convention matches v0.5.9 and is the prerequisite for correctly
# generating the pathway table (brainstem → sensors, not paws).

SENSORS: Final[tuple[Organ, ...]] = (EARS, EYES, WHISKERS)
VOICES: Final[tuple[Organ, ...]] = (MOUTH, PURR, TAIL)
EFFECTORS: Final[tuple[Organ, ...]] = (PAWS, MOUTH, PURR, TAIL)
BRAIN_REGIONS: Final[tuple[Organ, ...]] = (
    THALAMUS, HIPPOCAMPUS, CEREBRUM, CEREBELLUM,
    AMYGDALA, FRONTAL, HYPOTHALAMUS, CORTEX, BRAINSTEM,
)

# -- Organ name → coordinate reverse mapping ----------------------------------
# For referencing Organ coordinates by string name in YAML / config files.

ORGAN_BY_NAME: Final[dict[str, Organ]] = {
    # brain regions
    "thalamus": THALAMUS,
    "hippocampus": HIPPOCAMPUS,
    "cerebrum": CEREBRUM,
    "cerebellum": CEREBELLUM,
    "amygdala": AMYGDALA,
    "frontal": FRONTAL,
    "hypothalamus": HYPOTHALAMUS,
    "cortex": CORTEX,
    "brainstem": BRAINSTEM,
    # senses
    "ears": EARS,
    "eyes": EYES,
    "whiskers": WHISKERS,
    "paws": PAWS,
    # voices
    "mouth": MOUTH,
    "purr": PURR,
    "tail": TAIL,
    # growth
    "anomaly_growth": ANOMALY_GROWTH,
    "correction_growth": CORRECTION_GROWTH,
    "crystallizer": CRYSTALLIZER,
    "role_emergence": ROLE_EMERGENCE,
}


__all__ = [
    "ImplementationStyle",
    # category constants
    "BRAIN", "SENSE", "VOICE", "STORAGE", "GROWTH",
    # brain region coordinates
    "THALAMUS", "HIPPOCAMPUS", "CEREBRUM", "CEREBELLUM", "AMYGDALA",
    "FRONTAL", "HYPOTHALAMUS", "CORTEX", "BRAINSTEM",
    # sense coordinates
    "EARS", "EYES", "WHISKERS", "PAWS",
    # voice coordinates
    "MOUTH", "PURR", "TAIL",
    # growth coordinates
    "ANOMALY_GROWTH", "CORRECTION_GROWTH", "CRYSTALLIZER", "ROLE_EMERGENCE",
    # aggregate tuples
    "SENSORS", "VOICES", "EFFECTORS", "BRAIN_REGIONS",
    # Organ name → coordinate
    "ORGAN_BY_NAME",
]
