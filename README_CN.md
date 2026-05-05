# meowcat

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-Axonant%2FMeowAgent-181717?style=flat-square&logo=github)](https://github.com/Axonant/MeowAgent)

> 🐱 **纯个人开发** — 如果觉得有用，给个 ⭐ star ⭐ 支持一下吧！

**以猫的生物蓝图构建的 Agent 框架。**

meowcat 是 MeowAgent 生态的纯框架层 — 猫解剖学：协议、神经布线、反射、工具，以及从原子信号到可组合闭环的四层抽象。自带 LLM 即可，猫提供其余一切。

> 20 个器官、26 条链路、6 条链路串、5 个闭环、器官出入口规则全目录 → **[CATALOG.md](CATALOG.md)**

---

## 全景流程图

**Gateway（猫的皮肤）** — 唯一外部 I/O 出入口，所有协议适配器共插同一个 Gateway。

```
┌────────────────── Gateway — 猫的皮肤 ──────────────────────┐
│                                                              │
│   外部世界                                                   │
│   HTTP · WebSocket · Webhook · CLI · IPC                    │
│          │                                                   │
│          ▼                                                   │
│   ┌──────────────────────────────┐                          │
│   │  Gateway._on_message()       │  ← 1猫 : 1Gateway       │
│   │  Gateway._on_stream()        │    : N适配器             │
│   └──────────────┬───────────────┘                          │
│                  │                                           │
│                  ▼                                           │
│          cat.perceive()  →  进入猫的神经系统                 │
│                                                              │
│   Gateway 不是器官，是独立子系统，组合 CatBase 而非继承。      │
│   适配器实现见 meowcat.plus.gateway (HTTP/WS/Webhook/CLI/IPC) │
└──────────────────────────────────────────────────────────────┘
```

```
                        ┌──────────────────────────────────────────────────────────────┐
                        │                      猫的神经系统                             │
                        │                                                              │
   人类输入 ──────────► EARS ──► ╔══════════╗                                         │
   (文本/语音)          (耳朵)    ║ THALAMUS ║──► CEREBRUM (大脑) ──► CEREBELLUM ─┬──► MOUTH ──► 文本
                        │        ║  ★分叉★  ║    深度推理            快速响应     │   (嘴巴)
                  ──────► EYES   ╚══╤══╤═══╝    (LLM调用)         (效应器路由)   ├──► PURR  ──► 流式
                  (眼睛)           │  │              │                     │        │   (呼噜)
                                   │  │              ▼                     ▼        ├──► TAIL  ──► 状态
                  ──────► WHISKERS │  │         HIPPOCAMPUS              PAWS      │   (尾巴)
                  (胡须)           │  │         (记忆图谱)             (工具执行)   │
                                   │  │              │                                 │
                                   │  ├──────────────┤                                 │
                                   │  │  AMYGDALA ←──┼── 恐惧旁路 ───────────────────┤
                                   │  │  (杏仁核)     │                                 │
                                   │  │               │                                 │
                                   │  └──► BRAINSTEM ─┴── 总调度 ─────────────────────┤
                                   │       (脑干)                                      │
                                   │          │                                        │
                                   │          ▼                                        │
                                   │       FRONTAL ──► CORTEX                          │
                                   │       (额叶)      (皮层世界观 L0-L3)              │
                                   │                                                   │
                                   │    ┌─── 感悟融合管线 ────────────────────────┐   │
                                   │    │  ScribblePad ──► PinealGland ──► 冥想   │   │
                                   │    │  (写字台)         (松果体)        │     │   │
                                   │    │                                  ▼     │   │
                                   │    │           fuse_to_self ──► Cortex      │   │
                                   │    │           fuse_to_colony ──► 共享存储  │   │
                                   │    └─────────────────────────────────────────┘   │
                                   │                                                   │
                                   │    ┌─── 主动生长 ───────────────────────────┐   │
                                   │    │  盲区检测器 / 工具失败学习器            │   │
                                   │    │  热路径观察器 / 集体生长                │   │
                                   │    └─────────────────────────────────────────┘   │
                                   │                                                   │
                                   └─── CatSelf (统一自我) ──────────────────────────┘
                                        动作前 → 动作 → 动作后 → 记录碎片

   图例:  ──► 单向    ★ 分叉 ★ 路由    ◄──► 双向
```

**猫舍（Colony）** — 多只猫对等协作，通过 SharedStorage 共享记忆与状态。

```
┌─────────── Colony (猫舍) ──────────────────────────────┐
│                                                          │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐             │
│  │  猫 A   │    │  猫 B   │    │  猫 C   │             │
│  │ (对等)  │◄──►│ (对等)  │◄──►│ (对等)  │             │
│  │ cat_uid= │    │ cat_uid= │    │ cat_uid= │             │
│  │  "a"   │    │  "b"   │    │  "c"   │             │
│  └────┬────┘    └────┬────┘    └────┬────┘             │
│       │              │              │                   │
│       └──────────────┼──────────────┘                   │
│                      │                                  │
│               ┌──────▼──────┐                           │
│               │ SharedStorage│ ← 共享记忆/状态          │
│               └─────────────┘                           │
│                                                          │
│   每只猫内部 = 完整的神经系统 (上图)。猫间通过             │
│   signal_between() 通信 + SharedStorage 读写协作。        │
└──────────────────────────────────────────────────────────┘
```

**四层抽象** — Path → Chain → Loop → LoopSequence — 将原子信号组合为自治闭环。

**两大闭环** — 内环（单猫自我进化，经 CatSelf）+ 外环（集体智慧融合，经 Colony）。PinealGland 是枢纽。

> 详细器官规格、出入口规则、链路表、闭环定义 → **[CATALOG.md](CATALOG.md)**

---

## 亮点

| 类别             | 能力                                                                |
| ---------------- | ------------------------------------------------------------------- |
| **猫神经蓝图**   | 20 个器官，真实神经解剖映射（丘脑、海马体、杏仁核...）              |
| **插槽/插头**    | 器官 = 类型化插槽 (Protocol)。实现 = 插头 (4种风格)。自由替换。     |
| **四层抽象**     | Path (原子) → Chain (序列) → Loop (触发+退出) → LoopSequence (编排) |
| **两大闭环**     | 内环：自我进化。外环：集体智慧。PinealGland 为枢纽。                |
| **感悟管线**     | ScribblePad → PinealGland → 冥想 → fuse_to_self / fuse_to_colony    |
| **Cortex L0-L3** | 事实 → 规则 → 信念 → 元认知。全部可插拔。                           |
| **CatSelf**      | 统一自我模型：动作前/动作后 + 3 种预制默认闭环                      |
| **主动生长**     | 盲区检测器 + 工具失败学习器 + 热路径观察器 — 猫会自己学习           |
| **Pluggable**    | 每个器官支持运行时挂载/卸载 hook。3 种执行模式。支持异步插件。      |
| **Colony**       | 多猫对等协作：共享记忆、跨猫信号、联邦 + WorkerScheduler            |
| **信号安全**     | 按 (器官, 方法) 粒度熔断 — 连续失败自动断路                         |
| **可观测性**     | 内置 Tracer + Metrics — 零外部依赖的信号调用追踪                    |
| **闭环桥接**     | CatSelf DefaultLoop ↔ LoopRegistry 桥接 — 两种闭环体系可组合        |
| **零硬编码**     | 所有阈值、危险列表、语言预设均为构造器参数                          |
| **懒加载**       | `import meowcat` 只加载骨架。首次访问属性时才导入完整模块。         |
| **零 I/O 核心**  | 框架层无文件/网络 I/O。所有具体 I/O 在 `plus/` 中。                 |
| **双轨模式**     | Noop (毛坯空壳) 或 Renovated (简装修) — 可按器官混合。              |
| **双语预设**     | KW_EN / KW_ZH / KW_BILINGUAL 关键词 + PROMPT_DEFAULT / PROMPT_ZH    |

---

## 快速开始

```bash
pip install meowcat
```

### 简装修（20 个器官开箱即用）

```python
from meowcat.defaults import create_cat, KW_BILINGUAL, PROMPT_ZH

class MyBrain:
    name = "cerebrum"
    async def generate(self, prompt, system_prompt=None, **kw) -> str:
        return f"喵！你说：{prompt[:50]}"

cat = create_cat("小喵", cerebrum=MyBrain(),
                 keyword=KW_BILINGUAL, prompt=PROMPT_ZH)

# Path — 原子信号
result = await cat.path_registry.run("locate", query="天气")

# Chain — 命名序列
result = await cat.chain_registry.run("full_reasoning", prompt="天为什么是蓝的？")

# Loop — 闭环（带触发/退出）
result = await cat.run_loop("conversation", message="你好！")

# LoopSequence — 多闭环编排
result = await cat.run_loopseq("daily_maintenance")
```

### 毛坯（空壳，自己装配）

```python
cat = create_cat("小喵", cerebrum=MyBrain(), renovated=False)
# 所有 20 个器官为安全空存根。挂载你自己的实现。
```

### 自定义预设（你的领域/语言）

```python
from meowcat.defaults import create_cat, KeywordPreset, PromptPreset

cat = create_cat("my-bot", cerebrum=my_llm,
    keyword=KeywordPreset(
        name="物流行业",
        stop_words=frozenset({"嗯", "啊", "的", "了"}),
        command_patterns={"发货": "action", "查单": "memory"},
        danger_patterns=[],
        priority_keywords=["发货", "物流", "快递"],
    ),
    prompt=PromptPreset(
        name="物流",
        templates={"chat": "你是物流助手。领域: {domain}。语言: {language}。"},
        pre_prompt="你是专业的物流行业 AI。",
        post_prompt="不要承诺具体的配送时间。",
    ),
)
```

---

## 器官 = 插槽，实现 = 插头

每个器官是一个**插槽（slot）** — 类型化的契约（Protocol），定义了入口/出口边。
你选择一个**插头（plug）** 来填充它 — 算法、规则、模型或混合。

| 插头风格    | 含义       | 示例                       |
| ----------- | ---------- | -------------------------- |
| `ALGORITHM` | 纯代码     | 正则、字典查找、subprocess |
| `RULE`      | 声明式规则 | 白名单/黑名单、阈值触发    |
| `MODEL`     | ML 模型    | LLM、分类器、嵌入          |
| `HYBRID`    | 混合       | 规则优先 → 模型兜底        |

仅 **CEREBRUM 强制 MODEL**。其余 19 个器官至少支持 ALGORITHM。

```python
from meowcat import ImplementationStyle
print(cat.organ("brain", "amygdala").impl_style)  # ImplementationStyle.ALGORITHM
```

---

## 四层架构

```
  Organ ──► Path ──► Chain ──► Loop ──► LoopSequence
  单器官    原子信号   命名Path    Path+      多Loop
  单元      配方       序列        触发/退出   编排
```

| 层          | 模块         | 概念                                     | 数量   |
| ----------- | ------------ | ---------------------------------------- | ------ |
| **Organ**   | `anatomy.py` | 20 个默认器官 (THALAMUS, CEREBRUM...)    | **20** |
| **Path**    | `path.py`    | 26 条内置原子链路 ("locate", "speak"...) | **26** |
| **Chain**   | `chain.py`   | 6 条内置链路串 (MEMORY_SEARCH_CHAIN...)  | **6**  |
| **Loop**    | `loops.py`   | 5 个内置闭环 (CONVERSATION_LOOP...)      | **5**  |
| **LoopSeq** | `loops.py`   | 1 个闭环编排 (DAILY_MAINTENANCE_SEQ)     | **1**  |
| **Reflex**  | `reflex.py`  | 2 个内置反射弧 (text_dialogue, danger)   | **2**  |

> 完整 Path/Chain/Loop 表 → **[CATALOG.md](CATALOG.md)**

---

## 记忆架构 — 多维立体

猫的记忆不是单一平面存储，而是一套 **4×5×4×2** 体系，横跨认知深度、功能器官、物理后端和作用域四个维度。

```
┌─── 认知四层 (Cortex L0→L3) ───────────────────────────────────────────────┐
│                                                                              │
│   L0 原始事实         L1 推断规则          L2 信念           L3 元认知       │
│  ┌───────────┐    ┌──────────────────┐   ┌──────────────┐   ┌────────────┐  │
│  │Hippocampus│───→│  extract_rules   │──→│promote_belief│──→│Metacogni.  │  │
│  │ entities  │    │ "X 总是 Y"       │   │"永远用参数化" │   │"我擅长X"   │  │
│  │ episodes  │    │ conf 0.95        │   │conf 0.8 □    │   │"我不会Y"   │  │
│  └───────────┘    └──────────────────┘   └──────────────┘   └────────────┘  │
│                                                                              │
│   事实经 extract_rules 蒸馏 → 提升为信念 → 形成自我认知                       │
└──────────────────────────────────────────────────────────────────────────────┘

┌─── 功能器官 (5 个记忆角色) ────────────────────────────────────────────────┐
│                                                                              │
│  Hippocampus   Hypothalamus    ScribblePad    PinealGland       Cortex      │
│  存储·检索       衰减·清理      碎片缓冲(200)   感悟枢纽          世界观      │
│      ↑              ↑                ↑              ↑               ↑       │
│  BRAINSTEM写入   BRAINSTEM      CatSelf        trigger_if()     只读终端     │
│      │           触发         after_act    满/定时/事件触发                   │
│      └───────────────────────────┴───────────────────────────────┘           │
│                                    │                                          │
│                           感悟融合管线                                        │
│                    fuse_to_self ↕ fuse_to_colony                             │
└──────────────────────────────────────────────────────────────────────────────┘

┌─── 存储后端 ────────────┐  ┌─── 作用域 ──────────────────────────────────┐
│                         │  │                                               │
│  InMemoryStore  KV 内存 │  │  单猫私有 ──── PinealGland ──── 猫群共享     │
│  VectorStore    关键词/ │  │  Hippocampus       │          SharedStorage  │
│                 语义    │  │  ScribblePad        │          Collective*    │
│  SqliteGraphStore 图DB  │  │  Cortex             │                          │
│  JsonlL6Store   JSONL   │  │       fuse_to_self ─┴── fuse_to_colony       │
│                         │  │                                               │
└─────────────────────────┘  └───────────────────────────────────────────────┘

图例:  ──→ 数据流向    ↑ 写入入口    ↕ 双向    □ 可被挑战
```

**两大闭环**在此交汇：**内环**（Hippocampus → Cortex → CatSelf → ScribblePad → PinealGland → 回到 Cortex）完成自我进化，**外环**（PinealGland → SharedStorage → 其他猫）实现集体智慧。

---

## 器官分组

### 大脑 Brain (9)

| 器官             | 插槽 `(brain, ...)` | 角色                      |
| ---------------- | ------------------- | ------------------------- |
| **THALAMUS**     | `thalamus`          | 路由分叉 — 所有输入先经过 |
| **HIPPOCAMPUS**  | `hippocampus`       | 记忆 — 存储、查找、忘记   |
| **CEREBRUM**     | `cerebrum`          | 深度推理 (LLM)            |
| **CEREBELLUM**   | `cerebellum`        | 快速响应，效应器唯一上游  |
| **AMYGDALA**     | `amygdala`          | 安全检查、威胁检测        |
| **FRONTAL**      | `frontal`           | 焦点/规划/话题跟踪        |
| **HYPOTHALAMUS** | `hypothalamus`      | 稳态 — 记忆衰减、清理     |
| **CORTEX**       | `cortex`            | 世界观 L0-L3、信念体系    |
| **BRAINSTEM**    | `brainstem`         | 总调度中枢、系统提示词    |

### 感知 Senses (4)

| 器官         | 插槽 `(sense, ...)` | 角色                 |
| ------------ | ------------------- | -------------------- |
| **EARS**     | `ears`              | 文本/语音输入        |
| **EYES**     | `eyes`              | 图像/视频输入        |
| **WHISKERS** | `whiskers`          | 环境感知、漂移检测   |
| **PAWS**     | `paws`              | 工具执行（唯一入口） |

### 输出 Voice (3)

| 器官      | 插槽 `(voice, ...)` | 角色       |
| --------- | ------------------- | ---------- |
| **MOUTH** | `mouth`             | 文本输出   |
| **PURR**  | `purr`              | 流式状态   |
| **TAIL**  | `tail`              | 状态栏渲染 |

### 生长 Growth (4)

| 器官                  | 插槽 `(growth, ...)` | 角色     |
| --------------------- | -------------------- | -------- |
| **ANOMALY_GROWTH**    | `anomaly_growth`     | 异常沉淀 |
| **CORRECTION_GROWTH** | `correction_growth`  | 校正固化 |
| **CRYSTALLIZER**      | `crystallizer`       | 技能结晶 |
| **ROLE_EMERGENCE**    | `role_emergence`     | 角色涌现 |

> 完整器官出入口规则 → **[CATALOG.md](CATALOG.md)**

---

## 架构 — 已实现

- 20 器官、26 链路、6 链路串、5 闭环、2 反射弧、1 闭环编排
- 两大闭环：内环 (CatSelf 自我进化) + 外环 (Colony 集体智慧)
- ScribblePad → PinealGland 感悟融合管线 + Cortex 四层世界观 L0-L3
- 主动生长：盲区检测器 + 工具失败学习器 + 热路径观察器
- CatSelf 统一自我模型 + 3 种预制默认闭环 (conversation / task / learn)
- Pluggable 器官插件系统 (支持异步，3 种执行模式)
- Colony 多猫对等协作 + GlobalColonyRegistry + WorkerScheduler
- 双语关键词预设 (中/英/双语) + 毛坯/简装双轨
- Gateway I/O 抽象层 (HTTP/WS/Webhook/CLI/IPC 适配器在 `plus/gateway/`)
- 信号中间件 (日志、限流、超时、上下文注入) + 熔断器
- 内置可观测性：Tracer + Metrics + SignalSpan (零外部依赖)
- CatSelf DefaultLoop ↔ LoopRegistry 桥接 (两种闭环体系可组合)
- 懒加载 (`import meowcat` 仅加载骨架)
- 零硬编码 — 所有阈值/模式均为构造器参数
- `plus/` 可选电池包 (文件IO、浏览器、MCP客户端、ChromaDB、技能加载器、网关)

## 未来方向

1. PinealGland 融合事件广播 — fuse_to_self/fuse_to_colony 发射 GrowthEvent
2. ScribblePad 持久化预制件 — DefaultScribblePersister 自动写入 JsonlL6Store
3. `execute_tool` Path 迁移到统一的 `execute()` PawsProtocol 入口

---

## 版本历史

```
v1.2.24~v1.2.33 (2026-05-05) — 全面打磨: 34 项路线图全部解决 (11 个 Bug/安全修复, 9 个代码质量, 3 个架构优化)。魔法数字提取到 constants.py, 异常吞没审计, 延迟 import 耦合文档化
v1.2.15~v1.2.23 (2026-05-04) — 架构打磨: 热路径性能、Pluggable 异步化、事件类型安全、熔断器、闭环桥接、可观测性、WorkerScheduler、适配器、gateway→plus
v1.2.6~v1.2.13 (2026-05-04) — Plus 重构: 修复 4 个 bug、创建 plus/、删除行业预设、Renovated 全员配置化、Colony 拆分 + 懒加载
v1.2.0        (2026-05-04) — CatSelf 统一自我 + ScribblePad→PinealGland 管线 + Cortex L0-L3 + 元认知 + 主动生长
v1.1.1~v1.1.29 (2026-05-03~04) — 写字台、松果体、皮层世界观、主动生长三件套、集体生长+涌现、全局注册中心
v1.1.0        (2026-05-03) — 简装/毛坯双轨、ImplementationStyle 4 种插头风格、双语预设、20 器官预装、CATALOG.md
v1.0.1~v1.0.18 (2026-05-01~03) — 20 器官+26 链路+6 链路串+5 闭环、Pluggable 系统、Colony 多猫、Gateway I/O、中间件、生命周期钩子、工作流
v1.0.0        (2026-05-01) — 初始发布: 猫神经框架核心、四层抽象 Path→Chain→Loop→LoopSeq、pip install meowcat
```

---

## 示例

```bash
python -m meowcat.examples.01_organ_host_only   # OrganHost 类型化容器
python -m meowcat.examples.02_wiring_validation  # 布线安全验证
python -m meowcat.examples.03_event_bus_only     # EventBus 独立使用
python -m meowcat.examples.04_custom_cat         # 从 5 个子系统构建猫
python -m meowcat.examples.05_minimal_chat_cat   # <80 行最小聊天猫
python -m meowcat.examples.06_custom_organ       # 编写并挂载自定义器官
python -m meowcat.examples.07_custom_organ       # 自定义器官 + Path/Chain/Loop
```

---

## 许可证

本项目基于 **MIT 许可证**。详见 [LICENSE](LICENSE)。

---

_以猫的生物蓝图构建。MeowAgent 生态的框架层 — [MeowAgent](https://github.com/Axonant/MeowAgent)。_
