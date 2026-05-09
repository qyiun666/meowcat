# 🐱 meowcat · 仿生神经 AI Agent 框架

[![English](https://img.shields.io/badge/文档-English-blue.svg)](README.md)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![version](https://img.shields.io/badge/version-1.3.10-lightgrey.svg)](https://pypi.org/project/MeowCat/)
[![pypi](https://img.shields.io/badge/pypi-meowcat-orange.svg)](https://pypi.org/project/meowcat/)
[![GitHub](https://img.shields.io/badge/GitHub-Axonant%2FMeowAgent-181717?style=flat-square&logo=github)](https://github.com/Axonant/MeowAgent)

> 🐱 **纯个人开发** — 如果觉得有用，给个 ⭐ star ⭐ 支持一下吧！

以猫的生物蓝图构建的 AI Agent 框架。定义器官、接通神经，猫便活了过来。

> 📖 **[AGENTS.md](AGENTS.md)** — 应用开发者入口（3 分钟建立心智模型）
>
> **框架定义骨架。你来选择材质。**
>
> 20 个器官 · 31 条路径 · 8 条链条 · 7 个循环 · 完整默认配置速查 → **[CATALOG.md](CATALOG.md)**

---

## 💭 Agent 应该是什么样子？

未来的 AI Agent 应该是什么样的？

它不应该只是一条接 prompt、吐回复的管线。它应该像一个生物——有感知、有记忆、有安全意识、能自我进化、能与同类协作。

人处理一件事时，大脑不同区域各司其职：**丘脑**路由信息，**海马体**存取记忆，**杏仁核**在危险时绕过理性直接接管决策，**皮层**从经验中蒸馏世界观。如果 Agent 要真正融入人类社会——或者某一天，建造自己的社会——它需要的远不止推理能力。

它需要**本能**（反射弧，不经思考的快速响应）、**恐惧**（安全旁路，危险时跳过推理直接行动）、**直觉**（小脑模式匹配，高频场景零 LLM 开销）、**自知**（元认知，知道自己会什么、不会什么）。它需要知道什么能做、什么不能做，需要从错误中学习，需要在群体中自然形成分工。

这些思考最终凝结成了 meowcat——不是又一个 LLM 包装器，而是一套仿生神经架构。

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

## 🧬 不只是 Harness

大多数 Agent 框架的思路是：**你有 LLM → 给它接工具 → 编排成 workflow → 多 agent 协作**。框架负责"套上缰绳"（harness）——路由消息、管理状态、串起工具调用。

meowcat 的思路是：**生物有器官 → 器官有分工和约束 → 神经信号在约束内流动 → 整体涌现行为**。框架定义的是解剖结构和神经规则，不是 workflow。

|                  | Harness 模式                     | meowcat                                       |
| :--------------- | :------------------------------- | :-------------------------------------------- |
| **隐喻**         | 工坊 / 流水线                    | 生物体 / 神经系统                             |
| **Agent 是什么** | 功能性单元（planner / executor） | 完整生命体（20 器官 + 自我 + 生长）           |
| **通信**         | 消息路由 / topic / queue         | 神经信号（Path → Chain → Loop 四层）          |
| **约束**         | prompt guard / output validator  | 架构级禁止边（大脑不能直连爪子）              |
| **安全**         | 事后校验 / guardrail             | 杏仁核旁路（危险时跳过推理直接行动）          |
| **记忆**         | vector store + chat history      | 海马体实体图谱 + 皮层 L0→L3 世界观蒸馏        |
| **生长**         | fine-tune / prompt 优化          | 内环（自我进化）+ 外环（集体智慧）            |
| **多 agent**     | group chat / router→worker       | Colony 猫舍（共享存储 + 集体生长 + 角色涌现） |

Harness 解决的是**"怎么让 LLM 干活"**，meowcat 回答的是**"Agent 应该长什么样"**。你完全可以用 meowcat 实现 Harness 模式——但反过来不行。meowcat 是 Harness 的上一级抽象。

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
                             ┌──────────────────────────────┐
  外部世界 ─────────────────► │  Gateway (皮肤)               │  HTTP / WebSocket / CLI / IPC / Webhook
                             │  ┌────────────────────────┐   │
                             │  │  FrontDesk (前台)       │   │  on_route 插件: 安全门、审计、限流
                             │  └────────┬───────────────┘   │
                             └───────────┼───────────────────┘
                                         │
                           1 猫舍 : 1 皮肤 : N 适配器
                                         │
  ┌──────────────────────────────────────▼──────────────────────────────────────┐
  │                        Colony (猫舍 · 多猫容器)                              │
  │                                                                              │
  │   ┌─────────────────────────────────────┐   ┌────────────────────────────┐  │
  │   │  猫舍大看板 (Shared Board)           │   │  联邦 (Federation)          │  │
  │   │  owner/ rules/ knowledge/ cats/       │   │  P2P 请求-响应              │  │
  │   │  growth/ [自定义...]                  │   │  30s 超时                   │  │
  │   └─────────────────────────────────────┘   └────────────────────────────┘  │
  │                                                                              │
  │   ┌─ cat.perceive() ────────────────────────────────────────────────────┐   │
  │   │                                                                       │   │
  │   │   ┌──────────┐    ┌──────────┐    ┌──────────────────────────────┐   │   │
  │   │   │ 感官     │───►│ THALAMUS │───►│          脑区                │   │   │
  │   │   │ Ears     │    │ (中继)   │    │ Cerebrum Cerebellum Amygdala  │   │   │
  │   │   │ Eyes     │    └──────────┘    │ Frontal Hippocampus Cortex    │   │   │
  │   │   │ Whiskers │                    │ Hypothalamus Brainstem        │   │   │
  │   │   └──────────┘                    └──────────────┬───────────────┘   │   │
  │   │                                                  │                    │   │
  │   │                              ┌───────────────────▼───────────────┐   │   │
  │   │                              │           效应器                  │   │   │
  │   │                              │  Mouth (说话)  Purr (流式)       │   │   │
  │   │                              │  Tail (状态)   Paws (工具)        │   │   │
  │   │                              └───────────────────────────────────┘   │   │
  │   │                                                                       │   │
  │   │   ┌──────────────────────────────────────────────────────────────┐   │   │
  │   │   │  生长: PinealGland · AnomalyGrowth · CorrectionGrowth       │   │   │
  │   │   │        Crystallizer · RoleEmergence                          │   │   │
  │   │   └──────────────────────────────────────────────────────────────┘   │   │
  │   └───────────────────────────────────────────────────────────────────────┘   │
  └──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

> 💡 **你需要先准备一个大模型。** meowcat 不内置 LLM — 你提供一个 `generate(prompt) → str` 的实现即可接入任意模型。

```bash
pip install meowcat
```

```python
from meowcat.defaults import create_cat
from meowcat.colony import Colony

colony = Colony()  # colony_uid 自动生成（含版权水印）

# ✅ 方式一：接入真实 LLM（以 DeepSeek 为例）
# DeepSeek 兼容 OpenAI API，只需设置 base_url
from openai import AsyncOpenAI

class DeepSeekCerebrum:
    """DeepSeek 大脑 — 模型固定为 deepseek-chat。"""
    name = "cerebrum"

    def __init__(self, *, api_key=None):
        self.client = AsyncOpenAI(
            api_key=api_key or "your-deepseek-api-key",
            base_url="https://api.deepseek.com",
        )
        self.model = "deepseek-chat"

    async def generate(self, prompt, system_prompt=None, **kw) -> str:
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": prompt})
        r = await self.client.chat.completions.create(
            model=self.model, messages=msgs
        )
        return r.choices[0].message.content

    async def stream_generate(self, prompt, system_prompt=None,
                              temperature=0.7, max_tokens=None):
        result = await self.generate(prompt, system_prompt=system_prompt)

        async def _stream():
            yield result
        return _stream()

    def reload_config(self) -> None:
        pass

# 完整装配：20 器官 + 接线 + 反射弧
cat = create_cat(container=colony, cerebrum=DeepSeekCerebrum(), name="小喵")

# ✅ 方式二：最小 mock（无需 API key，用于测试布线）
# class EchoCerebrum:
#     name = "cerebrum"
#     async def generate(self, prompt, system_prompt=None, **kw) -> str:
#         return f"喵！{prompt[:100]}"
#     async def stream_generate(self, prompt, system_prompt=None,
#                               temperature=0.7, max_tokens=None):
#         result = await self.generate(prompt, system_prompt=system_prompt)
#
#         async def _stream():
#             yield result
#         return _stream()
#     def reload_config(self) -> None:
#         pass
# cat = create_cat(container=colony, cerebrum=EchoCerebrum(), name="小喵")

# 直接调用器官 — 最简单的工作方式
async def main():
    # Chain: 深度推理（大脑直接生成回复）
    result = await cat.path_registry.run(cat, "deep_reason", prompt="天为什么是蓝的？")
    print(result)

    # Path: 记忆检索
    result = await cat.path_registry.run(cat, "locate", msg="东京天气", session_id="default")

    # perceive(): 统一感知入口（需自定义 Stage 实现才能输出）
    async for event in cat.perceive("今天天气怎么样？"):
        pass

import asyncio
asyncio.run(main())
```

---

## 🔬 插槽-插头模型

框架只定义**插槽（Slot）** — 器官长什么样、能连接谁、能读写什么、支持什么实现。你来提供**插头（Plug）** — 实际实现。

```python
from meowcat.defaults import create_cat
from meowcat.colony import Colony
from meowcat.anatomy import ImplementationStyle

colony = Colony()

# cerebrum（Mock，用于演示）
class MockBrain:
    name = "cerebrum"
    async def generate(self, prompt, system_prompt=None, **kw) -> str:
        return f"[思考: {prompt[:50]}]"

    async def stream_generate(self, prompt, system_prompt=None,
                              temperature=0.7, max_tokens=None):
        result = await self.generate(prompt, system_prompt=system_prompt)

        async def _stream():
            yield result
        return _stream()

    def reload_config(self) -> None:
        pass

# 你提供插头 — 必须满足 AmygdalaProtocol
class MyAmygdala:
    name = "amygdala"
    impl_style = ImplementationStyle.RULE
    async def assess_safety(self, input, **kw):
        return {"safe": True, "risk_level": 0}

cat = create_cat(container=colony, cerebrum=MockBrain(),
                 amygdala=MyAmygdala(), name="小喵")
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
| **L1 Path**         | `源器官 → 目标器官.方法`             | 原子器官间信号。31 条内置路径。                |
| **L2 Chain**        | `[path1, path2, ...] + rollback`     | 命名路径序列。前步结果传给后步。8 条内置链条。 |
| **L3 Loop**         | `Chain + trigger_event + exit_event` | 自治闭环。7 条内置循环。                       |
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
from meowcat.defaults import create_cat
from meowcat.colony import Colony

colony = Colony("my-squad")

# 定义 cerebrum（参照快速开始）
class TaskBrain:
    name = "cerebrum"
    async def generate(self, prompt, system_prompt=None, **kw) -> str:
        return f"[处理: {prompt[:50]}]"

    async def stream_generate(self, prompt, system_prompt=None,
                              temperature=0.7, max_tokens=None):
        result = await self.generate(prompt, system_prompt=system_prompt)

        async def _stream():
            yield result
        return _stream()

    def reload_config(self) -> None:
        pass

# 孵化多只猫到猫舍中
analyst  = create_cat(container=colony, cerebrum=TaskBrain(), name="analyst")
executor = create_cat(container=colony, cerebrum=TaskBrain(), name="executor")

# 1:1 跨猫通信（用 cat_uid）
data = "DELETE FROM orders"
await colony.signal_between(analyst.cat_uid, executor.cat_uid,
    "brain", "amygdala", "assess_safety", user_input=data)

# 1:N 广播
await colony.broadcast("alert", level="high")

# 共享存储（命名空间 ns_set / ns_get）
await colony.ns_set("knowledge", "weather", {"city": "北京"})
result = await colony.ns_get("knowledge", "weather")

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

基于 meowcat 框架的完整 AI Agent 实现 → **[MeowAgent](https://github.com/Axonant/MeowAgent)** ([官网](https://qyiun666.github.io/meowagent.github.io/)) — 真实器官、SQLite 生产级存储、Discord/Telegram 适配器，一行 `Cat(CatBase)` 继承即可运行。

---

## 📬 联系我们

- **官网：** https://qyiun666.github.io/meowagent.github.io/
- **邮箱：** qyiun666@163.com
- **GitHub：** https://github.com/Axonant/MeowAgent — 基于 meowcat 的应用层 Agent 实现（待公开）

有什么功能建议、想法，或寻求合作？欢迎联系 — PR、功能需求、合作洽谈都欢迎。

---

## 📊 版本历史（关键里程碑）

| 版本        | 时间       | 亮点                                                                                                                                                                                                                                    |
| :---------- | :--------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **v1.3.10** | 2026.05.09 | CI lint 修复 + Release 重构为 workflow_dispatch 手动发包 · pypi/github-release 独立 job                                                                                                                                                 |
| **v1.3.9**  | 2026.05.09 | 代码健康整理 — 12 文件拆至 ≤500 行 · deprecated 清理 · 版本文档补全                                                                                                                                                                     |
| **v1.3.8**  | 2026.05.08 | mypy + ruff 静态检查 · CI lint job + 矩阵 3.10-3.13 · pre-commit · 10 蓝修复 · 大文件拆分                                                                                                                                               |
| **v1.3.7**  | 2026.05.08 | Gateway 绑定 Colony · FrontDesk 新物种 — on_route 插件链（安全门/审计/限流）                                                                                                                                                            |
| **v1.3.6**  | 2026.05.07 | OrganPrompt 提示插槽 · Hippocampus episodes 持久化 · LLM 模型货架 12 供应商 · 管理器基类 5 件套 · PeriodicScheduler/FocusStore/CheckpointStore · PlanReviser 策略链 · TaskOrchestrator DAG · Async 生命周期钩子 · Telemetry/CB 公开 API |
| **v1.3.x**  | 2026.05.06 | 任务委托 delegate_async / await_task、colony UID 自动生成 + CALL_SIGN 版权水印、Growth 新增 4 条 Path + 2 条 Chain + 2 条 Loop                                                                                                          |
| **v1.2.x**  | 2026.05.05 | CatSelf 统一自我模型、熔断器、遥测（Tracer+Metrics）、事件载荷类型、Colony 配置化、中间件重构                                                                                                                                           |
| **v1.1.x**  | 2026.05.03 | Crystallizer L1-L3 技能晶化、PinealGland 顿悟融合、ScribblePad 草稿纸、Cortex L0-L3 世界观、ActiveGrowth 主动生长、Colony 联邦、Pluggable 器官插件                                                                                      |
| **v1.0.x**  | 2026.05.02 | Colony 多猫容器、SharedStorage 共享存储、群聊、跨猫信号、Gateway 适配器（HTTP/WS/CLI/IPC/Webhook）                                                                                                                                      |
| **v0.5.x**  | 2026.05.01 | 从 MeowAgent 抽离为独立框架 · CatBase 外观模式 · 双脑架构 · OrganHost/Wiring/Nervous 子系统拆分 · ReflexArc 反射弧 · Slot-Plug 模型 · ImplementationStyle · 20 器官蓝图                                                                 |

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
| `meowcat/gateway/`    | Gateway — 猫舍皮肤，FrontDesk + 协议适配器                   |
| `meowcat/defaults/`   | Noop 空桩、Renovated 简装实现、预设、工厂                    |

---

## 📄 许可证

[MIT](LICENSE) © 2025-2026 Axonant — 以好奇心和猫的本能构建。
