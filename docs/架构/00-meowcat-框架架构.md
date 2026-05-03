# meowcat — 猫神经框架

> 独立 Python 包，零依赖 meowagent，定义「什么是一只猫」。
> 已作为 `pip install meowcat` 发到 PyPI（v1.0.9）。

> **v1.0.9 文档更新**：v1.0.7~v1.0.9 三轮审计修正合入 — Pluggable 插接化、Voice/Growth 协议补齐、Protocol/Wiring 修正、CatBase 门面方法、Colony 语义别名。635 tests passed。

---

## 0. 概念层次（从原子到复合）

```
 抽象层次
 ─────────
                ┌──────────────┐
                │ LoopSequence │ ← 元闭环 = 多个 Loop 顺序执行 (loops.py, v1.0.4)
                │  (元闭环)    │
                └──────┬───────┘
                       │ 声明式组合
                ┌──────▼──────┐
                │    Loop     │  ← 闭环 = Chain + 触发/退出事件 (loops.py)
                │  (闭环)     │
                └──────┬──────┘
                       │ 声明式组合
                ┌──────▼──────┐
                │   Chain     │  ← 链路 = 命名 Path 序列，不要求闭环 (chain.py)
                │  (链路)     │
                └──────┬──────┘
                       │ 声明式组合
                ┌──────▼──────┐
                │    Path     │  ← 原子路径 = 单次 signal(from→to.method) (path.py)
                │  (原子路径)  │
                └──────┬──────┘
                       │ Wiring 约束
                ┌──────▼──────┐
                │ OrganSpec   │  ← 器官规范 = 入口N / 出口M / 方法级权限 (biology.py)
                │ (器官规范)  │
                └─────────────┘
```

> **Path → Chain → Loop → LoopSequence** 是声明式四层抽象。PathRegistry / ChainRegistry / LoopRegistry / LoopSequenceRegistry 分别在注册中心管理内置和用户自定义的定义，`CatBase` 在装配时自动加载（LoopSequence 除外，需手动注册）。

---

## 1. 定位：大树与树枝

```
┌─────────────────────────────────────────────────┐
│  meowagent (应用层)                                │
│  ├── Brain 器官: Cerebrum, Hippocampus, Thalamus...│
│  ├── Senses: Ears, Eyes, Whiskers                │
│  ├── Voice: Mouth, Purr, Tail                    │
│  ├── CLI/TUI, Server, Worker, Storage            │
│  └── 自定义...                                    │
│       ↑ 继承并实现                                  │
│       │                                           │
│  meowcat (框架层) ← 这是大树，只有树干和分叉规则        │
│  ├── 协议定义: 每个器官的接口 Protocol               │
│  ├── 神经通路: 器官间允许/禁止的连接                  │
│  ├── 装配骨架: CatBase / KittenBase                │
│  ├── 执行原语: signal / probe / inject / event    │
│  ├── 四层组合: Path → Chain → Loop                 │
│  ├── 工具系统: Tool / Skill / PawsEngine           │
│  └── 零依赖 meowagent，可独立 pip install           │
└─────────────────────────────────────────────────┘
```

**核心原则**：meowcat 是纯抽象的骨架。它只定义「猫应该有什么器官、器官间怎么连」，不写任何具体逻辑。任何 AI Agent 框架用户都可以 `from meowcat import CatBase` 来实现自己的猫。

---

## 2. 器官全景映射表（Agent 能力 → 器官 → 入/出口）

> 新开发者一看就懂：想加 X 能力 → 实现 Y Protocol → 从 A 进、往 B 出。

### 2.1 输入通道

| 输入类型      | 器官                | 坐标                | 入边 | 出边                                 | 关键方法                                                                       |
| ------------- | ------------------- | ------------------- | ---- | ------------------------------------ | ------------------------------------------------------------------------------ |
| 语音输入      | **Ears** (耳朵)     | `(sense, ears)`     | 外部 | → THALAMUS, AMYGDALA                 | `hear(raw: str\|bytes)`, `tag_emotion(episode)`                                |
| 图像/视频输入 | **Eyes** (眼睛)     | `(sense, eyes)`     | 外部 | → THALAMUS, AMYGDALA                 | `see(image_data, mime_type)`                                                   |
| 环境上下文    | **Whiskers** (胡须) | `(sense, whiskers)` | 外部 | → THALAMUS, AMYGDALA, ANOMALY_GROWTH | `feel_input(text)`, `feel_output()`, `detect_drift()`, `check_hallucination()` |

> **输入通道语义**：文字消息（CLI/飞书/微信/TUI）从 **Eyes** 进入（猫用眼睛看屏幕上的文字）；语音消息从 **Ears** 进入（猫用耳朵听声音）。所有输入统一先经过丘脑中继，再分发到对应脑区。
>
> 框架层 Eyes/Ears/Whiskers 设计为多模态输入，应用层可按需实现：
>
> - 只做文本 Agent → 只实现 Eyes 或 Ears 中的一个
> - 做多模态 Agent → 三个都实现
>
> **v1.0.8 应激反射**：三感官均可直连 AMYGDALA（bypass Thalamus），实现危险输入的快速告警。Whiskers 检测到异常可直连 ANOMALY_GROWTH 记录。

### 2.2 核心脑区

| Agent 能力             | 器官                      | 坐标                    | 入边 ←                                     | → 出边                                                         | 关键方法                                                           |
| ---------------------- | ------------------------- | ----------------------- | ------------------------------------------ | -------------------------------------------------------------- | ------------------------------------------------------------------ |
| 路由决策               | **Thalamus** (丘脑)       | `(brain, thalamus)`     | EARS, EYES, WHISKERS                       | CEREBRUM, BRAINSTEM, AMYGDALA, HIPPOCAMPUS                     | `locate(msg, session_id)`, `decide_route()`                        |
| 深度推理/LLM           | **Cerebrum** (大脑)       | `(brain, cerebrum)`     | THALAMUS, HIPPOCAMPUS, FRONTAL, BRAINSTEM  | HIPPOCAMPUS, CEREBELLUM, FRONTAL                               | `generate()`, `stream_generate()`                                  |
| 快速响应/模式匹配      | **Cerebellum** (小脑)     | `(brain, cerebellum)`   | CEREBRUM, AMYGDALA, BRAINSTEM              | PAWS, MOUTH, PURR, TAIL (效应器)                               | `generate()`, `stream_generate()`                                  |
| 记忆存储+检索          | **Hippocampus** (海马)    | `(brain, hippocampus)`  | CEREBRUM, FRONTAL, HYPOTHALAMUS, BRAINSTEM | CEREBRUM, CORTEX                                               | `remember()`, `locate()`, `fts_search()`, `add_entity()`           |
| 安全/拒绝/风险评估     | **Amygdala** (杏仁核)     | `(brain, amygdala)`     | THALAMUS, BRAINSTEM, EARS, EYES, WHISKERS  | CEREBELLUM, MOUTH, CEREBRUM, ANOMALY_GROWTH, CORRECTION_GROWTH | `assess_safety()`, `assess_tool_risk()`, `handle_rejection()`      |
| 提示词构建+生命周期    | **BrainStem** (脑干)      | `(brain, brainstem)`    | THALAMUS                                   | 全脑区 + 所有感官 + 所有嗓音 + 生长器官                        | `build_system_prompt()`, `cancel_current()`                        |
| 焦点/工作记忆/任务拆解 | **Frontal** (额叶)        | `(brain, frontal)`      | CEREBRUM, BRAINSTEM                        | CEREBRUM, HIPPOCAMPUS, BRAINSTEM                               | `detect_shift()`, `update_focus()`, `archive_focus()`              |
| 记忆衰减/压缩/自维护   | **Hypothalamus** (下丘脑) | `(brain, hypothalamus)` | BRAINSTEM                                  | HIPPOCAMPUS, CORTEX, 自环                                      | `run_maintenance()`, `decay_memories()`, `compress_long_history()` |
| 世界观/知识库          | **Cortex** (皮层)         | `(brain, cortex)`       | HIPPOCAMPUS, HYPOTHALAMUS, BRAINSTEM       | 无（终端器官）                                                 | `ingest()`, `synthesize()`, `record_weakness()`                    |

### 2.3 效应器（输出通道）

| 输出类型      | 器官            | 坐标             | 入边 ←                          | → 出边 | 关键方法                 |
| ------------- | --------------- | ---------------- | ------------------------------- | ------ | ------------------------ |
| 文本/语音输出 | **Mouth** (嘴)  | `(voice, mouth)` | CEREBELLUM, AMYGDALA, BRAINSTEM | 无     | `speak(text, **kwargs)`  |
| 流式状态      | **Purr** (呼噜) | `(voice, purr)`  | CEREBELLUM, BRAINSTEM           | 无     | `stream(text, **kwargs)` |
| 状态信号      | **Tail** (尾巴) | `(voice, tail)`  | CEREBELLUM, BRAINSTEM           | 无     | `render(state: dict)`    |

> **v1.0.7**: MouthProtocol / PurrProtocol / TailProtocol 补齐。

### 2.4 工具执行（Paws — 唯一入口）

| Agent 能力         | 器官            | 坐标            | 入边 ←                | → 出边 | 关键方法                                                                                                                        |
| ------------------ | --------------- | --------------- | --------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------- |
| Skill/MCP/命令执行 | **Paws** (四肢) | `(sense, paws)` | CEREBELLUM (**唯一**) | 无     | `execute(tool_name, params)`, `interact_with_tool()`（deprecated）, `run_command()`（deprecated）, `touch_file()`（deprecated） |

> **Paws 是工具执行的唯一入口**。所有 Skill、MCP 调用、命令执行都收敛到 Paws。
> `cerebrum → paws` 是禁止边（大脑不直连四肢）。工具调用必须走 `cerebrum → cerebellum → paws`。
>
> **v1.0.8**: 新增 `execute(tool_name, params)` 作为统一入口，旧方法标记 deprecated。

### 2.5 生长与进化

| Agent 能力   | 器官                 | 坐标                          | 入边 ←                        | → 出边              | 关键方法                                                 |
| ------------ | -------------------- | ----------------------------- | ----------------------------- | ------------------- | -------------------------------------------------------- |
| 异常模式学习 | **AnomalyGrowth**    | `(growth, anomaly_growth)`    | BRAINSTEM, AMYGDALA, WHISKERS | HIPPOCAMPUS, CORTEX | `record(reason, snippet, confidence, phase, session_id)` |
| 纠正固化     | **CorrectionGrowth** | `(growth, correction_growth)` | BRAINSTEM, AMYGDALA           | HIPPOCAMPUS, CORTEX | `record(wrong, correct, session_id, topic)`              |
| 技能结晶     | **Crystallizer**     | `(growth, crystallizer)`      | BRAINSTEM                     | 无                  | `crystallize(slug, hit_count)`, `hotspots(threshold)`    |
| 角色涌现     | **RoleEmergence**    | `(growth, role_emergence)`    | BRAINSTEM                     | 无                  | `record(pattern, evidence)`                              |

> **v1.0.8 具名化**：四个生长器官从共用的 `GrowthProtocol`（无方法签名）拆分为各自具名 Protocol。旧 `GrowthProtocol` 保留为 deprecated 兼容别名。
> **v1.0.8 新增禁止边**：`CEREBRUM → ANOMALY_GROWTH / CORRECTION_GROWTH`（大脑不直连生长，生长是副作用）。

### 2.6 编排与多 Agent

| Agent 能力          | 组件                      | 入边 ←            | → 出边                      |
| ------------------- | ------------------------- | ----------------- | --------------------------- |
| 任务编排/分身猫派生 | **Orchestrator** (编排器) | 由 BrainStem 触发 | spawn_kitten → absorb_merge |
| 子任务执行          | **Kitten** (分身猫)       | 主猫 spawn        | → MergeProposal 回传        |

---

## 3. 模块地图

```
meowcat/                          (47 个 .py 文件 + 3 个目录)
├── __init__.py        # 公开 API + __version__（动态读取 pyproject.toml）
├── __main__.py        # python -m meowcat 入口
├── py.typed           # PEP 561 类型标记
├── anatomy.py         # 器官坐标常量（单一事实来源）
├── biology.py         # 默认神经通路表 (ORGAN_SPECS, FORBIDDEN_PATHS)
├── protocols.py       # Protocol re-export 中心（v1.0.5 拆分后保留基础协议）
├── protocols_brain.py # 脑区 + LLM + Growth 协议 (v1.0.5)
├── protocols_sense.py # 感官协议 (v1.0.5)
├── protocols_storage.py # 存储协议 (v1.0.5)
├── protocols_voice.py # 嗓音协议 Mouth/Purr/Tail (v1.0.7)
├── assembly.py        # CatBase 骨架类 + CLI 门面方法 (v1.0.1 KittenBase 并入, v1.0.9 门面)
├── wiring.py          # 神经布线图 (Wiring: 有向图 + freeze)
├── nervous.py         # 神经信号系统 (signal / probe, 7 步校验)
├── reflex.py          # 反射弧系统 (Reflex, ReflexRegistry, ReflexArc)
├── events.py          # 事件总线 (pub/sub)
├── pipeline.py        # Pipeline 执行器 (Stage 顺序执行)
├── host.py            # OrganHost 器官容器
├── loop.py            # 闭环事件名常量 (Lifecycle + Nerve + Kitten)
├── path.py            # Path 原子路径 + PathRegistry + 22 BUILTIN_PATHS (v0.5.27, v1.0.8 精简)
├── chain.py           # Chain 数据类 + ChainRegistry + 5 BUILTIN_CHAINS (v0.5.28a)
├── loops.py           # Loop 数据类 + LoopRegistry + 5 BUILTIN_LOOPS (v0.5.28b)
│                      #   + LoopSequence + LoopSequenceRegistry (v1.0.4)
├── colony.py          # Colony 猫群容器 — 多猫对等协作 (v1.0.2, v1.0.9 别名)
├── pluggable.py       # Pluggable mixin — 器官插件系统 (v1.0.7)
├── pathways.py        # [deprecated] 旧版 Pathways 命名空间（委托给 PathRegistry）
├── models.py          # 数据形状 (Pydantic: EntityShape, PipelineContext, 等)
├── errors.py          # 框架异常 (8 种)
├── perception.py      # 感知上下文 (PerceptionContext, Modality)
├── organ_base.py      # OrganMixin 便捷基类
├── organ_roles.py     # ORGAN_ROLES 声明（器官角色可读描述）
├── diagnose.py        # Stethoscope 听诊器（全身体检 probe 工具）
├── inject.py          # Needle 注射器（绕过 wiring 的调试写通路）
├── tools/             # 框架工具子系统
│   ├── __init__.py
│   ├── tool.py        #   Tool / ToolSpec / ToolRegistry / RiskLevel
│   ├── skill.py       #   Skill / SkillSpec / SkillRegistry
│   ├── builtin.py     #   BUILTIN_TOOLS 内置工具注册
│   └── paws.py        #   PawsEngine 工具执行器（框架层接口）
├── defaults/          # 内置默认实现 + 内存存储
│   ├── __init__.py
│   ├── factory.py     #   create_cat() 一键工厂
│   ├── organs.py      #   Noop* 空器官实现（17 个，全部 Pluggable + HOOKS）
│   └── stores.py      #   InMemory* 存储实现
└── examples/          # 使用示例（7 个）
    ├── 01_organ_host_only.py
    ├── 02_wiring_validation.py
    ├── 03_event_bus_only.py
    ├── 04_custom_cat.py
    ├── 05_minimal_chat_cat.py
    ├── 06_custom_organ.py
    └── 07_custom_organ.py
```

---

## 4. 四子系统装配图 (CatBase)

一只完整的猫由 **4 个子系统** 拼装而成（Wiring 内嵌于 Nervous），外加 **Pluggable 器官插件系统**（v1.0.7）：

```
                    CatBase
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   OrganHost       EventBus       Nervous
   (器官容器)       (事件总线)      (信号分发)
   [Pluggable]         │          ├── Wiring (内嵌)
        │              │          └── probe (诊断)
        └──────────────┼──────────────┘
                       │
                  ReflexArc        ToolRegistry
                (反射弧引擎)       (工具注册中心)
                       │              │
                PathRegistry    SkillRegistry
                (原子路径表)    (技能注册中心)
                       │
                ChainRegistry
                (链路注册中心)
                       │
                LoopRegistry
                (闭环注册中心)
                       │
             LoopSequenceRegistry
               (元闭环注册中心)
```

### 4.1 OrganHost — 器官容器

```
mount(category, name, organ, protocol=...) →  注册器官，Protocol 校验
organ(category, name)                       →  取出器官
unmount(category, name)                     →  卸载器官
has_organ(category, name)                   →  是否已装载
list_all_organs()                           →  所有已挂载坐标
assert_organs_mounted(required)             →  断言必需器官已挂载
```

所有器官通过 `mount()` 装入 Cat，`unmount()` 卸下。装载时可选 Protocol 校验。

### 4.2 EventBus — 事件总线

```
on(event_name, handler)  →  注册监听
emit(event_name, **data) →  异步广播
off(event_name, handler) →  取消监听
```

pub/sub 模式。器官通过事件总线解耦通信。事件名常量定义在 `loop.py`。

### 4.3 Nervous — 信号分发（内嵌 Wiring）

```
┌─ Nervous ────────────────────────────────────┐
│  ├── Wiring (内嵌有向图)                      │
│  │   ├── connect(from, to)    — 白名单边      │
│  │   ├── forbid(from, to)     — 黑名单边      │
│  │   ├── freeze()             — 冻结不可改    │
│  │   └── assert_allowed()     — 通路校验      │
│  │                                            │
│  ├── signal(from, to, method, **kw) — 写通路  │
│  │   └── 校验: wiring → Protocol → 写权限     │
│  │                                            │
│  └── probe(to_organ)              — 读通路    │
│      └── 校验: is_organ_wired → Diagnosable   │
└──────────────────────────────────────────────┘
```

- **允许通路**: `biology.py` 中定义，每个器官的 `out_edges` 列出可通达的目标器官
- **禁止通路**: 全局禁止列表 `FORBIDDEN_PATHS`，如 cerebrum → paws
- **方法级权限** (v0.5.26): `OrganSpec.write_methods` / `write_callers` 约束写方法只能由特定调用方调用
- **freeze()**: 装配完成后冻结，不可再添加边

### 4.4 ReflexArc — 反射弧

```
                   感知输入 (perception)
                         │
                         ▼
              ┌──────────────────────┐
              │  ReflexRegistry      │
              │  按 priority 匹配     │
              │  找到第一个命中反射    │
              └──────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Reflex              │
              │  trigger (callable)   │
              │  path (器官坐标序列)   │
              │  stages (Pipeline)    │
              └──────────────────────┘
```

反射弧是「刺激 → 响应」的快速通道。匹配到 trigger 后直接走预设的信号通路，不经过 LLM 推理。

---

## 5. 四层组合：Path → Chain → Loop

### 5.1 Path — 原子路径

一条 Path 是一次 `cat.signal(from, to, method, **kw)` 的不可变配方（`path.py`）。

```python
Path("locate", THALAMUS, HIPPOCAMPUS, "locate", "read", "检索记忆")
Path("remember", BRAINSTEM, HIPPOCAMPUS, "remember", "write", "存储记忆")
Path("deep_reason", THALAMUS, CEREBRUM, "generate", "read", "深度推理")
Path("speak", CEREBELLUM, MOUTH, "speak", "write", "输出回复")
```

内置 22 条原子路径（`BUILTIN_PATHS`），覆盖记忆/推理/输出/维护/工具执行五大域。
自环路径（from == to）不走 wiring 校验，直接调本地方法。

### 5.2 Chain — 链路

一组命名的 Path 序列（`chain.py`），描述多步复合操作：

```python
MEMORY_SEARCH_CHAIN  = Chain("memory_search",  ("locate",),           "记忆检索")
FULL_REASONING_CHAIN = Chain("full_reasoning", ("deep_reason", "speak"), "推理+输出")
TOOL_EXEC_CHAIN      = Chain("tool_exec",      ("execute_tool",),     "工具执行")
MAINTENANCE_CHAIN    = Chain("maintenance",     ("decay", "cleanup_orphans"), "自维护")
DIAGNOSTIC_CHAIN     = Chain("diagnostic",      (),                   "诊断（空链路）")
```

执行时按序调用 Path，前一步返回值作为下一步的 kwargs。

### 5.3 Loop — 闭环

Chain + 触发事件 + 退出事件（`loops.py`），形成自动化执行回路：

```python
CONVERSATION_LOOP    # 常规对话: hear→decide_route→locate→deep_reason→speak→remember
TOOL_EXECUTION_LOOP  # 工具执行: hear→decide_route→execute_tool→speak→remember
DANGER_RESPONSE_LOOP # 危险响应: assess_safety
MAINTENANCE_LOOP     # 自维护: decay→cleanup_orphans (heartbeat.tick 触发)
DIAGNOSTIC_LOOP      # 诊断: 空链路，走 Stethoscope（手动触发）
```

执行流程: `触发事件 → chain 执行 → 退出事件`。通过 `cat.run_loop("conversation", message="你好")` 使用。

### 5.4 LoopSequence — 元闭环

多个 Loop 顺序执行（`loops.py`, v1.0.4），形成复合自动化序列：

```python
DAILY_MAINTENANCE_SEQ = LoopSequence(
    "daily_maintenance",
    ("maintenance", "diagnostic"),  # 先维护，再诊断
    description="日常维护 + 诊断",
)
```

通过 `cat.run_loopseq("daily_maintenance")` 使用。注意 LoopSequence 不会在 CatBase 装配时自动注册，需手动 `loopseq_registry.register()`。

### 5.5 注册中心链

```
PathRegistry  ← 独立注册、独立运行
    ↑ 引用
ChainRegistry ← 引用 PathRegistry 中的 Path 名
    ↑ 引用
LoopRegistry  ← 引用 ChainRegistry 中的 Chain 名
    ↑ 引用
LoopSequenceRegistry ← 引用 LoopRegistry 中的 Loop 名
```

每层级都可独立使用，上层组合下层。CatBase 构造时自动注册所有内置 Path/Chain/Loop（LoopSequence 需手动注册）。

---

## 6. 工具子系统 (Tools)

每只猫都有爪子，爪子能执行工具。`meowcat/tools/` 提供框架层工具抽象（v0.5.23）：

```
┌─ Tool ────────────────────────────────────────┐
│  ToolSpec: name / description / parameters     │
│           / risk (LOW/MEDIUM/HIGH) / category │
│  handler: async callable                       │
│  execute(**params) → str                       │
│  to_openai_schema() → dict                     │
└───────────────────────────────────────────────┘

┌─ Skill ───────────────────────────────────────┐
│  SkillSpec: name / description / tools / ...  │
│  组合多个 Tool 为可复用技能                     │
└───────────────────────────────────────────────┘

┌─ PawsEngine ──────────────────────────────────┐
│  工具执行引擎，挂载在 paws 器官上               │
│  负责: 查找工具 → 风险评估 → 执行 → 记录       │
└───────────────────────────────────────────────┘
```

**内置工具** (`builtin.py`): `read_file`, `write_file`, `run_command`, `http_get` — 所有猫都需要的原子操作。

ToolRegistry / SkillRegistry 挂载在 CatBase 实例上，装配时自动注册内置工具。

---

## 7. 事件总线 + 闭环事件

`loop.py` 定义三大闭环 + 生命周期 + 神经信号 + 分身猫事件名常量：

```
闭环 A (记→找→给): LocateEvent.PRE/POST/ROUTE_DECIDED
                   RememberEvent.PRE/POST/COMPRESS_PRE/POST

闭环 B (编排):     OrchestrateEvent.START/END

闭环 C (生长):     GrowthEvent.ANOMALY/CORRECTION/CRYSTALLIZE/ROLE_EMERGE

生命周期:          Lifecycle.START/SHUTDOWN/PERCEIVE_START/PERCEIVE_END

神经信号:          NerveEvent.SIGNAL（每次合法 signal 调用广播）

分身猫:            KittenEvent.SPAWNED/EXECUTING/COMPLETED/STUCK/DISMISSED/MERGE_ABSORBED
```

> 事件名常量在框架层定义，具体实现在应用层。

---

## 8. 数据流：一次完整对话（通过 Loop 执行）

```
用户说 "帮我查下这个数据库的表结构"
    │
    ▼
cat.run_loop("conversation", message="...")
    │
    ├── emit PERCEIVE_START
    ├── Chain "conversation_chain" 按序执行:
    │   ├── Path "hear"           → EARS.hear()
    │   ├── Path "decide_route"   → THALAMUS.decide_route()  (自环)
    │   ├── Path "locate"         → signal(THALAMUS, HIPPOCAMPUS, "locate")
    │   ├── Path "deep_reason"    → signal(THALAMUS, CEREBRUM, "generate")
    │   ├── Path "speak"          → signal(CEREBELLUM, MOUTH, "speak")
    │   └── Path "remember"       → signal(BRAINSTEM, HIPPOCAMPUS, "remember")
    └── 返回最终结果
```

---

## 9. 三种通信方式

| 方式              | 用途           | 校验                         | 场景            |
| ----------------- | -------------- | ---------------------------- | --------------- |
| `signal()`        | 写通路         | wiring + Protocol + 写权限   | 正常器官互访    |
| `probe()`         | 只读诊断       | is_organ_wired + Diagnosable | CLI/健康检查    |
| `Needle.inject()` | 绕过 wiring 写 | 无（调试/管理）              | 调试/测试/admin |

### 9.1 Stethoscope（听诊器）

```python
from meowcat.diagnose import Stethoscope

health = await Stethoscope.probe_all(cat)        # 全身体检
brain  = await Stethoscope.probe_category(cat, "brain")  # 脑区体检
hippo  = await Stethoscope.probe_organ(cat, "brain", "hippocampus")  # 单器官
```

CatBase 提供快捷方法: `cat.health_check()` / `cat.brain_check()`。

### 9.2 Needle（注射器）

绕过 wiring 校验，直接写入任何器官。安全机制：

- 不挂在 CatBase 上，必须显式 `from meowcat.inject import Needle`
- 构造时打 warning 日志
- 生产环境 `MEOWCAT_DISABLE_NEEDLE=1` 禁用

---

## 10. API 总览（供 meowcat 使用者）

```python
from meowcat import (
    # === 核心骨架 ===
    CatBase,              # 主猫基类：组合 4 子系统 + 4 注册中心 + 门面方法
    KittenBase,           # 分身猫基类：带隔离的只读影子

    # === 协议接口（实现器官前必须先看） ===
    OrganProtocol,         # 器官基协议
    Diagnosable,           # 诊断协议
    ThalamusProtocol,      # 丘脑协议（路由判断）
    HippocampusProtocol,   # 海马体协议（记忆存取）
    LLMBrainProtocol,      # LLM 大脑协议（推理）
    BrainStemProtocol,     # 脑干协议（生命周期管理）
    CortexProtocol,        # 皮层协议（世界观）
    AmygdalaProtocol,      # 杏仁核协议（安全检测）
    FrontalCortexProtocol, # 额叶协议（焦点/计划）
    HypothalamusProtocol,  # 下丘脑协议（稳态维护）
    EarsProtocol,          # 耳朵协议（输入监听+情绪标注）
    EyesProtocol,          # 眼睛协议（视觉输入）
    WhiskersProtocol,      # 胡须协议（环境感知）
    PawsProtocol,          # 爪子协议（工具执行）
    MouthProtocol,         # 嘴巴协议（文本输出, v1.0.7）
    PurrProtocol,          # 咕噜协议（流式输出, v1.0.7）
    TailProtocol,          # 尾巴协议（状态渲染, v1.0.7）
    AnomalyGrowthProtocol,    # 异常生长协议（v1.0.8）
    CorrectionGrowthProtocol, # 纠正生长协议（v1.0.8）
    CrystallizerProtocol,     # 结晶器协议（v1.0.8）
    RoleEmergenceProtocol,    # 角色涌现协议（v1.0.8）
    GrowthProtocol,        # 生长协议（deprecated 兼容别名）

    # === 四层组合 ===
    Path, PathRegistry, BUILTIN_PATHS,             # 原子路径（22 条）
    Chain, ChainRegistry, BUILTIN_CHAINS,          # 链路（5 条）
    Loop, LoopRegistry, BUILTIN_LOOPS,              # 闭环（5 条）
    LoopSequence, LoopSequenceRegistry,             # 元闭环（v1.0.4）

    # === 工具系统 ===
    Tool, ToolSpec, ToolRegistry, RiskLevel,       # 工具
    Skill, SkillSpec, SkillRegistry,               # 技能
    PawsEngine, BUILTIN_TOOLS,                     # 执行引擎 + 内置工具

    # === 插件系统 ===
    Pluggable,              # 器官插件 mixin（v1.0.7）

    # === 诊断/注入 ===
    Stethoscope,           # 全身体检
    Needle, NeedleDisabledError,  # 绕过 wiring 写入

    # === 数据形状 ===
    EntityShape, ConnectionShape, EpisodeShape,
    KittenCapability, SubTaskShape, MergeProposalShape,

    # === 装配 ===
    assemble_default_cat, create_cat,
    Colony,                # 猫群容器
)
```

### 最小使用示例

```python
from meowcat import CatBase, assemble_default_cat

# 方式 1：手动装配
class MyCat(CatBase):
    def __init__(self, cat_id: str):
        super().__init__(cat_id)
        # 挂载你的器官...
        self.mount("hippocampus", MyHippocampus())

cat = MyCat("my-cat")

# 方式 2：一键创建（使用默认 noop 器官）
cat = assemble_default_cat("my-cat")
```

---

## 11. 听诊器 probe 通路

除了 `signal()` 这条器官间互访的「写通路」之外，框架还提供一条只读诊断通路 `probe()`：

```
┌────────────────────────────────────────────────────┐
│  signal()  = 写通路                                │
│  器官 A → Wiring 校验 → 器官 B.any_method()        │
│  emit nerve.signal 事件、可写入                     │
├────────────────────────────────────────────────────┤
│  probe()   = 听诊器（只读通路）                      │
│  CLI → Wiring 校验(器官已wire?) → 器官.diagnose()  │
│  不 emit 事件、不写入、返回必须是 dict              │
├────────────────────────────────────────────────────┤
│  Needle.poke() = 注射器（绕过校验）                  │
│  直接调用任何器官的任何方法，仅用于调试/admin         │
│  生产环境可通过 MEOWCAT_DISABLE_NEEDLE=1 禁用       │
└────────────────────────────────────────────────────┘
```

**设计原则**:

- CLI 就是听诊器 — 不是独立工具，是猫自身的感官输入
- `probe()` 建在 `CatBase` 上，与 `signal()` 平级：signal=写，probe=读
- 安全约束：只允许已 wire 的器官、只允许调 `diagnose()` 方法、返回值必须是纯 dict
- 器官需实现 `Diagnosable` 协议才能被 probe（v0.5.14: OrganProtocol 继承 Diagnosable，所有器官强制可 probe）

---

## 12. 开发约束（必须遵守）

| 规则                 | 说明                                                       |
| -------------------- | ---------------------------------------------------------- |
| **零依赖 meowagent** | `meowcat/` 下任何一个 `.py` 都不能 `import meowagent`      |
| **Protocol 优先**    | 新器官先在 `protocols*.py` 定义接口，再写实现              |
| **Pluggable 优先**   | Noop 器官须继承 Pluggable + 声明 HOOKS（v1.0.7）           |
| **Cat 是唯一装配点** | brain 器官之间不互相 import，通过 signal/probe 通信        |
| **函数 ≤50 行**      | 保证可读性和可测试性                                       |
| 文件 ≤500 行         | 超过就拆分（v1.0.5 已拆分 protocols.py，当前全部 ≤500 行） |
| **优先四层 API**     | 新代码优先用 Path→Chain→Loop→LoopSequence，避免裸 signal   |

---

## 13. Colony（猫群）— 多主猫对等协作

> Colony 是框架层的多猫协作容器，Kitten 是主从模式，Colony 是对等模式，两者正交。

### 13.1 Kitten vs Colony 区别

```
 模式       Kitten (分身猫)              Colony (猫群)
───────    ───────────────────────    ──────────────────────────
 关系       主从 (parent → child)      对等 (peer ↔ peer)
 生命周期    主猫控制 (spawn/dismiss)    各自独立管理
 共享       结果回传 (MergeProposal)     SharedStorage 读写
 通信       单向: parent → kitten       双向: 任意 cat 间 signal
 适用场景    子任务拆分执行              多 Agent 协作、角色分工
```

### 13.2 架构

```
┌─────────── Colony ──────────────────────────────┐
│                                                   │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐        │
│  │  Cat A  │   │  Cat B  │   │  Cat C  │        │
│  │ (主猫)  │   │ (主猫)  │   │ (主猫)  │        │
│  │ cat_id= │◄─►│ cat_id= │◄─►│ cat_id= │        │
│  │  "a"   │   │  "b"   │   │  "c"   │        │
│  └────┬────┘   └────┬────┘   └────┬────┘        │
│       │             │             │              │
│       └─────────────┼─────────────┘              │
│                     │                            │
│              ┌──────▼──────┐                     │
│              │ SharedStorage│ ← 共享记忆/状态     │
│              └─────────────┘                     │
└─────────────────────────────────────────────────┘
```

每只猫都是独立的 `CatBase` 实例，各自拥有完整的 4 子系统 + 器官 + 注册中心。它们通过 `SharedStorage` 读写共享状态（记忆、实体、配置），也可以互相 `signal` 通信（只要 wiring 允许）。

### 13.3 核心 API

```python
from meowcat import CatBase, SharedStorageProtocol

class Colony:
    """猫群容器 — 管理多只主猫的对等协作"""

    def __init__(self, colony_id: str, storage: SharedStorageProtocol): ...

    # 注册/移除猫
    def register(self, cat: CatBase) -> None: ...
    def unregister(self, cat_id: str) -> None: ...
    def adopt(self, cat: CatBase) -> None: ...     # register 的语义别名 (v1.0.9)
    def release(self, cat_id: str) -> None: ...     # unregister 的语义别名 (v1.0.9)
    def get_cat(self, cat_id: str) -> CatBase: ...
    def list_cats(self) -> list[str]: ...

    # 广播
    async def broadcast(self, event: str, **data) -> list[Any]: ...
    async def health_check_all(self) -> dict[str, dict]: ...

    # 猫间通信
    async def signal_between(
        self, from_id: str, to_id: str,
        to_category: str, to_name: str,
        method: str, **kw
    ) -> Any: ...
```

### 13.4 SharedStorageProtocol

```python
class SharedStorageProtocol(Protocol):
    """Colony 共享存储协议 — 所有猫通过此接口读写共享状态"""

    async def get(self, namespace: str, key: str) -> Any: ...
    async def set(self, namespace: str, key: str, value: Any) -> None: ...
    async def delete(self, namespace: str, key: str) -> None: ...
    async def list_keys(self, namespace: str) -> list[str]: ...
    async def watch(self, namespace: str, pattern: str) -> AsyncIterator: ...
```

> 命名空间约定：`memories/`、`entities/`、`config/`、`tasks/`、`messages/`。应用层实现具体存储后端。

### 13.5 典型使用场景

```
场景 1: 角色分工协作
  Cat "planner" → 拆解任务 → SharedStorage.tasks/
  Cat "executor" → watch tasks/ → 执行 → SharedStorage.results/
  Cat "reviewer" → watch results/ → 审查 → SharedStorage.reviews/

场景 2: 多平台 Agent
  Cat "feishu"  → Eyes/飞书输入
  Cat "wechat"  → Eyes/微信输入
  Cat "cli"     → Eyes/CLI 输入
  三只猫共享同一个 Hippocampus 记忆 → SharedStorage.memories/

场景 3: 分布式负载
  Colony.broadcast("健康检查") → 每只猫返回状态
  按负载选择空闲猫处理新任务
```

### 13.6 安全约束

| 规则                   | 说明                                |
| ---------------------- | ----------------------------------- |
| wiring 跨猫隔离        | Cat A 的 wiring 不校验 Cat B 的器官 |
| signal_between 需授权  | 猫间 signal 需要双方 wiring 白名单  |
| SharedStorage 只读隔离 | 猫只能读自己的 `cat_id` 前缀数据    |

---

## 14. Pluggable — 器官插件系统（v1.0.7）

所有 Noop 器官实现 `Pluggable` mixin，支持运行时挂载/卸载插件（hook）。

### 14.1 Pluggable mixin

```python
from meowcat import Pluggable

class Pluggable:
    """插件化 mixin — run_plug / unmount_plug / list_plugs"""

    def mount_plug(self, hook: str, fn: Callable) -> None: ...
    def unmount_plug(self, hook: str) -> None: ...
    def list_plugs(self) -> dict[str, Callable]: ...
    def _run_plugs(self, hook: str, *args, **kwargs) -> Generator: ...
```

每个 Noop 器官通过 `HOOKS` 类变量声明可挂载的 hook 及其建议签名。17 个 Noop 器官全部插接化。

### 14.2 三种执行模式

| 模式  | 含义                                   | 示例器官                    |
| ----- | -------------------------------------- | --------------------------- |
| **A** | 首命中覆盖 — 第一个非默认值返回        | Amygdala                    |
| **B** | 合并增强 — 所有插件结果 merge 到默认值 | Whiskers, Ears, Hippocampus |
| **C** | 完全替代 — 插件返回值替代默认行为      | Mouth, Purr, Tail, Paws     |

### 14.3 使用示例

```python
from meowcat import NoopAmygdala

a = NoopAmygdala()
# 默认行为：安全
assert await a.assess_safety("hello") == {"safe": True, "risk": "none"}

# 挂载安全检测插件（模式 A：首命中覆盖）
a.mount_plug("assess_safety", lambda x: {"safe": False, "risk": "block"})
assert await a.assess_safety("hello") == {"safe": False, "risk": "block"}

# 卸载恢复默认
a.unmount_plug("assess_safety")
assert await a.assess_safety("hello") == {"safe": True, "risk": "none"}

# 查看可挂载 hook
assert "assess_safety" in NoopAmygdala.HOOKS
```

---

## 15. 相关文档

| 文档                                                      | 用途                                   |
| --------------------------------------------------------- | -------------------------------------- |
| `docs/架构/01-meowagent-应用架构.md`                      | meowagent 应用层架构                   |
| `docs/架构/02-应用层接入指南.md`                          | 从零构建应用的 step-by-step 指南       |
| `meowcat/README.md`                                       | meowcat 快速入门                       |
| `meowcat/examples/`                                       | 用法示例代码                           |
| `docs/meowagent/v0.5.20/00-boundary-meowcat-meowagent.md` | 边界划分 ADR（哪些归框架、哪些归应用） |
