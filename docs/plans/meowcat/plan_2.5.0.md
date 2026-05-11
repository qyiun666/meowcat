# plan_2.5.0: Persona 面具系统

> **来源**: 架构探讨 — 任意蒸馏 skill 接入框架的标准化路径
> **基线**: v2.4.0 (架构精简后)
> **创建日期**: 2026-05-10
> **目标版本**: v2.5.0

---

## 背景

当前框架中，外部 skill/agent 可以通过 `mount()` 或 `AgentOrgan` 接入单个器官。但当面对 "马斯克 skill"、"前任 skill" 这类 **人格蒸馏产物** 时，问题浮现：

- 一个蒸馏 skill 包含 **性格 + 三观 + 自知 + 领域知识 + 行为模式 + 特殊能力** 六层
- 这六层对应四个不同器官：CatSelf、Cortex、Hippocampus、SkillRegistry
- 目前没有 "一键换人设" 的统一入口
- CatSelf 的 personality / beliefs / capabilities 是散装字段，需要分别设

**Persona（面具）** 概念：一套可加载、可切换、可序列化的身份预设，打包分发到各器官。

---

## 设计目标

```
猫戴上「马斯克面具」
  → CatSelf: personality={tone:"visionary", language:"en+zh"}
  → Cortex: worldview 种子 "第一性原理"、"物理思维"
  → Hippocampus: 知识图谱种子 (SpaceX, Tesla, X平台)
  → SkillRegistry: X API tool, 股价查询 tool
  → Reflex: 行为模式弧

猫戴上「前任面具」
  → 同上，不同值
```

框架层只提供 Persona 的 **结构 + 加载/切换机制**，不提供具体人设内容。具体面具由应用层/社区创建和分享。

---

## 架构位置

```
Colony (猫舍)
  └── namespace "personas/"        ← 新命名空间，存多套面具
        ├── musk.yaml              ← YAML 格式，社区可分享
        ├── ceo.yaml
        └── ...

Cat (单只猫)
  ├── CatSelf._persona: Persona | None  ← 当前面具引用
  └── cat.wear_persona("musk")         ← 一键换面具
       → CatSelf.apply(persona)
       → Cortex.ingest(persona.worldview)
       → Hippocampus.ingest(persona.knowledge)
       → SkillRegistry.register(persona.tools)
```

### 依赖现有组件

- `colony.ns_get/set("personas", ...)` → 面具存储（复用 Colony namespace）
- `CatSelf._personality / _capabilities` → 性格+自知覆写
- `Cortex.ingest()` → 三观种子注入
- `Hippocampus.add_entity()` → 知识图谱种子
- `SkillRegistry.register()` → 工具注册
- `Reflex` 弧 → 行为模式
- `plus/skill_loader.py` → 面具文件加载（复用模式）

---

## 核心数据结构

### Persona dataclass

```python
@dataclass
class Persona:
    name: str                    # 面具名 "musk"
    version: str = "0.1.0"
    description: str = ""
    # -- CatSelf 映射 --
    personality: dict = {}       # {tone, language, style, ...}
    beliefs: list[Belief] = []   # [(key, value, confidence), ...]
    capable: list[str] = []
    incapable: list[str] = []
    # -- 知识种子 --
    knowledge_seeds: list[KnowledgeSeed] = []  # Hippocampus 初始实体
    # -- 工具 --
    tools: list[ToolSpec] = []   # SkillRegistry 注册
    # -- 行为 --
    reflex_specs: list[ReflexSpec] = []  # 预设反射弧
    # -- 示例对话 (可选) --
    sample_dialogues: list[tuple[str, str]] = []
```

### Belief / KnowledgeSeed / ReflexSpec（子结构）

```python
@dataclass
class Belief:
    key: str           # e.g. "第一性原理"
    value: str         # e.g. "从最基本的事实出发推理"
    confidence: float = 0.8

@dataclass
class KnowledgeSeed:
    entity_type: str   # e.g. "company"
    name: str          # e.g. "SpaceX"
    properties: dict   # e.g. {industry: "aerospace", founded: 2002}
```

---

## 关键 API

### Cat 层

```python
# 换面具（从 Colony persona namespace 加载）
await cat.wear_persona("musk")

# 脱面具（恢复到骨架 CatSelf）
cat.unwear_persona()

# 当前面具
cat.current_persona  # → Persona | None
```

### Colony 层

```python
# 注册面具到猫舍
await colony.register_persona(musk_persona)

# 列出所有面具
await colony.list_personas()  # → ["musk", "ceo", "ex-gf"]

# 获取面具
persona = await colony.get_persona("musk")
```

### 文件加载（复用 SkillLoader 模式）

```python
from meowcat.persona import PersonaLoader

loader = PersonaLoader(dir=Path("./personas"))
loader.scan()  # 扫描所有 persona.yaml
loader.load_all(colony)  # 注册到猫舍
```

---

## Persona 文件格式 (YAML)

```yaml
# persona/musk.yaml
name: musk
version: "0.1.0"
description: 马斯克思维模式
personality:
  tone: visionary
  language: en+zh

beliefs:
  - key: first_principles
    value: 从最基本的事实出发推理，不依赖类比
    confidence: 0.95
  - key: physics_approach
    value: 用物理学的眼光看待问题
    confidence: 0.9

capable:
  - 工程架构
  - 商业决策
  - 物理分析
incapable:
  - 文学创作
  - 政治正确

knowledge_seeds:
  - entity_type: company
    name: SpaceX
    properties:
      industry: aerospace
      founded: 2002
      ceo: Elon Musk

tools:
  - name: check_stock_price
    description: 查美股股价
```

社区可以直接分享 `.yaml` 文件。

---

## 子任务拆解

| 子任务 | 能力域   | 依赖        | 并发 | 一句话                                                      |
| ------ | -------- | ----------- | ---- | ----------------------------------------------------------- |
| T-01   | 架构设计 | v2.4.0 完成 | —    | ✅ 产出 design.md + 接口定义                                |
| T-02   | 代码生成 | T-01        | [∥]  | ✅ 实现 Persona dataclass + 子结构 (`meowcat/persona.py`)   |
| T-03   | 代码生成 | T-01        | [∥]  | ✅ 实现 Colony namespace 面具存储 (`colony/persona_mgr.py`) |
| T-04   | 代码生成 | T-02,T-03   | —    | ✅ 实现 Cat.wear/unwear + CatSelf.apply                     |
| T-05   | 代码生成 | T-02        | [∥]  | ✅ 实现 PersonaLoader (YAML 加载)                           |
| T-06   | 测试编写 | T-04,T-05   | —    | ✅ 面具加载/切换/序列化 测试                                |
| T-07   | 文档更新 | T-06        | —    | 同步 AGENTS + CATALOG + agents/AGENTS.md                    |

### 新增文件预估

| 文件                             | 行数 | 说明                                     |
| -------------------------------- | ---- | ---------------------------------------- |
| `meowcat/persona.py`             | ~120 | Persona dataclass + Belief/KnowledgeSeed |
| `meowcat/colony/persona_mgr.py`  | ~80  | Colony namespace 面具存储                |
| `meowcat/plus/persona_loader.py` | ~80  | YAML 加载器                              |
| `meowcat/biology/cat_self.py`    | +30  | CatSelf.apply_persona / remove_persona   |

合计新增代码: ~300 行，修改已有文件: ~50 行。

---

## 设计决策（待确认）

1. **面具存 Colony 还是 Cat 私有？** → Colony namespace，面具属于猫舍共享资源
2. **切换面具时是覆写还是追加？** → 覆写（干净切换），但保留选项可追加
3. **知识种子是否持久化到 Hippocampus？** → 是，但不覆盖已有同名实体（merge 语义）
4. **YAML 还是 JSON？** → YAML（跟 SKILL.md 模式一致，人类可读可编辑）

---

## 与 v2.4.0 的关系

v2.4.0 负责精简架构（去冗余 exports），v2.5.0 在精简后的架构上新增 Persona。无代码冲突：

- v2.4.0: 删冗余 exports (Path/Chain/Loop 公开面)
- v2.5.0: 加 Persona dataclass + 加载器 + Cat 接口

两者操作不同文件，但 v2.5.0 依赖 v2.4.0 完成后的干净基线。
