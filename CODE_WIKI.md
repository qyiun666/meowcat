# meowcat Code Wiki

> **版本**: 0.5.9+ (>= v1.2+ 特性已融入)
> **许可证**: MIT (c) 2025-2026 Axonant
> **仓库**: [Axonant/MeowAgent](https://github.com/Axonant/MeowAgent)
> **Python**: 3.10+

---

## 1. 项目概述

**meowcat** 是 MeowAgent 生态系统的纯框架层——以猫的生物学神经系统为蓝图构建的 AI Agent 框架。它提供了猫的"解剖结构"：Protocols（器官接口）、Neural Wiring（神经布线）、Reflex Arc（反射弧）、Tools/Skills（工具/技能），以及从原子信号到可组合闭环的四层抽象。

> **核心设计哲学**: 框架只定义"骨架"和"连接规则"（Slot），具体的器官实现（Plug）由上层应用提供。框架本身零 I/O 依赖——所有具体 I/O 实现位于 `plus/` 可选模块中。

### 核心特性

| 类别                 | 说明                                                                |
| -------------------- | ------------------------------------------------------------------- |
| 猫的解剖结构         | 20 个器官，基于真实神经蓝图（丘脑、海马体、杏仁核等）               |
| Slot / Plug 模型     | 器官 = 类型化 Slot (Protocol)，实现 = Plug（4 种风格），可自由替换  |
| 四层抽象             | Path (原子) → Chain (序列) → Loop (触发+退出) → LoopSequence (编排) |
| 两个闭环             | 内环: 自我进化 (CatSelf)。外环: 群体智能 (Colony)                   |
| CatSelf 统一自我模型 | before_act / after_act + 默认定时快照 + 3 个预制闭环                |
| 主动成长             | BlindSpotDetector + ToolFailureLearner + HotPathObserver — 猫会学习 |
| Pluggable 混入       | 每个器官支持运行时钩子 mount/unmount，3 种执行模式，异步兼容        |
| Colony 多猫容器      | 对等协作: 共享内存、跨猫信号、联邦通信                              |
| 反射弧系统           | 预定义的刺激 → 响应路径，零 LLM 依赖的条件触发                      |
| 信号安全             | 每条 (organ, method) 独立熔断器，连续失败自动断路                   |
| Telemetry 遥测       | 内置 Tracer + Metrics — 零依赖的信号调用可观测性                    |
| 懒加载               | `import meowcat` 仅加载骨架，按需展开完整模块树                     |
| 零硬编码             | 所有阈值、危险列表、语言预设都是构造函数参数                        |

---

## 2. 项目架构

### 2.1 目录结构

```
meowcat/
├── __init__.py               # 包入口，版本号
├── _exports.py               # 静态 API 导出列表 (CI 验证)
├── anatomy.py                # 解剖坐标常量 + 器官枚举定义
├── assembly.py               # CatBase — 猫的组装车间 (976行核心)
├── host.py                   # OrganHost — 器官容器 (挂载/卸载/查找)
├── wiring.py                 # Wiring — 神经布线 (允许/禁止边)
├── nervous.py                # Nervous — 信号调度引擎 (中间件/熔断)
├── reflex.py                 # ReflexArc — 反射弧系统
├── protocols.py              # Organ Protocol 接口定义 (~20 个 Protocol)
├── protocols_storage.py      # 存储 Protocol 接口
├── errors.py                 # 异常类型层次
├── events.py                 # EventBus — 事件发布/订阅
├── models.py                 # Pydantic 数据模型 (纯数据形状)
├── perception.py             # PerceptionContext — 感知上下文
├── pipeline.py               # Pipeline 执行器 — Stage 链式驱动
├── path.py                   # Path — 原子信号路径
├── chain.py                  # Chain — 路径序列
├── loops.py                  # Loop / LoopSequence — 闭环系统
├── log.py                    # MeowLog — 结构化日志
├── diagnose.py               # Stethoscope — 听诊器 (诊断工具)
├── pluggable.py              # Pluggable 混入 (插件系统)
├── biology/                  # 生物学高级模块
│   ├── __init__.py           # OrganSpec + 内置神经系统 + 懒加载
│   ├── cat_self.py           # CatSelf — 统一自我模型
│   ├── cortex.py             # Cortex — 皮层世界观 L0-L3
│   ├── pineal_gland.py       # PinealGland — 松果体洞察融合
│   ├── fusion_cycle.py       # FusionCycle — 融合周期管理
│   ├── metacognition.py      # Metacognition — 元认知
│   ├── scribble_pad.py       # ScribblePad — 私有记事本
│   ├── growth.py             # CollectiveGrowth — 群体成长
│   ├── roles.py              # CollectiveEmergence — 角色涌现
│   ├── active_growth.py      # 主动成长机制
│   └── active_growth_pack.py # 主动成长包
├── tools/                    # 工具/技能框架 (零 I/O 依赖)
│   ├── __init__.py           # 懒加载入口
│   ├── tool.py               # Tool / ToolSpec / ToolRegistry
│   ├── skill.py              # Skill / SkillSpec / SkillRegistry
│   ├── paws.py               # PawsEngine — 工具执行引擎
│   └── matcher.py            # KeywordToolMatcher — 关键词匹配
├── colony/                   # Colony 多猫容器
│   ├── __init__.py           # Colony 主类
│   ├── config.py             # ColonyConfig / ColonyOwner
│   ├── rules.py              # ColonyRules — 安全/审批规则
│   ├── federation.py         # _FederationMixin — 跨主机联邦
│   └── registry.py           # GlobalColonyRegistry — 全局注册表
├── defaults/                 # 默认实现层
│   ├── factory.py            # create_cat() / create_colony() 工厂函数
│   ├── organs.py             # 15 个 Noop* 器官无操作桩
│   ├── stores.py             # InMemory* 存储实现
│   ├── renovated.py          # Renovated 精装器官 (预制实现)
│   └── presets.py            # 关键词/提示预设 (KW_EN, KW_ZH 等)
├── plus/                     # 可选扩展模块 (pip install meowcat[plus])
│   ├── __init__.py           # Plus 入口
│   ├── browser.py            # BrowserTool — Playwright 浏览器自动化
│   ├── chroma_store.py       # ChromaStore — ChromaDB 向量存储
│   ├── crystallizer.py       # Crystallizer — 三层知识结晶引擎
│   ├── mcp_client.py         # MCPClient — MCP 多服务器客户端
│   ├── skill_loader.py       # SkillLoader — SKILL.md 文件加载器
│   ├── gateway/              # 网关适配器
│   │   ├── __init__.py
│   │   ├── http_adapter.py   # HTTPAdapter — HTTP POST + SSE
│   │   ├── ws_adapter.py     # WsAdapter — WebSocket RFC 6455
│   │   ├── webhook_adapter.py # WebhookAdapter — Webhook 骨架
│   │   ├── cli_adapter.py    # CliAdapter — stdio / queue
│   │   └── ipc_adapter.py    # IpcAdapter — Unix Socket JSON-line
│   └── tools/                # 内置工具实现
│       ├── __init__.py
│       ├── file_ops.py       # read_file / write_file
│       ├── command.py        # run_command
│       └── http_client.py    # http_get
├── colony_transports.py      # Federation 传输实现
└── tests/                    # 测试系统 (60+ 测试文件)
    ├── conftest.py
    └── test_v*.py            # 按版本组织
```

### 2.2 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        应用层 (App Layer)                        │
│  • 自定义器官实现 (YourBrain, YourCerebellum, ...)               │
│  • 自定义 Skin/Gateway 适配器                                    │
│  • Colony 编排 (多猫团队)                                        │
├─────────────────────────────────────────────────────────────────┤
│                      Plus 层 (可选扩展)                           │
│  • BrowserTool, ChromaStore, MCPClient, Crystallizer            │
│  • 网关适配器 (HTTP/WS/Webhook/CLI/IPC)                          │
│  • 内置工具 (file_ops, command, http_client)                     │
├─────────────────────────────────────────────────────────────────┤
│                      Defaults 层 (默认实现)                       │
│  • Noop* 无操作桩 (15 个器官)                                    │
│  • Renovated 精装器官 (预制实现)                                  │
│  • InMemory* 内存存储实现                                        │
│  • create_cat() 工厂函数                                         │
│  • 关键词/提示预设 (KW_EN, KW_ZH, ...)                           │
├─────────────────────────────────────────────────────────────────┤
│                    Biology 层 (高级生物学模块)                     │
│  • CatSelf, Cortex, PinealGland, FusionCycle, Metacognition      │
│  • ScribblePad, CollectiveGrowth, CollectiveEmergence            │
│  • ActiveGrowth (BlindSpotDetector, ToolFailureLearner)          │
├─────────────────────────────────────────────────────────────────┤
│                    Framework 层 (框架核心)                         │
│  • CatBase (组装车间)                                            │
│  • OrganHost (器官容器) + Wiring (神经布线) + Nervous (信号调度)  │
│  • ReflexArc (反射弧) + EventBus (事件总线)                       │
│  • Tool/Skill/Paws (工具系统) + Pipeline (管道执行器)             │
│  • Path/Chain/Loop (四层执行原语)                                 │
├─────────────────────────────────────────────────────────────────┤
│                    Protocol 层 (接口契约)                          │
│  • Organ Protocols (~20 个 typed Protocol)                       │
│  • Storage Protocols (Graph/L6/Vector/Shared/Federation)         │
│  • OrganSpec (器官规格 SSOT)                                      │
├─────────────────────────────────────────────────────────────────┤
│                    Anatomy 层 (解剖常量)                           │
│  • 器官坐标常量 (THALAMUS, CEREBRUM, ...)                        │
│  • 五大类别 (BRAIN, SENSE, VOICE, STORAGE, GROWTH)               │
│  • ImplementationStyle 枚举                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心模块详解

### 3.1 解剖常量 (anatomy.py)

**职责**: 定义所有器官的名称坐标，是整个框架最底层的单一事实来源 (SSOT)。零依赖。

```python
# 器官坐标 = (category, organ_name)
THALAMUS: Organ    = ("brain", "thalamus")
CEREBRUM: Organ    = ("brain", "cerebrum")
CEREBELLUM: Organ  = ("brain", "cerebellum")
HIPPOCAMPUS: Organ = ("brain", "hippocampus")
AMYGDALA: Organ    = ("brain", "amygdala")
FRONTAL: Organ     = ("brain", "frontal")
HYPOTHALAMUS: Organ = ("brain", "hypothalamus")
CORTEX: Organ      = ("brain", "cortex")
BRAINSTEM: Organ   = ("brain", "brainstem")
EARS: Organ        = ("sense", "ears")
EYES: Organ        = ("sense", "eyes")
WHISKERS: Organ    = ("sense", "whiskers")
PAWS: Organ        = ("sense", "paws")
MOUTH: Organ       = ("voice", "mouth")
PURR: Organ        = ("voice", "purr")
TAIL: Organ        = ("voice", "tail")
PINEAL_GLAND: Organ = ("growth", "pineal_gland")
ANOMALY_GROWTH: Organ = ("growth", "anomaly_growth")
CORRECTION_GROWTH: Organ = ("growth", "correction_growth")
CRYSTALLIZER: Organ = ("growth", "crystallizer")
ROLE_EMERGENCE: Organ = ("growth", "role_emergence")
```

**关键类型**:

- `Organ = tuple[str, str]` — 器官坐标，`(category, name)`
- `ImplementationStyle` — 枚举: `ALGORITHM | RULE | MODEL | HYBRID`
- `ORGAN_BY_NAME: dict[str, Organ]` — 名称 → 坐标反向映射

**聚合元组**: `SENSORS` (EARS/EYES/WHISKERS), `EFFECTORS` (MOUTH/PURR/TAIL/PAWS), `BRAIN_REGIONS` (全部脑区), `GROWTH_ORGANS` (全部生长器官)

---

### 3.2 器官规格 (biology/**init**.py)

**职责**: `OrganSpec` 是每个器官的"身份证"——统一描述器官的合约、允许的神经边、读写权限和支持的实现风格。是整个器官系统的 SSOT。

```python
@dataclass(frozen=True)
class OrganSpec:
    coord: Organ                    # 器官坐标
    protocol: type                  # 对应的 Protocol 类
    in_edges: tuple[Organ, ...]     # 允许的入边
    out_edges: tuple[Organ, ...]    # 允许的出边
    read_methods: tuple[str, ...]   # 允许读取的方法
    write_methods: tuple[str, ...]  # 允许写入的方法
    write_callers: tuple[Organ, ...] # 允许写入的调用方
    supported_styles: tuple[ImplementationStyle, ...]  # 支持的实现风格
```

**全局常量**:

- `ORGAN_SPECS: dict[Organ, OrganSpec]` — 20 个器官的完整规格
- `BUILTIN_NERVOUS_SYSTEM: dict[Organ, set[Organ]]` — 预制的神经边
- `FORBIDDEN_PATHS: set[tuple[Organ, Organ]]` — 被禁止的路径
- `ORGAN_PROTOCOLS: dict[Organ, type]` — 器官 → Protocol 快速查找

**懒加载机制**: 使用 `__getattr__` 实现子模块懒加载。`import meowcat.biology` 时只加载 `__init__.py` 中的 `OrganSpec`，访问 `meowcat.biology.cat_self` 时才加载对应模块。这保证了框架核心导入速度。

---

### 3.3 器官 Protocol 接口 (protocols.py)

**职责**: 使用 Python `typing.Protocol` 定义每个器官必须实现的接口合约。实现 duck-type 的结构化类型检查。

**大脑区域 Protocols**:

| Protocol                | 对应器官 | 关键方法                                                                                   |
| ----------------------- | -------- | ------------------------------------------------------------------------------------------ |
| `ThalamusProtocol`      | 丘脑     | `relay(input) -> routed_output`                                                            |
| `LLMBrainProtocol`      | 大脑     | `generate(prompt) -> str`, `generate_stream(prompt) -> AsyncIterator[str]`                 |
| `HippocampusProtocol`   | 海马体   | `remember(episode)`, `recall(query) -> list[Episode]`, `associate(entity) -> list[Entity]` |
| `AmygdalaProtocol`      | 杏仁核   | `assess(input) -> SafetyReport` (可绕过大脑直接触发动作)                                   |
| `FrontalCortexProtocol` | 前额叶   | `plan(task) -> Plan`, `decide(options) -> Decision`                                        |
| `HypothalamusProtocol`  | 下丘脑   | `maintain()` (稳态维护: 衰减/清理/压缩)                                                    |
| `CortexProtocol`        | 皮层     | `extract_rules()`, `promote_belief()`, 世界观 L0-L3                                        |
| `BrainStemProtocol`     | 脑干     | `dispatch()`, 协调所有脑区和感官                                                           |

**感官与效应器 Protocols**:

| Protocol           | 对应器官 | 关键方法                     |
| ------------------ | -------- | ---------------------------- |
| `EarsProtocol`     | 听觉     | `hear(input) -> audiogram`   |
| `EyesProtocol`     | 视觉     | `see(input) -> visiogram`    |
| `WhiskersProtocol` | 触觉     | `sense(input) -> tacogram`   |
| `PawsProtocol`     | 执行     | `execute(tool_name, params)` |
| `MouthProtocol`    | 语音输出 | `speak(text) -> str`         |
| `PurrProtocol`     | 呼噜     | `purr(status) -> stream`     |
| `TailProtocol`     | 尾巴     | `wag(status)`                |

**其他 Protocols**:

- `StageProtocol` — Pipeline 阶段的接口: `async def run(ctx) -> AsyncIterator[StageEvent]`
- `CatProtocol` — Cat 对外暴露能力的接口（供 Colony 使用）

---

### 3.4 神经布线 (wiring.py)

**职责**: 定义器官间的有线连接关系——哪些器官可以向哪些器官发送信号。用有向图 (allowlist + blocklist) 描述神经通路。

**`Wiring` 类**:

```python
class Wiring:
    def connect(self, source: Organ, target: Organ) -> None      # 建立允许边
    def forbid(self, source: Organ, target: Organ) -> None       # 建立禁止边
    def is_allowed(self, source: Organ, target: Organ) -> bool    # 检查边是否允许
    def edges(self) -> frozenset[Edge]                           # 获取所有允许边
    def forbids(self) -> frozenset[Edge]                         # 获取所有禁止边
    def adjacency(self) -> dict[Organ, set[Organ]]                # 邻接表
    def freeze(self) -> None                                     # 冻结（不可再修改）
    def is_frozen(self) -> bool                                  # 是否已冻结
```

**核心规则**:

- `Edge = tuple[Organ, Organ]` 是有向边，方向 = 信号流向
- **禁止边优先于允许边**: 先检查 `forbid` 集合，再检查 `connect` 集合
- `freeze()` 后不可再调用 `connect()` / `forbid()`（防御性设计）
- 冻结后的 Wiring 可作为信号调度的不可变参考

---

### 3.5 信号调度 (nervous.py)

**职责**: 神经系统的信号调度引擎——负责在合法的神经通路（Wiring）上发送器官间信号，带有中间件链和熔断器保护。

**`Nervous` 类**:

```python
class Nervous:
    def __init__(self, host: OrganHost, wiring: Wiring) -> None

    async def signal(self, target: Organ, method: str, *args, **kwargs)
        # 向目标器官发送信号

    def use(self, middleware: SignalMiddleware)
        # 注册信号中间件

    # 熔断器
    def circuit_state(self, organ: Organ, method: str) -> str  # "closed"|"open"|"half_open"
```

**信号调度流程**:

```
signal(target, method, *args, **kwargs)
    │
    ▼
1. 检查 Wiring — is_allowed(source, target)?
    │ NO → 抛出 IllegalNeuralPathError
    ▼ YES
2. 检查 forbidden_methods (Kitten 权限)
    │
    ▼
3. 中间件链 (before → signal → after)
    ├── 日志中间件
    ├── 遥测中间件 (Tracer.start / end)
    ├── 指标中间件 (Metrics.increment)
    └── 自定义中间件
    │
    ▼
4. 熔断器检查
    │ OPEN → 抛出 CircuitOpenError
    ▼ CLOSED/HALF_OPEN
5. 调用目标器官方法
    │
    ▼
6. 触发事件: nerve.signal.from.{source} / nerve.signal.to.{target}
    │
    ▼
7. 熔断器记录结果 (成功 → 恢复; 失败 → 计数)
```

**SignalMiddleware 协议**:

```python
class SignalMiddleware:
    async def before(self, signal: Signal) -> Signal | None  # 返回 None 阻断
    async def after(self, signal: Signal, result: Any) -> Any  # 后处理
```

---

### 3.6 器官容器 (host.py)

**职责**: 管理器官的生命周期——挂载、卸载、查找。在挂载时验证器官是否满足其 Protocol 合约。

**`OrganHost` 类**:

```python
class OrganHost:
    def mount(self, organ: Any, protocol: type | None = None) -> None
        # 挂载器官; 若提供 protocol 则进行 Protocol 检查
        # Protocol 不匹配时抛出 OrganProtocolMismatchError

    def unmount(self, category: str, name: str) -> Any
        # 卸载器官并返回

    def organ(self, category: str, name: str) -> Any | None
        # 按坐标查找器官

    def list_organs(self) -> list[tuple[str, str, Any]]
        # 列出所有已挂载器官

    def assert_organs_mounted(self, *organs: Organ) -> None
        # 断言指定器官已挂载，否则抛出 OrganNotMountedError
```

---

### 3.7 CatBase — 猫的组装车间 (assembly.py)

**职责**: **Cat 是五个子系统的组合体**。CatBase 不继承任何组件，而是以组合模式 (Composition) 持有它们。这是整个框架的核心纽带。

**`CatBase` 类 (~976 行)**:

```python
class CatBase:
    def __init__(self, name: str, *, owner, wiring=None, colony=None,
                 reflex_arc=None, rules=None, ...):
        self._host = OrganHost()         # 子系统1: 器官容器
        self._wiring = Wiring()          # 子系统2: 神经布线
        self._nervous = Nervous(...)     # 子系统3: 信号调度
        self._events = EventBus(...)     # 子系统4: 事件总线
        self._reflex_arc = ReflexArc()   # 子系统5: 反射弧

    # === 器官访问 (Facade 模式) ===
    def organ(self, category: str, name: str) -> Any
    # 支持 cat.ears, cat.thalamus 等属性访问（通过 __getattribute__ 拦截）

    # === 信号发送 (Facade 模式) ===
    async def signal(self, target: Organ, method: str, *args, **kwargs)

    # === 感知入口 (统一的对外接口) ===
    async def perceive(self, input: Any) -> Any
        # ReflexArc 入口: 输入 → 匹配反射弧 → Pipeline 执行

    # === Kittens (子猫/权限控制) ===
    def kitten(self, name: str, allowed_organs: set[Organ], forbidden_methods: set[str]) -> CatBase
        # 创建受限视图的子猫

    # === 生命周期钩子 ===
    async def on_start(self)
    async def on_shutdown(self)
    async def on_organs_mounted(organs: dict[Organ, Any])

    # === 注册表 (直接属性访问) ===
    cat.tool_registry    # Tool 注册表
    cat.skill_registry   # Skill 注册表
    cat.path_registry    # Path 注册表
    cat.chain_registry   # Chain 注册表
    cat.loop_registry    # Loop 注册表
    cat.loopseq_registry # LoopSequence 注册表

    # === 便捷方法 ===
    async def run_path(name, **kw)        # 执行一个 Path
    async def run_chain(name, **kw)       # 执行一个 Chain
    async def run_loop(name, **kw)        # 执行一个 Loop
    async def run_loopseq(name, **kw)     # 执行一个 LoopSequence
```

**Facade 模式**: CatBase 对外暴露 `cat.ears`、`cat.thalamus` 等直接属性访问，但内部通过 `__getattribute__` 拦截，将器官名转发到 `self._host.organ("category", "name")`。

**Kitten 机制**: `kitten()` 方法创建一个新的 CatBase 实例，但只允许访问白名单器官和禁止黑名单方法——实现精细化的权限控制。Kitten 与母猫共享同一个 `_host`（视图限制而非拷贝）。

**关键辅助函数**:

- `mount_known_organs(cat, organ_dict)` — 根据字典键按 OrganSpec 自动挂载
- `assemble_default_cat(name, **kw)` — 一键组装默认猫

---

### 3.8 反射弧系统 (reflex.py)

**职责**: 受生物条件反射启发——某些刺激直接触发预设的响应路径，无需通过大脑的完整回路。反射弧是 `cat.perceive()` 的一级入口。

**`Reflex` 类** (Pydantic BaseModel):

```python
class Reflex(BaseModel):
    name: str                       # 反射名
    trigger: Callable               # 触发条件 (返回 (matched, confidence))
    path: str                       # 关联的 Path 或 Chain 名称
    stages: list[StageProtocol]     # 附加的前/后处理 Stage
    priority: int = 0               # 优先级 (数字越大越先匹配)
```

**`ReflexRegistry` 类**:

```python
class ReflexRegistry:
    def register(self, reflex: Reflex) -> None
    def unregister(self, name: str) -> None
    def match(self, input: Any) -> Reflex | None   # 按优先级匹配
    def list_all() -> list[Reflex]                  # 按优先级排序
```

**`ReflexArc` 类** — 独立的反射弧子系统:

```python
class ReflexArc:
    def __init__(self, reflexes=None, hot_path_observer=None) -> None
    def register(self, reflex: Reflex) -> None
    def add_stages(self, *stages: StageProtocol) -> None  # 全局 Stage
    async def perceive(self, input: Any, *, cat: CatProtocol, ctx: PerceptionContext) -> Any
        # 一级入口: 匹配 → Pipeline 执行 → 返回结果
```

**`BUILTIN_REFLEX_PATHS`**: 内置反射路径定义。

**感知流程** (`cat.perceive()` → `ReflexArc.perceive()`):

```
输入 → ReflexRegistry.match(input)
       │
       ▼ 匹配到 Reflex
1. 创建 PerceptionContext (input, modality, reflex_name, cat)
2. Pipeline(stages) 执行:
   ├── global_stages (ReflexArc 全局)
   ├── reflex.stages (Reflex 专属)
   ├── reflex.path (关联的 Path/Chain 执行)
   └── post_stages
3. 返回 PerceptionContext.final_reply
       │
       ▼ 未匹配 (Fallback)
直接运行 default_path
```

---

### 3.9 事件系统 (events.py)

**职责**: 基于 pub/sub 模式的事件总线——解耦各子系统间的通知。事件分为异步和同步两种模式。

**`EventBus` 类**:

```python
class EventBus:
    def on(self, event: str, handler: Callable) -> None       # 注册事件处理器
    def off(self, event: str, handler: Callable) -> None      # 注销事件处理器
    def clear(self, event: str = None) -> None                 # 清除处理器
    async def emit(self, event: str, **payload) -> None        # 同步发射（等待所有处理器）
    def emit_nowait(self, event: str, **payload) -> Task       # 异步发射（不等待）
```

**事件名称常量**（按类别组织）:

| 类别             | 事件示例                                                |
| ---------------- | ------------------------------------------------------- |
| Lifecycle        | `cat.start`, `cat.shutdown`, `cat.organs_mounted`       |
| LocateEvent      | `path.locate.before`, `path.locate.after`               |
| RememberEvent    | `memory.store`, `memory.recall`                         |
| OrchestrateEvent | `orchestrate.plan`, `orchestrate.dispatch`              |
| GrowthEvent      | `growth.anomaly`, `growth.correction`, `growth.crystal` |
| NerveEvent       | `nerve.signal` (before + after 自动触发)                |
| KittenEvent      | `kitten.create`, `kitten.destroy`                       |
| SelfEvent        | `self.snapshot`, `self.reflect`                         |
| FusionEvent      | `fuse.self`, `fuse.colony`                              |
| TelemetryEvent   | `telemetry.metric`, `telemetry.trace`                   |

---

### 3.10 原子路径 (path.py)

**职责**: Path 是四层执行原语的最底层——单个原子信号路径，从一个器官出发到达另一个器官。

**`Path` 类**:

```python
class Path:
    name: str
    source: Organ
    target: Organ
    method: str                    # 调用的目标方法名
    args_transform: Callable | None  # 参数转换函数
```

**`PathRegistry` 类**: 路径注册表，支持注册、查找和执行路径。

---

### 3.11 路径序列 (chain.py)

**职责**: Chain 是第二层执行原语——多个 Path 的顺序组合，支持链嵌套和回滚。

**`Chain` 类**:

```python
class Chain:
    name: str
    steps: list[Path | Chain]     # 步骤 (支持嵌套)
    rollback: list[Path]          # 回滚路径 (任一步骤失败时执行)
```

**`ChainRegistry` 类**: 链注册表。

---

### 3.12 闭环系统 (loops.py)

**职责**: Loop 是第三层执行原语——Chain + 触发事件 + 退出事件 = 自主闭环。LoopSequence 是第四层。

**`Loop` 类**:

```python
class Loop:
    name: str
    chain: Chain                   # 关联的链
    trigger_event: str             # 触发事件
    exit_event: str                # 退出事件
```

**`LoopSequence` 类** (v1.0.4): 多个 Loop 的顺序或并发编排。

**三个默认闭环** (v1.2.0):

- **ConversationLoop** — 对话闭环: EARS → THALAMUS → CEREBRUM → CEREBELLUM → MOUTH/PURR/TAIL
- **TaskLoop** — 任务闭环: THALAMUS → FRONTAL → PAWS → 结果回流
- **LearnLoop** — 学习闭环: HIPPOCAMPUS → CORTEX → PinealGland → 融合

---

### 3.13 Colony 多猫容器 (colony/)

**职责**: Colony 是管理多只猫对等协作的容器。每只猫保持其完整神经系统，通过 SharedStorage 和跨猫信号进行通信。

**`Colony` 类** (继承 `Pluggable` + `_FederationMixin`):

```python
class Colony(Pluggable, _FederationMixin):
    def __init__(self, colony_id, storage=None, *, name=None, ...)

    # 猫管理
    def create_cat(cat_uid, ...) -> CatBase
    def get_cat(cat_uid) -> CatBase | None
    def remove_cat(cat_uid) -> bool
    def get_all_cats() -> dict[str, CatBase]
    def list_cats() -> list[str]

    # 猫间通信
    async def signal_between(from_id, to_id, category, name, method, ...)
        # 1对1 私聊（跨猫信号）
    async def broadcast_request(method, **params)
        # 1对多 群聊（广播请求-响应）
    async def broadcast(event, **payload)
        # 全员广播

    # 共享存储
    async def shared_get(key) -> Any
    async def shared_set(key, value) -> None

    # Federation (跨主机)
    async def federate(transport)
    async def signal_remote(target_colony, cat_uid, ...)

    # 群体智能
    @property growth -> CollectiveGrowth       # 群体成长
    @property emergence -> CollectiveEmergence # 角色涌现
```

**子模块**:

| 模块            | 类/职责                                                                  |
| --------------- | ------------------------------------------------------------------------ |
| `config.py`     | `ColonyConfig` (名称/描述/最大猫数) + `ColonyOwner`                      |
| `rules.py`      | `ColonyRules(Pluggable)` — 安全策略/审批/速率限制                        |
| `federation.py` | `_FederationMixin` — 跨主机 Colony 对等通信 (request-response, 30s 超时) |
| `registry.py`   | `GlobalColonyRegistry(Pluggable)` — 进程级多 Colony 全局注册表           |

**共享存储命名空间** (v1.1.6):

- `owner/` — 拥有者信息
- `rules/` — 群体规则
- `knowledge/` — 共享知识
- `growth/` — 群体成长记录
- `cats/` — 猫元数据

**Federation 联邦通信**: 使用 UUID 追踪请求-响应，通过 `FederationTransport.publish/subscribe` 进行消息路由。

---

### 3.14 生物学高级模块 (biology/)

**子模块一览**:

| 模块                    | 版本    | 主要类                                    | 职责                        |
| ----------------------- | ------- | ----------------------------------------- | --------------------------- |
| `cat_self.py`           | v1.2.0  | `CatSelf`, `SelfSnapshot`                 | 统一自我模型 + 三个默认闭环 |
| `cortex.py`             | v1.1.25 | `Cortex`, `DefaultRuleExtractor`          | 皮层世界观 L0-L3            |
| `pineal_gland.py`       | v1.1.24 | `PinealGland`, `Insight`, `DefaultMerger` | 松果体 - 洞察融合           |
| `fusion_cycle.py`       | v1.1.24 | `FusionCycle`                             | 融合周期管理                |
| `metacognition.py`      | v1.1.27 | `Metacognition`                           | 元认知 L3                   |
| `scribble_pad.py`       | v1.1.23 | `ScribblePad`, `DefaultScribbleFilter`    | 猫的私有记事本              |
| `growth.py`             | v1.1.22 | `CollectiveGrowth`                        | 群体级异常/纠错记录         |
| `roles.py`              | v1.1.22 | `CollectiveEmergence`                     | 群体级角色涌现              |
| `active_growth.py`      | v1.1.26 | `BlindSpotDetector`, `ToolFailureLearner` | 主动成长机制                |
| `active_growth_pack.py` | v1.1.26 | `ActiveGrowthPack`                        | 主动成长包                  |

**`CatSelf` 类** — 统一自我模型:

```python
class CatSelf(Pluggable):
    def __init__(self, personality, cortex, skills, scribble_pad, ...)
    def before_act(action_type) -> SelfSnapshot  # 动作前冻结快照
    def after_act(description, metadata)          # 动作后写回 + 反思
    def loop(loop_name)                           # 获取默认闭环
```

是**所有器官读写路径的统一起点和终点**。每个动作前冻结 `SelfSnapshot`，动作后写回 + 反思。

**`PinealGland`** — 洞察融合:

- 将多个来源的洞察融合为统一知识
- 支持自我融合 (`fuse_to_self`) 和群体融合 (`fuse_to_colony`) 两种策略
- 通过 `FusionEvent` 事件通知 CORTEX 更新世界观

**`CollectiveGrowth`** — 群体成长:

- 将猫的异常和纠正记录到 Colony 的 `growth/` 命名空间
- 实现跨猫学习：每只猫都能从其他猫的错误中学习
- 支持可插拔的策略钩子 (first-hit 执行模式)

**Epiphany 管道**: ScribblePad → PinealGland → meditate → fuse_to_self / fuse_to_colony

**主动成长机制**:

- `BlindSpotDetector` — 检测猫的盲点（反复出错但未修正的知识）
- `ToolFailureLearner` — 从工具失败中学习正确的调用方式
- `HotPathObserver` — 观察高频路径并优化

---

### 3.15 错误类型系统 (errors.py)

**异常层次结构**:

```
MeowCatError (基类)
├── OrganNotMountedError            # 器官未挂载
├── LoopFailedError                 # 闭环执行失败
├── StageTimeoutError               # Pipeline Stage 超时
├── IllegalNeuralPathError          # 非法神经路径调用
├── ReflexPathInvalidError          # 反射弧路径非法
├── NoReflexMatchedError            # 无匹配反射弧
├── StandaloneCatError              # Cat 不在 Colony 中
├── OrganProtocolMismatchError      # 器官不满足 Protocol
├── OrganDelegateError              # AgentOrgan/SkillOrgan 委托失败
└── CircuitOpenError                # 熔断器开路
```

---

### 3.16 诊断工具 (diagnose.py)

**`Stethoscope` 类** — 听诊器（全身体检工具）:

```python
class Stethoscope:
    @staticmethod
    async def probe_all(cat) -> dict[str, dict]
        # 遍历所有器官，调用 diagnose()

    @staticmethod
    async def probe_category(cat, category) -> dict[str, dict]
        # 按类别诊断

    @staticmethod
    async def probe_organ(cat, category, name) -> dict
        # 单个器官诊断
```

**`render_wiring(wiring, format)` 函数**:

- 生成 wiring 图的可视化描述
- 支持 `"mermaid"` 和 `"dot"` 两种格式
- 允许边用实线箭头，禁止边用红色虚线，孤立节点标灰色

---

### 3.17 日志系统 (log.py)

**`MeowLog` 类** — 结构化日志:

```python
class MeowLog:
    @classmethod get(name) -> MeowLog       # 获取/创建 logger (单例)
    @classmethod plug_handler(handler)      # 注册自定义处理器
    @classmethod clear_handlers()           # 清除所有处理器

    def debug(msg, **data)
    def info(msg, **data)
    def warning(msg, **data)
    def error(msg, **data)
    def critical(msg, **data)
```

底层包装 stdlib `logging`，增加结构化 `**data` 参数和可插拔的处理器管道。

---

### 3.18 数据模型 (models.py)

纯数据结构 (Pydantic BaseModel)，零业务逻辑：

| 形状                       | 用途                                 |
| -------------------------- | ------------------------------------ |
| `EntityShape`              | 纠缠图实体节点                       |
| `ConnectionShape`          | 纠缠图边                             |
| `EpisodeShape`             | 事件记忆片段                         |
| `FocusShape`               | 焦点/上下文                          |
| `SubTaskShape`             | 子任务                               |
| `TaskResultShape`          | 任务结果                             |
| `OrchestratorReportShape`  | 编排报告                             |
| `MaintenanceReportShape`   | 维护报告                             |
| `CandidateShape`           | 搜索候选结果                         |
| `LocateResultShape`        | 定位结果                             |
| `StageEvent`               | 管道阶段事件 (kind, reply, metadata) |
| `PipelineContext`          | 管道上下文                           |
| `LoopEvent`                | 闭环事件                             |
| `MergeProposalShape`       | 合并建议                             |
| `KittenCapability`         | Kitten 能力声明                      |
| `WorkflowShape`            | 工作流形状                           |
| `LLMConfig`, `ModelConfig` | LLM 配置                             |

---

### 3.19 感知上下文 (perception.py)

**`PerceptionContext`** — `cat.perceive()` 执行期间的跨 Stage 共享状态容器:

```python
class PerceptionContext(BaseModel):
    input: Any                      # 原始输入
    modality: Modality = "unknown"  # 推断的输入模态 (text/image/audio/tool_result/unknown)
    reflex_name: str = ""           # 匹配的反射弧名称
    cat: Any = None                 # CatBase 回引用 (供 Stage 中发送信号)
    short_circuited: bool = False   # 短路标志
    final_reply: Any = None         # 最终回复
```

**`infer_modality(input)`** — 粗粒度的模态推断函数。

---

### 3.20 Pipeline 执行器 (pipeline.py)

**`Pipeline` 类** — 顺序执行 Stage 列表，支持短路停止:

```python
class Pipeline:
    def __init__(self, stages: list[StageProtocol]) -> None
    async def execute(self, ctx: Any) -> AsyncIterator[StageEvent]
```

当任何 Stage 产生 `kind == "short_circuit"` 的事件时，Pipeline 停止执行后续 Stage，并设置 `ctx.short_circuited = True` / `ctx.final_reply = ev.reply`。

---

### 3.21 存储协议 (protocols_storage.py)

持久化存储的 Protocol 接口定义：

| Protocol                | 用途           | 关键方法                                    |
| ----------------------- | -------------- | ------------------------------------------- |
| `GraphStorageProtocol`  | 纠缠图持久化   | `load()`, `save()`                          |
| `L6StorageProtocol`     | 原始对话持久化 | `append()`, `load_all()`, `load_recent()`   |
| `VectorStorageProtocol` | 向量搜索存储   | `search()`, `upsert()`, `delete()`          |
| `SharedStorageProtocol` | 共享存储       | `get()`, `set()`, `delete()`, `list_keys()` |
| `FederationTransport`   | 跨主机传输     | `send()`, `receive()`                       |

---

### 3.22 工具/技能系统 (tools/)

**框架层 (零 I/O 依赖)**:

| 模块         | 关键类                                          | 职责                                             |
| ------------ | ----------------------------------------------- | ------------------------------------------------ |
| `tool.py`    | `RiskLevel`, `ToolSpec`, `Tool`, `ToolRegistry` | 工具核心抽象                                     |
| `skill.py`   | `SkillSpec`, `Skill`, `SkillRegistry`           | 技能 (比 Tool 粗粒度)                            |
| `paws.py`    | `PawsEngine`                                    | 工具执行引擎: match → security → execute → audit |
| `matcher.py` | `KeywordToolMatcher`                            | 基于关键词的意图→工具匹配                        |

**`RiskLevel` 枚举**: `LOW | MEDIUM | HIGH`

**`ToolSpec`**:

```python
@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict          # JSON Schema 参数定义
    risk_level: RiskLevel
    category: str
    requires_approval: bool
```

**`ToolRegistry`**: 支持两级级联查找 (私有 → colony 共享)，可生成 OpenAI function call schema。

**`PawsEngine`**: 标准四步执行流程:
1. **match** — 按名称查找工具
2. **security** — 检查风险等级 + 确认要求
3. **execute** — 执行 handler (含超时控制)
4. **audit** — 审计日志记录

**`KeywordToolMatcher`**: 基于关键词重叠的打分匹配:
- 名称匹配 → +20 或 +10
- 描述匹配 → +5
- 类别匹配 → +3
支持可插拔的自定义评分器和过滤器。

---

### 3.23 Pluggable 混入 (pluggable.py)

**职责**: 为所有器官和组件提供统一的插件挂载/卸载/运行机制。

**`Pluggable` 类**:
```python
class Pluggable:
    HOOKS: tuple[str, ...] = ()  # 子类声明支持的钩子名
    
    def mount_plug(self, hook: str, fn: Callable) -> None
    def unmount_plug(self, hook: str, fn: Callable) -> None
    async def _run_plugs(self, hook: str, *args, **kwargs) -> Any
```

**三种执行模式**:
- **first-hit** (默认): 返回第一个非空结果，短路
- **merge-enhance**: 聚合并增强
- **full-replace**: 完全替换原始行为

---

## 4. 神经解剖架构

### 4.1 器官分类与职责

```
五大类别 (Category):
┌──────────────────────────────────────────────────────────────────┐
│ BRAIN (大脑区域) — 9个器官                                        │
│   THALAMUS      → 丘脑：感官中继，所有外部输入的第一站              │
│   HIPPOCAMPUS   → 海马体：记忆存储、检索、关联                      │
│   CEREBRUM      → 大脑：LLM 推理、思考                             │
│   CEREBELLUM    → 小脑：动作协调，输出到效应器                       │
│   AMYGDALA      → 杏仁核：安全评估、风险检测（可绕过大脑直接行动）    │
│   FRONTAL       → 前额叶：决策规划、任务编排                         │
│   HYPOTHALAMUS  → 下丘脑：稳态维护（衰减、清理、压缩）               │
│   CORTEX        → 皮层：世界观构建、规则提炼 (L0-L3)                │
│   BRAINSTEM     → 脑干：总调度器，连接所有脑区和感官                  │
├──────────────────────────────────────────────────────────────────┤
│ SENSE (感官) — 4个器官                                            │
│   EARS          → 听觉输入 (text/voice)                            │
│   EYES          → 视觉输入 (image/vision)                          │
│   WHISKERS      → 触觉/异常感知                                     │
│   PAWS          → 执行输出 (tool call / action) ★也是效应器        │
├──────────────────────────────────────────────────────────────────┤
│ VOICE (发声) — 3个器官                                             │
│   MOUTH         → 语音/文本输出                                     │
│   PURR          → 呼噜 (非语言状态信号: 满意/不满)                  │
│   TAIL          → 尾巴 (非语言状态信号: 摇摆/竖起/夹住)             │
├──────────────────────────────────────────────────────────────────┤
│ GROWTH (生长) — 4个器官                                            │
│   PINEAL_GLAND  → 松果体: 洞察融合 (自我+群体)                      │
│   ANOMALY_GROWTH → 异常检测与学习                                   │
│   CORRECTION_GROWTH → 纠错学习                                      │
│   CRYSTALLIZER  → 知识结晶（从经验到知识）                           │
│   ROLE_EMERGENCE → 角色涌现（动态专业化）                            │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 默认神经通路图

```
                        ┌─────────┐
                        │  EARS   │ (听觉)
                        └────┬────┘
                             │
                        ┌────▼────┐        ┌─────────┐
                        │THALAMUS │◄───────│  EYES   │ (视觉)
                        │ (丘脑)  │        └─────────┘
                        └────┬────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
     ┌────▼────┐       ┌────▼────┐       ┌─────▼─────┐
     │CEREBRUM │       │BRAINSTEM│       │ AMYGDALA  │
     │ (大脑)  │◄──────│ (脑干)  │──────►│ (杏仁核)  │
     │ LLM推理 │       │ 总调度  │       │ 安全评估  │
     └────┬────┘       └────┬────┘       └─────┬─────┘
          │                 │                   │
     ┌────▼────┐       ┌────▼────┐        ┌─────▼─────┐
     │CEREBELLUM│      │HIPPOCAMPUS│      │ CEREBELLUM│
     │ (小脑)  │      │ (海马体) │      │ (应激通道)│
     │ 动作协调│      │ 记忆存储 │      └─────┬─────┘
     └────┬────┘      └──────────┘            │
          │                                    │
     ┌────▼────┬──────┬──────┬───────────────┘
     │         │      │      │
 ┌───▼──┐ ┌───▼──┐ ┌─▼──┐ ┌▼────┐
 │MOUTH │ │ PURR │ │TAIL│ │PAWS │
 │(口)  │ │(呼噜)│ │(尾)│ │(爪) │
 └──────┘ └──────┘ └────┘ └────┘
  文本输出  流式信号  状态   工具执行

            ┌────────────────────────┐
            │    内部环路 (可同时)     │
            │  FRONTAL → CORTEX      │ 决策 → 世界观
            │  HYPOTHALAMUS 维护      │ 稳态衰减
            │  CatSelf 快照/反思      │ 自我模型
            │  Epiphany 管道         │ 洞察融合
            └────────────────────────┘

  图例: ──► 单向    ◄──► 双向    ★ 并行分支
```

---

## 5. 默认实现层 (defaults/)

### 5.1 工厂函数 (factory.py)

**`create_cat(name, **organs)`** — 一站式猫工厂:

```python
def create_cat(
    name: str,
    *,
    renovated: bool = True,           # 是否使用精装器官
    cerebrum=None,                     # 必须提供: LLM 实现
    thalamus=None, cerebellum=None,
    hippocampus=None, amygdala=None,
    frontal=None, hypothalamus=None,
    cortex=None, brainstem=None,
    ears=None, eyes=None, whiskers=None,
    paws=None, mouth=None, purr=None,
    tail=None, pineal_gland=None,
    anomal_growth=None, correction_growth=None,
    crystallizer=None, role_emergence=None,
    keyword: KeywordPreset = KW_EN,
    prompt: PromptPreset = PROMPT_DEFAULT,
    colon_id=None, storage=None,
    scribble_pad=None, cat_self=None,
    **kw
) -> CatBase:
```

**自动组装流程**: 创建 CatBase → mount_known_organs → 建立 wiring → 注册 built-in reflexes → wiring.freeze()

**`create_colony(colony_id, **kw)`** — Colony 工厂，装配 SharedStorage + ColonyRules。

### 5.2 无操作桩 (organs.py)

15 个 `Noop*` 类，每个对应一个器官 Protocol 的默认无操作实现。所有 Noop 类继承 `Pluggable`:

| Noop 类 | 对应器官 | 实现风格 |
|----------|---------|---------|
| `NoopThalamus` | 丘脑 | ALGORITHM |
| `NoopHippocampus` | 海马体 | ALGORITHM |
| `NoopAmygdala` | 杏仁核 | RULE |
| `NoopFrontal` | 前额叶 | ALGORITHM |
| `NoopHypothalamus` | 下丘脑 | ALGORITHM |
| `NoopCortex` | 皮层 | RULE |
| `NoopBrainstem` | 脑干 | ALGORITHM |
| `NoopEars` | 听觉 | ALGORITHM |
| `NoopEyes` | 视觉 | ALGORITHM |
| `NoopWhiskers` | 触觉 | ALGORITHM |
| `NoopPaws` | 执行 | ALGORITHM |
| `NoopMouth` | 发声 | ALGORITHM |
| `NoopPurr` | 呼噜 | ALGORITHM |
| `NoopTail` | 尾巴 | ALGORITHM |

所有 Noop 类都有 `impl_style` 属性返回其实现风格，以及 `diagnose()` 方法返回诊断信息。它们是麻雀虽小的完整器官——有骨架但无血肉，供应用层替换。

### 5.3 精装器官 (renovated.py)

Renovated 器官是带有预制逻辑的实现，提供比 Noop 更丰富的默认行为：
- `RenovatedThalamus` — 带关键词路由的丘脑
- `RenovatedAmygdala` — 带危险词检测的杏仁核
- `RenovatedCortex` — 带规则提取的皮层
- 等等

**dual track 机制**: `create_cat(renovated=True)` 使用精装器官，`renovated=False` 使用 Noop 桩。也可以**逐器官混合**: 部分使用精装，部分自定义。

### 5.4 存储实现 (stores.py)

纯内存实现，供开发/测试使用:
- `InMemoryGraphStore` — `GraphStorageProtocol` 实现
- `InMemoryL6Store` — `L6StorageProtocol` 实现
- `InMemoryVectorStore` — `VectorStorageProtocol` 实现
- `InMemorySharedStore` — `SharedStorageProtocol` 实现

### 5.5 预设 (presets.py)

**关键词预设**:
- `KW_EN` — 英文关键词: stop_words, command_patterns, danger_patterns, priority_keywords
- `KW_ZH` — 中文关键词: 停用词、命令模式、危险模式、优先关键词
- `KW_BILINGUAL` — 中英双语合并

**提示预设**:
- `PROMPT_DEFAULT` — 英文默认提示
- `PROMPT_ZH` — 中文默认提示

**`KeywordPreset` 数据类**:
```python
@dataclass(frozen=True)
class KeywordPreset:
    name: str
    stop_words: frozenset[str]
    command_patterns: dict[str, str]
    danger_patterns: frozenset[str]
    priority_keywords: frozenset[str]
```

**`PromptPreset` 数据类**:
```python
@dataclass(frozen=True)
class PromptPreset:
    name: str
    templates: dict[str, str]
    pre_prompt: str
    post_prompt: str
```

---

## 6. Plus 扩展模块 (plus/)

### 6.1 浏览器工具 (browser.py)

**`BrowserTool`** — 基于 Playwright 的浏览器自动化:
- 支持 headless / headed 模式
- 导航: `navigate(url)`
- 交互: `click(selector)`, `type_text(selector, text)`
- 内容获取: `get_content()`, `get_text(selector)`, `screenshot(path)`
- JS 执行: `evaluate(js)`
- 实现了 `diagnose()` 接口

### 6.2 向量存储 (chroma_store.py)

**`ChromaStore`** — ChromaDB 向量存储，实现 `VectorStorageProtocol`:
- `add(text, metadata)` — 添加文档
- `search(query, k)` — 语义搜索
- `delete(doc_id)` — 删除
- `count()` / `list_collections()` — 管理
- 支持持久化存储和自定义 embedding 函数

### 6.3 知识结晶器 (crystallizer.py)

**`Crystallizer`** — 三层知识结晶引擎:
- **L1**: 工具使用频率热点检测 → 自动提升为 Skill
- **L2**: 重复路径序列检测 → 自动注册为 Chain
- **L3**: 高置信度修正 → 自动固化为永久知识
- 支持可插拔检测器 (`DefaultDetector`) 和阈值配置

| 方法 | 层级 | 功能 |
|------|------|------|
| `record(slug)` | L1 | 记录工具调用 |
| `hotspots() / detect()` | L1 | 检测热点，提升 Skill |
| `record_sequence(seq)` | L2 | 记录执行序列 |
| `detect_patterns()` | L2 | 检测模式，注册 Chain |
| `record_correction(key, val, conf)` | L3 | 记录高置信度修正 |
| `detect_knowledge()` | L3 | 固化为永久知识 |

### 6.4 MCP 客户端 (mcp_client.py)

**`MCPClient`** — Model Context Protocol 多服务器客户端:
- 通过 stdio 子进程或 HTTP 传输连接外部 MCP 服务器
- `add_server(MCPServerConfig)` — 添加 MCP 服务器
- `discover()` — 发现工具列表
- `call_tool(server, tool, args)` — 调用远程工具
- 纯 JSON-RPC 2.0 实现，零外部 MCP SDK 依赖

### 6.5 Skill 加载器 (skill_loader.py)

**`SkillLoader`** — 从目录递归扫描 `SKILL.md` 文件:
- `scan_directory(path)` — 扫描目录，解析 YAML frontmatter
- `register_all(registry)` — 批量注册到 SkillRegistry
- Markdown 正文作为工具执行结果 (tool result content)

### 6.6 网关适配器 (gateway/)

Gateway 是猫的"皮肤"——所有外部 I/O 的唯一出入口。Gateway 是独立子系统，与 CatBase 组合而非继承。1 Cat : 1 Gateway : N Adapters。

| 适配器 | 协议 | 用途 |
|--------|------|------|
| `HttpAdapter` | HTTP POST + SSE | JSON 请求/响应，SSE 流式 (`Accept: text/event-stream`) |
| `WsAdapter` | WebSocket (RFC 6455) | 文本帧双向通信，流式推送 |
| `WebhookAdapter` | HTTP POST | Webhook 回调骨架，可继承适配飞书/微信 |
| `CliAdapter` | stdio / asyncio.Queue | 终端交互 / Textual TUI 集成 |
| `IpcAdapter` | Unix Socket + JSON-line | 桌面应用进程间通信 |

所有适配器纯 asyncio / stdlib 实现，零外部依赖。

### 6.7 内置工具 (plus/tools/)

每只猫开箱即用的 4 个基础工具 (`BUILTIN_TOOLS`):

| 工具 | 功能 | 安全机制 |
|------|------|---------|
| `plus_read_file` | 读取文件内容 | workspace 沙箱 + 符号链接穿越防护 + 1MB 限制 |
| `plus_write_file` | 写入文件内容 | workspace 沙箱 + 路径安全检查 |
| `plus_run_command` | 执行 shell 命令 | `shlex.split` 安全解析 + 环境变量白名单 |
| `plus_http_get` | HTTP GET 请求 | httpx 异步请求，响应长度限制 |

---

## 7. 依赖关系

### 7.1 项目依赖 (pyproject.toml)

**核心依赖** (`meowcat`):
- `pydantic >= 2.0` — 数据模型 (Reflex, PerceptionContext, models)
- `typing_extensions` — 跨 Python 版本的 typing 支持

**扩展依赖** (`meowcat[plus]`):
- `httpx` — HTTP 客户端 (http_get, MCP HTTP transport)
- `playwright` — 浏览器自动化 (BrowserTool)
- `chromadb` — 向量数据库 (ChromaStore)

**测试依赖** (`dev`):
- `pytest` / `pytest-asyncio` — 测试框架

### 7.2 内部依赖图

```
                    ┌──────────────┐
                    │  anatomy.py  │ (零依赖 — 最底层)
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     ┌────────────┐ ┌────────────┐ ┌──────────────┐
     │protocols.py│ │pluggable.py│ │  errors.py   │
     └─────┬──────┘ └─────┬──────┘ └──────────────┘
           │              │
    ┌──────┼──────────────┼──────────────────────┐
    ▼      ▼              ▼                      ▼
┌────────┐┌────────┐┌──────────┐┌─────────────────┐
│host.py ││wiring.py││events.py ││protocols_storage│
└───┬────┘└───┬─────┘└────┬─────┘└────────┬────────┘
    │         │           │               │
    └────┬────┴───────────┴───────────────┘
         │
    ┌────▼─────┐
    │nervous.py│ ←── 依赖 host.py + wiring.py
    └────┬─────┘
         │
    ┌────▼────────────────────┐
    │     assembly.py         │ ←── 组合 host/wiring/nervous/events/reflex
    │     (CatBase)           │     依赖 protocols.py, anatomy.py, models.py
    └────────┬───────────────┘
             │
    ┌────────┼────────────────────────────────┐
    ▼        ▼                ▼               ▼
┌────────┐┌──────────┐┌──────────────┐┌──────────────┐
│reflex  ││biology/  ││  tools/      ││  colony/     │
│.py     ││(高级模块)││  (工具系统)  ││  (多猫容器)  │
└───┬────┘└────┬─────┘└──────┬───────┘└──────┬───────┘
    │          │              │               │
    └──────────┴──────────────┴───────────────┘
                       │
              ┌────────▼────────┐
              │   defaults/     │ ←── 组合 Noop + Renovated + factory
              │   (默认实现层)  │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │     plus/       │ ←── 可选扩展 (Browser, Chroma, MCP...)
              │   (独立可选包)  │
              └─────────────────┘
```

**关键依赖原则**:
- `anatomy.py` 零依赖，被几乎所有模块引用
- `biology/__init__.py` 含懒加载机制，避免循环依赖
- `tools/__init__.py` 使用 `__getattr__` 将具体实现委托给 `plus/`，框架层零 I/O
- `plus/` 可选安装，不增加核心包体积
- CatBase (assembly.py) 是组合节点：组合各种子系统但不触发反向依赖

---

## 8. 项目运行方式

### 8.1 安装

```bash
# 核心框架
pip install meowcat

# 含扩展模块 (浏览器、ChromaDB、MCP 等)
pip install meowcat[plus]

# 开发安装
pip install -e ".[plus,dev]"
```

### 8.2 快速使用

**Renovated 模式（精装，20 器官即用）**:
```python
from meowcat.defaults import create_cat, KW_BILINGUAL, PROMPT_ZH

class MyBrain:
    name = "cerebrum"
    async def generate(self, prompt, system_prompt=None, **kw) -> str:
        return f"Meow! You said: {prompt[:50]}"

cat = create_cat("Kitty", cerebrum=MyBrain(),
                 keyword=KW_BILINGUAL, prompt=PROMPT_ZH)

# Path — 原子信号
result = await cat.path_registry.run("locate", query="weather")

# Chain — 命名序列
result = await cat.chain_registry.run("full_reasoning", prompt="Why is the sky blue?")

# Loop — 闭环
result = await cat.run_loop("conversation", message="Hello!")

# 统一感知入口
reply = await cat.perceive("What's the weather today?")
```

**Noop 模式（空壳，自行组装）**:
```python
cat = create_cat("Kitty", cerebrum=MyBrain(), renovated=False)
# 20 个器官均为安全无操作桩，自行挂载自定义实现
```

**自定义预设**:
```python
from meowcat.defaults import create_cat, KeywordPreset, PromptPreset

cat = create_cat("my-bot", cerebrum=my_llm,
    keyword=KeywordPreset(
        name="logistics",
        stop_words=frozenset({"uh", "um"}),
        command_patterns={"ship": "action", "track": "memory"},
        danger_patterns=frozenset(),
        priority_keywords=["shipping", "logistics", "delivery"],
    ),
    prompt=PromptPreset(
        name="Logistics",
        templates={"chat": "You are a logistics AI."},
        pre_prompt="You are a professional logistics AI.",
        post_prompt="Do not promise specific delivery times.",
    ),
)
```

### 8.3 Colony 多猫模式

```python
# 创建 Colony
colony = create_colony("my-colony")

# 在 Colony 中创建多只猫
cat_a = colony.create_cat("analyst", cerebrum=AnalystBrain())
cat_b = colony.create_cat("executor", cerebrum=ExecutorBrain())

# 猫间通信
await colony.signal_between("analyst", "executor",
    "brain", "amygdala", "assess", input=data)

# 广播
await colony.broadcast("alert", level="high", message="Anomaly detected")

# 共享存储
await colony.shared_set("knowledge/weather", {"city": "NYC", "temp": 22})
result = await colony.shared_get("knowledge/weather")
```

### 8.4 运行测试

```bash
# 运行全部测试
pytest tests/

# 运行特定版本测试
pytest tests/test_v510_builtin_equivalence.py

# 按标记运行
pytest tests/ -m "not slow"

# 并行运行
pytest tests/ -n auto
```

**测试文件组织**:
- 60+ 测试文件，按版本号命名 (`test_v*.py`)
- `conftest.py` 提供 `cat_base` 等通用 fixture（使用 `meowcat.testing.make_cat`）
- `__init__.py` 确保测试目录作为 package 导入

---

## 9. 测试系统

### 9.1 测试设施

- **`meowcat.testing`** — 测试辅助模块，提供 `make_cat()` 和 `make_test_colony()` 等工厂函数
- **pytest fixtures** — `conftest.py` 中定义 `cat_base` fixture 提供最小 CatBase 实例
- **独立测试** — 测试完全不依赖 meowagent 上层应用

### 9.2 测试覆盖

| 类别 | 测试文件 (部分) |
|------|---------------|
| 框架核心 | `test_core.py`, `test_assembly.py`, `test_protocols.py` |
| Wiring | `test_wiring.py`, `test_v051_wiring.py` |
| Reflex | `test_reflex.py`, `test_v051_reflex.py`, `test_v1018_reflex_security.py` |
| Biology | `test_biology.py`, `test_v051_biology.py`, `test_v1123_scribble_pad.py` |
| Colony | `test_v102_colony.py`, `test_v1107_group_chat.py`, `test_v1012_colony_federation.py` |
| Pluggable | `test_v107_pluggable.py` |
| Gateway | `test_v1010_gateway.py`, `test_v1214_adapters.py` |
| Events | `test_v1218_event_safety.py` |
| Circuit Breaker | `test_v1219_circuit_breaker.py` |
| CatSelf | `test_v120_cat_self.py` |
| Crystallizer | `test_v1117_crystallizer.py`, `test_v1125_crystallizer_l2l3_cortex.py` |
| Active Growth | `test_v1126_active_growth.py` |
| Organ Spec | `test_v510_organ_spec.py`, `test_v510_builtin_equivalence.py` |

---

## 10. 关键设计原则

### 10.1 Slot-Plug 分离
框架定义器官接口 (Slot = Protocol)，应用层提供具体实现 (Plug)。这是整个框架最核心的设计原则。OrganSpec 作为 SSOT 定义每个 Slot 的全貌：合约类型、允许的输入/输出边、读写权限、支持实现风格。

### 10.2 组合优于继承
CatBase 不继承任何组件，而是通过组合持有 OrganHost + Wiring + Nervous + ReflexArc + EventBus 五个子系统。这也是"5核"设计。

### 10.3 Facade 模式
CatBase 对外提供简洁的 `cat.ears`、`cat.signal(...)`、`cat.perceive(...)` 接口，内部通过 `__getattribute__` 拦截转发到子系统。

### 10.4 零 I/O 核心 + 可选 I/O 扩展
框架核心 (`meowcat`) 没有任何文件/网络 I/O。所有具体 I/O 实现 (浏览器、命令行、HTTP、ChromaDB) 都位于 `plus/`，通过 `pip install meowcat[plus]` 可选安装。

### 10.5 四层执行抽象
Path (原子信号) → Chain (序列+回滚) → Loop (闭环+事件) → LoopSequence (编排) — 从微观到宏观，层层组合。

### 10.6 双层闭环
内环 (CatSelf 自我进化): 每个动作前冻结快照，动作后反思写回。外环 (Colony 群体智能): 共享存储 + 跨猫信号 + 群体成长 + 联邦通信。

### 10.7 防御性设计
- Wiring.freeze() 冻结后不可修改
- 每条 (organ, method) 独立熔断器
- 禁止边优先于允许边
- Kitten 机制实现细化权限控制
- 所有 Noop 器官不会产生副作用

### 10.8 懒加载导入
`import meowcat` 只加载骨架 (anatomy + protocols + errors)。完整模块树在首次访问时按需展开。`biology/__init__.py` 和 `tools/__init__.py` 均通过 `__getattr__` 实现子模块懒加载。

### 10.9 事件驱动的可观测性
所有关键操作通过 EventBus 发布事件。Telemetry 系统 (Tracer + Metrics) 挂载在 Nervous 中间件链上，零额外开销。

### 10.10 零硬编码策略
所有阈值、危险词列表、关键词模式、语言预设都是构造函数参数 (Pydantic / frozen dataclass)。双语支持 (KW_EN / KW_ZH / KW_BILINGUAL) 通过预设切换，不需改代码。

---

> **文档生成日期**: 2026-05-05  
> **项目版本**: 0.5.9+ (>= v1.2 特性已融入)  
> **覆盖模块**: 40+ 个源文件, 60+ 个测试文件

