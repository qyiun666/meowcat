"""meowcat 生物学默认神经通路表 + 默认反射弧 path。

定义"一只正常猫"的默认神经解剖结构。应用层调用
``CatBase.wire_default_nervous_system()`` 即可一键装配。

**生物学锚点**：

- 感官先经丘脑中继再入大脑（哺乳动物基本原则）
- 大脑不直连四肢——走大脑→小脑→肌肉（运动皮层→小脑）
- 杏仁核可绕开大脑直接触发效应器（应激反射）
- 下丘脑做稳态维护（衰减/清理）
- 脑干作为总调度，连接所有（bulbar crossroads）

**禁止边（FORBIDDEN）** 优先级高于允许边：
- ``cerebrum → paws`` ：大脑不直连四肢
- ``cerebrum → mouth``：大脑不直接驱动发声

本文件零第三方依赖，零 meowagent import。
"""

from __future__ import annotations

from typing import Final

from meowcat.wiring import Edge, Organ, Wiring

# -- 节点分类常量 -----------------------------------------------

BRAIN: Final[str] = "brain"
SENSE: Final[str] = "sense"
VOICE: Final[str] = "voice"
STORAGE: Final[str] = "storage"

# -- 关键器官坐标 -----------------------------------------------

THALAMUS: Final[Organ] = (BRAIN, "thalamus")
HIPPOCAMPUS: Final[Organ] = (BRAIN, "hippocampus")
CEREBRUM: Final[Organ] = (BRAIN, "cerebrum")
CEREBELLUM: Final[Organ] = (BRAIN, "cerebellum")
AMYGDALA: Final[Organ] = (BRAIN, "amygdala")
FRONTAL: Final[Organ] = (BRAIN, "frontal")
HYPOTHALAMUS: Final[Organ] = (BRAIN, "hypothalamus")
CORTEX: Final[Organ] = (BRAIN, "cortex")
BRAINSTEM: Final[Organ] = (BRAIN, "brainstem")

EARS: Final[Organ] = (SENSE, "ears")
EYES: Final[Organ] = (SENSE, "eyes")
WHISKERS: Final[Organ] = (SENSE, "whiskers")
PAWS: Final[Organ] = (SENSE, "paws")

MOUTH: Final[Organ] = (VOICE, "mouth")
PURR: Final[Organ] = (VOICE, "purr")
TAIL: Final[Organ] = (VOICE, "tail")

SENSORS: Final[tuple[Organ, ...]] = (EARS, EYES, WHISKERS)
VOICES: Final[tuple[Organ, ...]] = (MOUTH, PURR, TAIL)
EFFECTORS: Final[tuple[Organ, ...]] = (PAWS, MOUTH, PURR, TAIL)
BRAIN_REGIONS: Final[tuple[Organ, ...]] = (
    THALAMUS, HIPPOCAMPUS, CEREBRUM, CEREBELLUM,
    AMYGDALA, FRONTAL, HYPOTHALAMUS, CORTEX, BRAINSTEM,
)


def _make_default_allowed() -> list[Edge]:
    """构造默认允许边清单（去重由 set 保证）。"""
    edges: list[Edge] = []

    # 感官 → 丘脑（丘脑是感官中枢）
    for s in SENSORS:
        edges.append((s, THALAMUS))

    # 记忆回路：海马 ↔ 大脑皮层，海马 → 皮层（世界观）
    edges.append((HIPPOCAMPUS, CEREBRUM))
    edges.append((CEREBRUM, HIPPOCAMPUS))
    edges.append((HIPPOCAMPUS, CORTEX))

    # 运动回路：大脑 → 小脑 → 效应器
    edges.append((CEREBRUM, CEREBELLUM))
    for eff in EFFECTORS:
        edges.append((CEREBELLUM, eff))

    # 应激反射：杏仁核 → 小脑 / 嘴（绕开大脑）
    edges.append((AMYGDALA, CEREBELLUM))
    edges.append((AMYGDALA, MOUTH))

    # 稳态：下丘脑 → 下丘脑（自律维护）/ 海马 / 皮层
    edges.append((HYPOTHALAMUS, HYPOTHALAMUS))
    edges.append((HYPOTHALAMUS, HIPPOCAMPUS))
    edges.append((HYPOTHALAMUS, CORTEX))

    # 工作记忆：前额叶 ↔ 大脑，前额叶 → 海马（检索）
    edges.append((FRONTAL, CEREBRUM))
    edges.append((CEREBRUM, FRONTAL))
    edges.append((FRONTAL, HIPPOCAMPUS))

    # 脑干：总调度，可到所有脑区/感官/嗓音
    for target in (*BRAIN_REGIONS, *SENSORS, *VOICES):
        if target == BRAINSTEM:
            continue
        edges.append((BRAINSTEM, target))

    # 丘脑 → 大脑（路由后转高层），丘脑 → 脑干（回环）
    edges.append((THALAMUS, CEREBRUM))
    edges.append((THALAMUS, BRAINSTEM))
    edges.append((THALAMUS, AMYGDALA))  # 感官有威胁直连杏仁核

    return edges


def _make_default_forbidden() -> list[Edge]:
    """构造默认禁止边清单。"""
    forbid: list[Edge] = []
    # 生物学铁律：大脑不直连四肢/嘴（必须经小脑/脑干）
    forbid.append((CEREBRUM, PAWS))
    forbid.append((CEREBRUM, MOUTH))
    return forbid


BUILTIN_NERVOUS_SYSTEM: Final[tuple[Edge, ...]
                              ] = tuple(_make_default_allowed())
"""一张"正常猫"默认的允许边清单。"""

FORBIDDEN_PATHS: Final[tuple[Edge, ...]] = tuple(_make_default_forbidden())
"""默认禁止通路清单（优先级高于允许）。"""


def apply_default_wiring(wiring: Wiring) -> None:
    """把默认神经解剖装到 wiring 上。

    不 freeze，由调用方（通常是 ``CatBase.freeze_nervous_system``）决定时机。
    可重复调用，边表是 set 天然去重。
    """
    wiring.connect_many(BUILTIN_NERVOUS_SYSTEM)
    wiring.forbid_many(FORBIDDEN_PATHS)


# -- 分身猫 wiring 裁剪 ------------------------------------------------

KITTEN_FORBIDDEN_METHODS: Final[frozenset[str]] = frozenset({
    "spawn_kitten",
    "absorb_merge",
})
"""分身猫禁止调用的方法名集合。

由 ``KittenBase.signal()`` 校验——这些方法属于主猫专属能力，
分身猫调用直接抛 :class:`IllegalNeuralPathError`。

规则：
- ``spawn_kitten``: 分身猫不能递归派生下级 kitten
- ``absorb_merge``: 分身猫不能吸收合并（主猫专属）
"""


def apply_kitten_wiring(wiring: Wiring) -> None:
    """为分身猫装配受限神经通路表。

    在默认 wiring 基础上追加分身猫特有禁止边：
    - ``(brain,cerebrum) → (brain,hippocampus)`` 改单向（只读记忆），
      分身猫不改主猫记忆。

    注意：方法级限制（spawn_kitten / absorb_merge）不在此处校验，
    由 ``KittenBase.signal()`` 重写负责。
    """
    apply_default_wiring(wiring)
    # 分身猫额外禁止：大脑皮层不能写入海马体（只读记忆）
    # 注意：默认表里 cerebrum↔hippocampus 是双向的，
    # 分身猫只保留 hippocampus→cerebrum（读取方向）
    wiring.forbid(CEREBRUM, HIPPOCAMPUS)


# -- 默认反射弧 path（供 meowagent 构造 Reflex 时引用） ---------

DEFAULT_REFLEX_PATHS: Final[dict[str, tuple[Organ, ...]]] = {
    # 文本对话：耳朵 → 丘脑 → 脑干 → 大脑 →（经小脑）→ 嘴
    # 注意 path 只是"声明走过哪些器官"，实际 signal 调用仍逐跳校验
    "text_dialogue": (
        EARS, THALAMUS, BRAINSTEM, CEREBRUM, CEREBELLUM, MOUTH,
    ),
    # 视觉输入：眼睛 → 丘脑 → 大脑 →（经小脑）→ 嘴
    "visual": (
        EYES, THALAMUS, CEREBRUM, CEREBELLUM, MOUTH,
    ),
    # 危险应激：耳朵 → 丘脑 → 杏仁核 → 嘴（绕开大脑）
    "danger": (
        EARS, THALAMUS, AMYGDALA, MOUTH,
    ),
    # 动作命令：耳朵 → 丘脑 → 小脑 → 四肢（不经大脑，更快）
    # 注意：严肃场景下仍应经脑干+大脑裁决；这里是快速反射通路
    "action_order": (
        EARS, THALAMUS, CEREBELLUM, PAWS,
    ),
}


__all__ = [
    # 分类常量
    "BRAIN", "SENSE", "VOICE", "STORAGE",
    # 器官坐标
    "THALAMUS", "HIPPOCAMPUS", "CEREBRUM", "CEREBELLUM", "AMYGDALA",
    "FRONTAL", "HYPOTHALAMUS", "CORTEX", "BRAINSTEM",
    "EARS", "EYES", "WHISKERS", "PAWS",
    "MOUTH", "PURR", "TAIL",
    "SENSORS", "VOICES", "EFFECTORS", "BRAIN_REGIONS",
    # 表 + 装配函数
    "BUILTIN_NERVOUS_SYSTEM", "FORBIDDEN_PATHS",
    "apply_default_wiring",
    "apply_kitten_wiring", "KITTEN_FORBIDDEN_METHODS",
    "DEFAULT_REFLEX_PATHS",
]
