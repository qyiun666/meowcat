"""meowcat 解剖坐标 — 器官位置的单一源真相。

本模块只定义"器官叫什么、挂在哪个分类下"，零业务语义、零依赖
（仅 import ``Organ`` 类型别名）。biology.py 和 protocols.py 都从这里
import 坐标常量，打破 biology ↔ protocols 的循环依赖。

本文件零第三方依赖，零 meowagent import。
"""

from __future__ import annotations

from typing import Final

from meowcat.wiring import Organ

# -- 节点分类常量 -----------------------------------------------

BRAIN: Final[str] = "brain"
SENSE: Final[str] = "sense"
VOICE: Final[str] = "voice"
STORAGE: Final[str] = "storage"
GROWTH: Final[str] = "growth"

# -- 脑区坐标 ---------------------------------------------------

THALAMUS: Final[Organ] = (BRAIN, "thalamus")
HIPPOCAMPUS: Final[Organ] = (BRAIN, "hippocampus")
CEREBRUM: Final[Organ] = (BRAIN, "cerebrum")
CEREBELLUM: Final[Organ] = (BRAIN, "cerebellum")
AMYGDALA: Final[Organ] = (BRAIN, "amygdala")
FRONTAL: Final[Organ] = (BRAIN, "frontal")
HYPOTHALAMUS: Final[Organ] = (BRAIN, "hypothalamus")
CORTEX: Final[Organ] = (BRAIN, "cortex")
BRAINSTEM: Final[Organ] = (BRAIN, "brainstem")

# -- 感官坐标 ---------------------------------------------------

EARS: Final[Organ] = (SENSE, "ears")
EYES: Final[Organ] = (SENSE, "eyes")
WHISKERS: Final[Organ] = (SENSE, "whiskers")
PAWS: Final[Organ] = (SENSE, "paws")

# -- 嗓音坐标 ---------------------------------------------------

MOUTH: Final[Organ] = (VOICE, "mouth")
PURR: Final[Organ] = (VOICE, "purr")
TAIL: Final[Organ] = (VOICE, "tail")

# -- 生长坐标（v0.5.15 闭环 C）-----------------------------------

ANOMALY_GROWTH: Final[Organ] = (GROWTH, "anomaly_growth")
CORRECTION_GROWTH: Final[Organ] = (GROWTH, "correction_growth")
CRYSTALLIZER: Final[Organ] = (GROWTH, "crystallizer")
ROLE_EMERGENCE: Final[Organ] = (GROWTH, "role_emergence")

# -- 聚合元组 ---------------------------------------------------
#
# SENSORS 是"感知输入器官"（耳/眼/触须），PAWS 虽在 sense 分类下但属于
# 执行输出（EFFECTORS），不纳入 SENSORS。这一语义约定与 v0.5.9 保持一致，
# 是通路表（brainstem → sensors 而非 paws）正确生成的前提。

SENSORS: Final[tuple[Organ, ...]] = (EARS, EYES, WHISKERS)
VOICES: Final[tuple[Organ, ...]] = (MOUTH, PURR, TAIL)
EFFECTORS: Final[tuple[Organ, ...]] = (PAWS, MOUTH, PURR, TAIL)
BRAIN_REGIONS: Final[tuple[Organ, ...]] = (
    THALAMUS, HIPPOCAMPUS, CEREBRUM, CEREBELLUM,
    AMYGDALA, FRONTAL, HYPOTHALAMUS, CORTEX, BRAINSTEM,
)

# -- Organ 名称 → 坐标反向映射 ----------------------------------
# 供 YAML / 配置文件通过字符串名称引用 Organ 坐标使用。

ORGAN_BY_NAME: Final[dict[str, Organ]] = {
    # 脑区
    "thalamus": THALAMUS,
    "hippocampus": HIPPOCAMPUS,
    "cerebrum": CEREBRUM,
    "cerebellum": CEREBELLUM,
    "amygdala": AMYGDALA,
    "frontal": FRONTAL,
    "hypothalamus": HYPOTHALAMUS,
    "cortex": CORTEX,
    "brainstem": BRAINSTEM,
    # 感官
    "ears": EARS,
    "eyes": EYES,
    "whiskers": WHISKERS,
    "paws": PAWS,
    # 嗓音
    "mouth": MOUTH,
    "purr": PURR,
    "tail": TAIL,
    # 生长
    "anomaly_growth": ANOMALY_GROWTH,
    "correction_growth": CORRECTION_GROWTH,
    "crystallizer": CRYSTALLIZER,
    "role_emergence": ROLE_EMERGENCE,
}


__all__ = [
    # 分类常量
    "BRAIN", "SENSE", "VOICE", "STORAGE", "GROWTH",
    # 脑区坐标
    "THALAMUS", "HIPPOCAMPUS", "CEREBRUM", "CEREBELLUM", "AMYGDALA",
    "FRONTAL", "HYPOTHALAMUS", "CORTEX", "BRAINSTEM",
    # 感官坐标
    "EARS", "EYES", "WHISKERS", "PAWS",
    # 嗓音坐标
    "MOUTH", "PURR", "TAIL",
    # 生长坐标
    "ANOMALY_GROWTH", "CORRECTION_GROWTH", "CRYSTALLIZER", "ROLE_EMERGENCE",
    # 聚合元组
    "SENSORS", "VOICES", "EFFECTORS", "BRAIN_REGIONS",
    # Organ 名称 → 坐标
    "ORGAN_BY_NAME",
]
