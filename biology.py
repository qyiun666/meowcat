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

**v0.5.10 通路元数据化**：每个器官的入/出边集中在 ``ORGAN_SPECS``
单源表里声明，``BUILTIN_NERVOUS_SYSTEM`` 和 ``ORGAN_PROTOCOLS`` 由该表
自动聚合得到。新增/迁移器官只改 ``ORGAN_SPECS`` 一处，避免边列表漂移。

本文件零第三方依赖，零 meowagent import。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

# 坐标常量从 anatomy.py re-export（对外 API 路径保持不变）
from meowcat.anatomy import (
    AMYGDALA,
    ANOMALY_GROWTH,
    BRAIN,
    BRAIN_REGIONS,
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
    GROWTH,
    HIPPOCAMPUS,
    HYPOTHALAMUS,
    MOUTH,
    PAWS,
    PURR,
    ROLE_EMERGENCE,
    SENSE,
    SENSORS,
    STORAGE,
    TAIL,
    THALAMUS,
    VOICE,
    VOICES,
    WHISKERS,
)
from meowcat.wiring import Edge, Organ, Wiring

if TYPE_CHECKING:
    pass


# -- 器官规范表（单源真相） ---------------------------------------

@dataclass(frozen=True)
class OrganSpec:
    """单个器官的解剖规范。

    每条记录声明一个器官：
    - ``coord``: 器官坐标（category, name）
    - ``protocol``: 该坐标对应的 Protocol 类型（runtime 校验用）
    - ``in_edges``: 入边——谁能调我（组合为 ``(src, self) in BUILTIN``）
    - ``out_edges``: 出边——我能调谁（组合为 ``(self, dst) in BUILTIN``）
    - ``read_methods``: 该器官声明的只读方法名（可选，用于文档/审计）
    - ``write_methods``: 该器官声明的写方法名（触发写权限校验）
    - ``write_callers``: 允许调用 write_methods 的器官（空=写校验不生效）

    方法级权限由 ``Nervous.signal()`` 在 wiring 校验后执行：
    ``from_organ not in write_callers`` 则抛 ``IllegalNeuralPathError``。

    新增/迁移器官只需改动本表一条记录，``BUILTIN_NERVOUS_SYSTEM`` 和
    ``ORGAN_PROTOCOLS`` 自动同步。
    """

    coord: Organ
    protocol: type
    in_edges: tuple[Organ, ...] = ()
    out_edges: tuple[Organ, ...] = ()
    read_methods: tuple[str, ...] = ()
    write_methods: tuple[str, ...] = ()
    write_callers: tuple[Organ, ...] = ()


def _build_organ_specs() -> tuple[OrganSpec, ...]:
    """构造 ORGAN_SPECS（惰性 import protocols，避免循环）。"""
    from meowcat.protocols import (  # noqa: PLC0415
        AmygdalaProtocol,
        BrainStemProtocol,
        CortexProtocol,
        EarsProtocol,
        EyesProtocol,
        FrontalCortexProtocol,
        GrowthProtocol,
        HippocampusProtocol,
        HypothalamusProtocol,
        LLMBrainProtocol,
        OrganProtocol,
        PawsProtocol,
        ThalamusProtocol,
        WhiskersProtocol,
    )
    return (
        # -- 脑区 ----------------------------------------------
        OrganSpec(
            coord=THALAMUS, protocol=ThalamusProtocol,
            in_edges=SENSORS,                              # 感官 → 丘脑
            out_edges=(CEREBRUM, BRAINSTEM, AMYGDALA,
                       HIPPOCAMPUS),  # 丘脑 → 大脑/脑干/杏仁核/海马
        ),
        OrganSpec(
            coord=HIPPOCAMPUS, protocol=HippocampusProtocol,
            in_edges=(CEREBRUM, FRONTAL, HYPOTHALAMUS, BRAINSTEM),
            out_edges=(CEREBRUM, CORTEX),
            read_methods=(
                "entities", "episodes",
                "locate", "get_entity", "get_all", "get_by_name",
                "get_related", "stats", "fts_search", "to_dict",
            ),
            write_methods=(
                "remember", "add_entity", "add_episode",
                "connect", "decay", "weaken_connections",
                "cleanup_orphan_connections", "from_dict",
                "record_access", "set_dormant", "append_content",
                "update_importance", "set_last_seen",
            ),
            write_callers=(BRAINSTEM, HYPOTHALAMUS),
        ),
        OrganSpec(
            coord=CEREBRUM, protocol=LLMBrainProtocol,
            in_edges=(THALAMUS, HIPPOCAMPUS, FRONTAL, BRAINSTEM),
            out_edges=(HIPPOCAMPUS, CEREBELLUM, FRONTAL),
        ),
        OrganSpec(
            coord=CEREBELLUM, protocol=LLMBrainProtocol,
            in_edges=(CEREBRUM, AMYGDALA, BRAINSTEM),
            out_edges=EFFECTORS,                           # paws/mouth/purr/tail
        ),
        OrganSpec(
            coord=AMYGDALA, protocol=AmygdalaProtocol,
            in_edges=(THALAMUS, BRAINSTEM),
            out_edges=(CEREBELLUM, MOUTH, CEREBRUM),       # 应激反射 + 安全推理
        ),
        OrganSpec(
            coord=FRONTAL, protocol=FrontalCortexProtocol,
            in_edges=(CEREBRUM, BRAINSTEM),
            out_edges=(CEREBRUM, HIPPOCAMPUS, BRAINSTEM),
        ),
        OrganSpec(
            coord=HYPOTHALAMUS, protocol=HypothalamusProtocol,
            in_edges=(BRAINSTEM,),
            out_edges=(HYPOTHALAMUS, HIPPOCAMPUS, CORTEX),  # 含自环
        ),
        OrganSpec(
            coord=CORTEX, protocol=CortexProtocol,
            in_edges=(HIPPOCAMPUS, HYPOTHALAMUS, BRAINSTEM),
            out_edges=(),
        ),
        OrganSpec(
            coord=BRAINSTEM, protocol=BrainStemProtocol,
            in_edges=(THALAMUS,),
            # 总调度：到所有脑区（除自己）/感官/嗓音；PAWS 不在此列
            # （brainstem→paws 边不存在于 v0.5.9 黄金集合，SENSORS 不含 PAWS）
            out_edges=(
                THALAMUS, HIPPOCAMPUS, CEREBRUM, CEREBELLUM,
                AMYGDALA, FRONTAL, HYPOTHALAMUS, CORTEX,
                ANOMALY_GROWTH, CORRECTION_GROWTH, CRYSTALLIZER, ROLE_EMERGENCE,
                *SENSORS, *VOICES,
            ),
        ),
        # -- 感官 ----------------------------------------------
        OrganSpec(
            coord=EARS, protocol=EarsProtocol,
            in_edges=(), out_edges=(THALAMUS,),
        ),
        OrganSpec(
            coord=EYES, protocol=EyesProtocol,
            in_edges=(), out_edges=(THALAMUS,),
        ),
        OrganSpec(
            coord=WHISKERS, protocol=WhiskersProtocol,
            in_edges=(), out_edges=(THALAMUS,),
        ),
        # PAWS 是效应器：仅 cerebellum→paws 一条入边（与 v0.5.9 一致）
        OrganSpec(
            coord=PAWS, protocol=PawsProtocol,
            in_edges=(CEREBELLUM,), out_edges=(),
        ),
        # -- 嗓音（弱约束效应器，protocol=None 不校验方法）-----
        OrganSpec(
            coord=MOUTH, protocol=None,
            in_edges=(CEREBELLUM, AMYGDALA, BRAINSTEM), out_edges=(),
        ),
        OrganSpec(
            coord=PURR, protocol=None,
            in_edges=(CEREBELLUM, BRAINSTEM), out_edges=(),
        ),
        OrganSpec(
            coord=TAIL, protocol=None,
            in_edges=(CEREBELLUM, BRAINSTEM), out_edges=(),
        ),
        # -- 生长器官（v0.5.29 meowcat 侧只声明，不实现）------
        OrganSpec(
            coord=ANOMALY_GROWTH, protocol=GrowthProtocol,
            in_edges=(BRAINSTEM,),
            out_edges=(HIPPOCAMPUS, CORTEX),
        ),
        OrganSpec(
            coord=CORRECTION_GROWTH, protocol=GrowthProtocol,
            in_edges=(BRAINSTEM,),
            out_edges=(HIPPOCAMPUS, CORTEX),
        ),
        OrganSpec(
            coord=CRYSTALLIZER, protocol=GrowthProtocol,
            in_edges=(BRAINSTEM,), out_edges=(),
        ),
        OrganSpec(
            coord=ROLE_EMERGENCE, protocol=GrowthProtocol,
            in_edges=(BRAINSTEM,), out_edges=(),
        ),
    )


ORGAN_SPECS: Final[tuple[OrganSpec, ...]] = _build_organ_specs()
"""一只"正常猫"的完整器官解剖规范表。

新增/迁移器官时只改此表一条记录，``BUILTIN_NERVOUS_SYSTEM`` 和
``ORGAN_PROTOCOLS`` 自动同步。
"""


# -- 从 ORGAN_SPECS 派生的只读视图 --------------------------------

ORGAN_PROTOCOLS: Final[dict[Organ, type]] = {
    s.coord: s.protocol for s in ORGAN_SPECS if s.protocol is not None
}
"""每个器官坐标对应的 Protocol 类型（由 ORGAN_SPECS 聚合生成）。

由 ``CatBase._assemble()`` 在自动挂载时读取，
应用层器官实现不满足 Protocol 时启动即失败。
"""


def _aggregate_edges() -> tuple[Edge, ...]:
    """从 ORGAN_SPECS 聚合所有默认允许边（去重 + 稳定排序）。"""
    edges: set[Edge] = set()
    for s in ORGAN_SPECS:
        for src in s.in_edges:
            edges.add((src, s.coord))
        for dst in s.out_edges:
            edges.add((s.coord, dst))
    return tuple(sorted(edges))


BUILTIN_NERVOUS_SYSTEM: Final[tuple[Edge, ...]] = _aggregate_edges()
"""一张"正常猫"默认的允许边清单（由 ORGAN_SPECS 聚合生成）。"""


# -- 禁止边（工程护栏，显式硬编码不走 OrganSpec） ---------------

FORBIDDEN_PATHS: Final[tuple[Edge, ...]] = (
    # cerebrum 不应产生副作用。所有 side effect 收拢到 cerebellum→effectors 管道，
    # 便于审计/拦截/mock
    (CEREBRUM, PAWS),
    # cerebrum 不应直接驱动发声。所有 side effect 收拢到 cerebellum→effectors 管道
    (CEREBRUM, MOUTH),
)
"""默认禁止通路清单（优先级高于允许边）。"""


# -- 装配函数 ----------------------------------------------------

def apply_default_wiring(wiring: Wiring) -> None:
    """把默认神经解剖装到 wiring 上。

    不 freeze，由调用方（通常是 ``CatBase.freeze_nervous_system``）决定时机。
    可重复调用，边表是 set 天然去重。
    """
    wiring.connect_many(BUILTIN_NERVOUS_SYSTEM)
    wiring.forbid_many(FORBIDDEN_PATHS)


__all__ = [
    # 分类常量（re-export from anatomy）
    "BRAIN", "SENSE", "VOICE", "STORAGE", "GROWTH",
    # 器官坐标（re-export from anatomy）
    "THALAMUS", "HIPPOCAMPUS", "CEREBRUM", "CEREBELLUM", "AMYGDALA",
    "FRONTAL", "HYPOTHALAMUS", "CORTEX", "BRAINSTEM",
    "EARS", "EYES", "WHISKERS", "PAWS",
    "ANOMALY_GROWTH", "CORRECTION_GROWTH",
    "CRYSTALLIZER", "ROLE_EMERGENCE",
    "MOUTH", "PURR", "TAIL",

    "SENSORS", "VOICES", "EFFECTORS", "BRAIN_REGIONS",
    # v0.5.10 器官规范表
    "OrganSpec", "ORGAN_SPECS",
    # 表 + 装配函数
    "BUILTIN_NERVOUS_SYSTEM", "FORBIDDEN_PATHS",
    "ORGAN_PROTOCOLS",
    "apply_default_wiring",


]
