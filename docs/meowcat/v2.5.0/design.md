# v2.5.0 设计文档 — Persona 面具系统

> 来源: `.qoder/plans/plan_2.5.0.md`

## 动机

当前框架中，外部 skill/agent 可以通过 `mount()` 或 `AgentOrgan` 接入单个器官。但当面对人格蒸馏产物时，问题浮现：

- 一个蒸馏 skill 包含 **性格 + 三观 + 自知 + 领域知识 + 行为模式 + 特殊能力** 六层
- 这六层对应四个不同器官：CatSelf、Cortex、Hippocampus、SkillRegistry
- 目前没有"一键换人设"的统一入口

## 设计目标

```
猫戴上「马斯克面具」
  → CatSelf: personality={tone:"visionary", language:"en+zh"}
  → Cortex: worldview 种子 "第一性原理"、"物理思维"
  → Hippocampus: 知识图谱种子 (SpaceX, Tesla, X平台)
  → SkillRegistry: X API tool, 股价查询 tool
  → Reflex: 行为模式弧
```

框架层只提供 Persona 的 **结构 + 加载/切换机制**，不提供具体人设内容。

## 架构位置

```
Colony (猫舍)
  └── namespace "personas/"        ← 面具存储
        ├── PERSONA.yaml
        └── ...

Cat (单只猫)
  ├── CatSelf._persona_backup      ← 切换前备份
  └── cat.wear_persona("musk")     ← 一键换面具
       → CatSelf.apply(persona)
       → Cortex.ingest(persona.beliefs)
       → Hippocampus.add_entity(knowledge_seeds)
       → SkillRegistry.register(persona.tools)
```

## 核心数据结构

### Persona dataclass

```python
@dataclass
class Persona:
    name: str
    version: str = "0.1.0"
    description: str = ""
    personality: dict[str, Any] = {}
    beliefs: list[Belief] = []
    capable: list[str] = []
    incapable: list[str] = []
    knowledge_seeds: list[KnowledgeSeed] = []
    tools: list[ToolSpec] = []
    reflex_specs: list[ReflexSpec] = []
    sample_dialogues: list[tuple[str, str]] = []
```

### 子结构

```python
@dataclass
class Belief:           # key, value, confidence (0-1), challengeable
@dataclass
class KnowledgeSeed:    # entity_type, name, properties, connections
@dataclass
class ConnectionSpec:   # to, relation, strength
@dataclass
class ReflexSpec:       # name, trigger, from_organ, to_organ, method
```

## 关键 API

### Cat 层

```python
cat.current_persona           # Persona | None
await cat.wear_persona(name)  # 戴面具
await cat.unwear_persona()    # 脱面具（不删除工具和知识）
```

### Colony 层

```python
await colony.register_persona(persona)  # 注册
await colony.list_personas()            # 列出名称
await colony.get_persona(name)          # 获取 Persona 实例
```

### 文件加载

```python
loader = PersonaLoader(dir=Path("./personas"))
personas = loader.scan()            # 扫描 PERSONA.yaml
await loader.load_all(colony)       # 扫描并注册
```

## 设计决策

1. **面具存 Colony namespace** — 面具属于猫舍共享资源
2. **切换是覆写（保留未提及的 key）** — `apply_persona` 覆盖 personality 字段但保留面具未涉及的 key
3. **知识种子 merge 语义** — 不覆盖已存在的同名实体
4. **unwear 不删除工具和知识** — 知识和技能持久保留
5. **YAML 格式** — 人类可读可编辑

## 与 v2.4.0 的关系

v2.4.0 负责精简架构，v2.5.0 在精简后的架构上新增 Persona。无代码冲突。
