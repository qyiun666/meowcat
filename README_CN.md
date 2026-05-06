<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Axonant/MeowAgent/main/assets/logo_white_240.png">
  <img alt="meowcat logo" src="https://raw.githubusercontent.com/Axonant/MeowAgent/main/assets/logo_dark_240.png" width="120">
</picture>

# 🐱 meowcat · 仿生神经 AI Agent 框架

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![version](https://img.shields.io/badge/version-1.2.36-lightgrey.svg)]()
[![pypi](https://img.shields.io/badge/pypi-meowcat-orange.svg)](https://pypi.org/project/meowcat/)
[![GitHub](https://img.shields.io/badge/GitHub-Axonant%2FMeowAgent-181717?style=flat-square&logo=github)](https://github.com/Axonant/MeowAgent)

> 🐱 **纯个人开发** — 如果觉得有用，给个 ⭐ star ⭐ 支持一下吧！

以猫的生物蓝图构建的 AI Agent 框架。定义器官、接通神经，猫便活了过来。

> 📖 **[AGENTS.md](AGENTS.md)** — 应用开发者入口（3 分钟建立心智模型）
>
> **框架定义骨架。你来选择材质。**
>
> 20 个器官 · 26 条路径 · 6 条链条 · 5 个循环 · 完整默认配置速查 → **[CATALOG.md](CATALOG.md)**

---

## 📐 meowcat 是什么？

meowcat 之于 AI Agent，如同骨骼之于身体 — 它定义结构、连接、信号流动的规则。

```
          Protocols    Anatomy    Wiring    Nervous    Reflex
            器官契约   仿生蓝图   神经通路   信号调度    反射弧
              │          │         │         │         │
              └──────────┴────┬────┴─────────┴─────────┘
                              │
                    CatBase (骨架 + 生命周期)
                              │
              ┌───────────────┼───────────────┐
              │               │               │
          OrganHost        Colony         defaults/
          器官挂载/校验    多猫容器       Noop空桩/Renovated简装
```

- **零 I/O 核心** — 框架层无文件/网络 I/O，纯抽象
- **Slot-Plug 解耦** — 框架定义插槽（Protocol），你来提供插头（实现）
- **可选电池包** — `pip install meowcat[plus]` 获得浏览器、ChromaDB、MCP、网关等

---

## ✨ 为什么是"猫"？

meowcat 将 AI Agent 建模为**猫的生物神经系统** — 一套经过亿万年进化验证的架构：

| 生物学事实             | meowcat 等价                                |
| :--------------------- | :------------------------------------------ |
| 丘脑路由所有感觉输入   | `Thalamus` — 唯一感觉中继枢纽               |
| 大脑负责深度推理       | `Cerebrum` — LLM 驱动的深度思考             |
| 小脑协调快速动作       | `Cerebellum` — 所有效应器的唯一入口         |
| 杏仁核触发恐惧反应     | `Amygdala` — 安全旁路（可绕过推理直接输出） |
| 海马体存储记忆         | `Hippocampus` — 实体图谱记忆                |
| 下丘脑维持体内稳态     | `Hypothalamus` — 记忆衰减 + 清理            |
| 皮层从经验中构建世界观 | `Cortex` — L0→L3 认知管线                   |
| 反射弧绕过大脑         | `ReflexArc` — 刺激→响应，零 LLM 依赖        |

**20 个器官。5 大类别。1 套统一神经系统。** 猫架构提供了扁平的 LLM 管线永远无法拥有的生物级防御层（杏仁核安全旁路、熔断器、禁止边）。

---

## 🎯 亮点

<table>
<tr>
<td width="50%">

### 🧬 仿生神经蓝图

仿照真实神经解剖学建模。20 个器官，5 大类别（大脑 / 感官 / 声音 / 存储 / 生长）。每个器官都有入口/出口规则、读写权限和支持的实现风格 — 如同真实的生物约束。

### 🔌 插槽-插头架构

框架定义**插槽**（Protocol 接口 + OrganSpec 契约）。你来提供**插头**（具体实现）。4 种插头风格：`ALGORITHM` | `RULE` | `MODEL` | `HYBRID`。按器官混合搭配。

### 🧠 四层执行模型

`Path`（原子信号）→ `Chain`（序列 + 回滚）→ `Loop`（触发 + 退出 + 事件）→ `LoopSequence`（编排）。从微观到宏观，层层可组合。

</td>
<td width="50%">

### 🛡️ 生物级防御层

- **杏仁核安全旁路** — 检测到危险 → 直接输出，零 LLM 推理
- **熔断器** — 按 (器官, 方法) 粒度独立熔断，连续失败 → 断路
- **禁止边** — 生物合理的接线约束（大脑不能直接控制爪子）
- **Kittens** — 细粒度权限视图（允许器官白名单 + 禁止方法）

### 🔄 两大闭环

- **内环（CatSelf）**：冻结快照 → 行动 → 反思 → 融合洞察 → 进化世界观
- **外环（Colony）**：共享存储 → 跨猫信号 → 集体生长 → 角色涌现

### 📦 零 I/O 核心 + 可选电池包

`pip install meowcat` → 纯框架，零文件/网络 I/O。`pip install meowcat[plus]` → 浏览器、ChromaDB、MCP、网关适配器、晶化器 — 所有 I/O 在可选的 `plus/` 包中。

</td>
</tr>
</table>

---

## 🏗️ 架构一瞥

```
                             ┌────────────────────┐
  外部世界 ─────────────────► │  Gateway (皮肤)     │  HTTP / WebSocket / CLI / IPC / Webhook
                             └────────┬───────────┘
                                      │
  ┌───────────────────────────────────▼───────────────────────────────────┐
  │                         cat.perceive()                                │
  │                                                                       │
  │   ┌──────────┐    ┌──────────┐    ┌──────────────────────────────┐   │
  │   │ 感官     │───►│ THALAMUS │───►│          脑区                │   │
  │   │ Ears     │    │ (中继)   │    │ Cerebrum Cerebellum Amygdala  │   │
  │   │ Eyes     │    └──────────┘    │ Frontal Hippocampus Cortex    │   │
  │   │ Whiskers │                    │ Hypothalamus Brainstem        │   │
  │   └──────────┘                    └──────────────┬───────────────┘   │
  │                                                  │                    │
  │                              ┌───────────────────▼───────────────┐   │
  │                              │           效应器                  │   │
  │                              │  Mouth (说话)  Purr (流式)       │   │
  │                              │  Tail (状态)   Paws (工具)        │   │
  │                              └───────────────────────────────────┘   │
  │                                                                       │
  │   ┌──────────────────────────────────────────────────────────────┐   │
  │   │  生长: PinealGland · AnomalyGrowth · CorrectionGrowth       │   │
  │   │        Crystallizer · RoleEmergence                          │   │
  │   └──────────────────────────────────────────────────────────────┘   │
  └───────────────────────────────────────────────────────────────────────┘
                                      │
                             ┌────────▼───────────┐
                             │  Colony (猫舍)      │  共享存储 · 联邦 · 跨猫信号
                             └────────────────────┘
```

---

## 🚀 快速开始

```bash
pip install meowcat
```

```python
from meowcat.defaults import create_cat

# 你的 LLM — 只需要 generate(prompt) → str
class MyCerebrum:
    name = "cerebrum"
    async def generate(self, prompt, system_prompt=None, **kw) -> str:
        return f"喵！{prompt[:100]}"

# 一行代码：完整装配的猫，20 器官 + 接线 + 反射弧
cat = create_cat("小喵", cerebrum=MyCerebrum())

# 统一感知入口 — 输入进入，回复出来
reply = await cat.perceive("今天天气怎么样？")

# Path: 原子器官间信号
result = await cat.path_registry.run("locate", query="东京天气")

# Chain: 命名路径序列
result = await cat.chain_registry.run("full_reasoning", prompt="天为什么是蓝的？")

# Loop: 带触发/退出事件的闭环执行
await cat.run_loop("conversation", message="你好，猫猫！")
```

---

## 🔬 插槽-插头模型

框架只定义**插槽（Slot）** — 器官长什么样、能连接谁、能读写什么、支持什么实现。你来提供**插头（Plug）** — 实际实现。

```python
# 框架定义插槽 (OrganSpec)
#   coord:          ("brain", "amygdala")
#   protocol:       AmygdalaProtocol
#   in_edges:       [THALAMUS, BRAINSTEM, EARS, EYES, WHISKERS]
#   out_edges:      [CEREBELLUM, MOUTH, CEREBRUM, ...]
#   read_methods:   [is_rejection, classify_rejection, assess_safety]
#   write_methods:  [handle_rejection, handle_correction]
#   write_callers:  [BRAINSTEM]   # 仅脑干可调用写方法
#   supported_styles: [ALGORITHM, RULE, MODEL, HYBRID]

# 你提供插头 — 必须满足 AmygdalaProtocol
class MyAmygdala:
    name = "amygdala"
    impl_style = ImplementationStyle.RULE

    async def assess_safety(self, input, **kw) -> SafetyReport:
        # 你的安全逻辑
        return SafetyReport(safe=True, risk_level=0)

cat = create_cat("小喵", cerebrum=MyLLM(), amygdala=MyAmygdala())
```

**各器官的插头风格** — 框架自动校验兼容性：

| 风格        | 说明            | 典型器官                           |
| :---------- | :-------------- | :--------------------------------- |
| `ALGORITHM` | 确定性，无 LLM  | Ears, Mouth, Purr, Tail, Brainstem |
| `RULE`      | 基于规则决策    | Amygdala, Cortex                   |
| `MODEL`     | LLM 驱动        | Cerebrum, Cerebellum               |
| `HYBRID`    | 算法 + LLM 结合 | Hippocampus, Frontal               |

---

## 🔗 四层执行模型

| 层                  | 原语                                 | 说明                                           |
| :------------------ | :----------------------------------- | :--------------------------------------------- |
| **L1 Path**         | `源器官 → 目标器官.方法`             | 原子器官间信号。26 条内置路径。                |
| **L2 Chain**        | `[path1, path2, ...] + rollback`     | 命名路径序列。前步结果传给后步。6 条内置链条。 |
| **L3 Loop**         | `Chain + trigger_event + exit_event` | 自治闭环。5 条内置循环。                       |
| **L4 LoopSequence** | `[loop1, loop2, ...]`                | 顺序或并行的多循环编排。                       |

```python
# L1: Path
await cat.path_registry.run("deep_reason", prompt="...")

# L2: Chain 带回滚
await cat.chain_registry.run("full_reasoning", prompt="...")
# = deep_reason → speak  （speak 失败则回滚）

await cat.chain_registry.run("maintenance")
# = decay → cleanup_orphans

# L3: Loop — 事件驱动的自治执行
await cat.loop_registry.start("conversation")
# 由 perceive.start 触发，conversation.end 退出

# L4: LoopSequence
await cat.loopseq_registry.run("daily_maintenance")
# = maintenance → diagnostic  （顺序执行）
```

---

## 🧭 数据流：从输入到输出

```
用户输入
    │
    ▼
┌──────────┐     ┌──────────┐     ┌─────────────────────────┐
│  EARS    │────►│ THALAMUS │────►│        脑区             │
│ (感官)   │     │ (中继)   │     │  ┌───────────────────┐  │
└──────────┘     └──────────┘     │  │ CEREBRUM (深度)   │  │
                                  │  │    ↓              │  │
                                  │  │ CEREBELLUM (快速) │  │
                                  │  │    ↓              │  │
                                  │  │ 效应器             │  │
                                  │  │ Mouth/Purr/Tail   │  │
                                  │  │ Paws (工具)       │  │
                                  │  └───────────────────┘  │
                                  └─────────────────────────┘
    │                                                     │
    │         ┌───────────────────────────┐               │
    └────────►│ AMYGDALA (安全旁路)        │───────────────┘
              │ 危险 → 直接输出            │
              └───────────────────────────┘
```

**每次输入都有两条通路：**

1. **推理通路**：EARS → THALAMUS → CEREBRUM → CEREBELLUM → MOUTH（完整推理）
2. **紧急通路**：EARS → THALAMUS → AMYGDALA → MOUTH（绕过大脑，即时安全响应）

---

## 📦 器官目录

### 9 大脑区域

| 器官             | 角色         | 核心特征                      |
| :--------------- | :----------- | :---------------------------- |
| **Thalamus**     | 感觉中继枢纽 | 所有输入必经此地              |
| **Cerebrum**     | 深度推理     | LLM 驱动，仅支持 MODEL/HYBRID |
| **Cerebellum**   | 快速响应     | 所有效应器的唯一入口          |
| **Hippocampus**  | 记忆图谱     | 实体-关联存储                 |
| **Amygdala**     | 安全旁路     | 可绕过推理直接触发输出        |
| **Frontal**      | 专注与规划   | 话题追踪、任务分解            |
| **Hypothalamus** | 体内稳态     | 记忆衰减、孤立清理            |
| **Cortex**       | 世界观蒸馏   | L0→L3 认知管线                |
| **Brainstem**    | 总调度       | 协调所有脑区                  |

### 4 感官 + 3 声音 + 5 生长

| 类别            | 器官                                                                                                                                  |
| :-------------- | :------------------------------------------------------------------------------------------------------------------------------------ |
| **感官 SENSE**  | Ears（文本）、Eyes（视觉）、Whiskers（异常检测）、Paws（工具 — 兼效应器）                                                             |
| **声音 VOICE**  | Mouth（说话）、Purr（流式状态）、Tail（状态栏）                                                                                       |
| **生长 GROWTH** | PinealGland（顿悟融合）、AnomalyGrowth（异常沉淀）、CorrectionGrowth（纠错固化）、Crystallizer（技能结晶）、RoleEmergence（角色涌现） |

---

## 🐱 Colony — 猫舍多猫容器

```python
from meowcat.defaults import create_colony

colony = create_colony("my-squad")

# 孵化多只猫到猫舍中
analyst  = colony.create_cat("analyst", cerebrum=AnalystBrain())
executor = colony.create_cat("executor", cerebrum=ExecutorBrain())

# 1:1 跨猫通信
await colony.signal_between("analyst", "executor",
    "brain", "amygdala", "assess_safety", input=data)

# 1:N 广播
await colony.broadcast("alert", level="high")

# 共享记忆
await colony.shared_set("knowledge/weather", {"city": "北京"})
result = await colony.shared_get("knowledge/weather")

# 联邦 — 跨主机猫舍通信
await colony.federate(transport)
await colony.signal_remote("other-colony", "cat-3", ...)
```

| 功能         | 说明                                                                 |
| :----------- | :------------------------------------------------------------------- |
| **跨猫信号** | 1:1 (`signal_between`)、1:N (`broadcast_request`)、N:N (`broadcast`) |
| **共享存储** | 命名空间：`owner/` `rules/` `knowledge/` `growth/` `cats/`           |
| **联邦**     | 跨主机猫舍 P2P 通信（请求-响应，30s 超时）                           |
| **集体生长** | 猫之间互相学习异常和纠错                                             |
| **角色涌现** | 行为模式 → 隐式角色分工                                              |

---

## 🛠️ 基于 meowcat 的应用

基于 meowcat 框架的完整 AI Agent 实现 → **[MeowAgent](https://github.com/Axonant/MeowAgent)** — 真实器官、SQLite 生产级存储、Discord/Telegram 适配器，一行 `Cat(CatBase)` 继承即可运行。

---

## 📊 版本历史（关键里程碑）

| 版本       | 亮点                                                                                                                                               |
| :--------- | :------------------------------------------------------------------------------------------------------------------------------------------------- |
| **v1.2.x** | CatSelf 统一自我模型、熔断器、遥测（Tracer+Metrics）、事件载荷类型、Colony 配置化、中间件重构                                                      |
| **v1.1.x** | Crystallizer L1-L3 技能晶化、PinealGland 顿悟融合、ScribblePad 草稿纸、Cortex L0-L3 世界观、ActiveGrowth 主动生长、Colony 联邦、Pluggable 器官插件 |
| **v1.0.x** | Colony 多猫容器、SharedStorage 共享存储、群聊、跨猫信号、Gateway 适配器（HTTP/WS/CLI/IPC/Webhook）                                                 |
| **v0.5.x** | CatBase 外观模式、双脑架构、OrganHost/Wiring/Nervous 子系统拆分、ReflexArc 反射弧、Slot-Plug 模型、ImplementationStyle、20 器官蓝图                |

---

## 📦 安装

```bash
# 核心框架（零 I/O）
pip install meowcat

# 含可选电池包（浏览器、ChromaDB、MCP、网关适配器）
pip install meowcat[plus]

# 开发环境
pip install -e ".[plus,dev]"
pytest tests/
```

**环境要求**：Python 3.10+、`pydantic>=2.0`、`anyio>=4.0`

---

## 📂 包结构速查

| 模块                  | 用途                                                         |
| :-------------------- | :----------------------------------------------------------- |
| `meowcat/anatomy.py`  | 器官坐标、类别、ImplementationStyle                          |
| `meowcat/biology/`    | OrganSpec SSOT、CatSelf、Cortex、PinealGland、Fusion、Growth |
| `meowcat/assembly.py` | CatBase — 将 5 个子系统组合为一只活的猫                      |
| `meowcat/host.py`     | OrganHost — 挂载/卸载/查找器官，Protocol 校验                |
| `meowcat/wiring.py`   | Wiring — 有向神经图（允许 + 禁止）                           |
| `meowcat/nervous.py`  | Nervous — 信号调度 + 中间件 + 熔断器                         |
| `meowcat/reflex.py`   | ReflexArc — 刺激→响应，零 LLM 路径                           |
| `meowcat/tools/`      | Tool/Skill/Paws 核心（零 I/O 抽象）                          |
| `meowcat/plus/`       | 可选 I/O：浏览器、ChromaDB、MCP、网关、晶化器                |
| `meowcat/colony/`     | Colony 多猫容器 + 联邦                                       |
| `meowcat/defaults/`   | Noop 空桩、Renovated 简装实现、预设、工厂                    |

---

## 📄 许可证

[MIT](LICENSE) © 2025-2026 Axonant — 以好奇心和猫的本能构建。
