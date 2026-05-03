# meowcat

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-Axonant%2FMeowAgent-181717?style=flat-square&logo=github)](https://github.com/Axonant/MeowAgent)

**An agent framework built on the biological blueprint of a cat.**

meowcat is the framework layer of the MeowAgent ecosystem — pure cat anatomy:
protocols, wiring, reflexes, tools, and the four-layer abstraction from
atomic signals to composable loops. Bring your own LLM; the cat provides
everything else.

> **📋 [完整目录 CATALOG.md](CATALOG.md)** — 20器官、26链路、6链路串、5闭环、2反射弧、1闭环编排、8关键词预设、7提示词预设，逐一列出。

---

## 生物学解剖图 Biological Anatomy

```
                    ┌─────────────────────────────────────────────────────────────────┐
                    │                         BRAIN 脑                                │
                    │                                                                 │
  人类输入 ──────► EARS ──► ╔══════════╗                                              │
  (打字/语音)      (ears)   ║ THALAMUS ║──► CEREBRUM (cerebrum) ──► CEREBELLUM ──┬──► MOUTH ──► 文本输出
                    │        ║  丘脑    ║    深度推理 A脑             小脑 B脑    │    (mouth)
              ──────► EYES   ║  ★分叉★  ║    │              │         │           ├──► PURR  ──► 流式输出
              (eyes)        ╚══╤══╤═══╝    │              │         │           │    (purr)   (SSE/token)
                              │  │          │              │         │           ├──► TAIL  ──► 状态栏
              ──────► WHISKERS│  │          ▼              ▼         ▼           │    (tail)   (health)
              (whiskers)      │  │     HIPPOCAMPUS    HYPOTHALAMUS  PAWS        │
                              │  │     海马体 记忆      下丘脑 稳态    爪子 工具   │
                              │  │        │               │            │         │
                              │  │        │   ◄───────────┘            │         │
                              │  │        │   (decay/cleanup)          │         │
                              │  │        │                            │         │
                              │  ├────────┤                            │         │
                              │  │  AMYGDALA ────── fear bypass ──────┤         │
                              │  │   杏仁核 安全                        │         │
                              │  │                                      │         │
                              │  └──► BRAINSTEM ── master dispatch ────┘         │
                              │         脑干 调度                                     │
                              │            │                                         │
                              │            ▼                                         │
                              │       FRONTAL 额叶                                   │
                              │           focus/planning                             │
                              │            │                                         │
                              │            ▼                                         │
                              │         CORTEX 皮层                                  │
                              │          worldview                                   │
                              │                                                      │
                              │    ┌──────────────────────────────────────┐         │
                              │    │  GROWTH 生长器官 (Loop C 进化回路)     │         │
                              │    │  ANOMALY ──► CORRECTION              │         │
                              │    │   异常沉淀      校正固化              │         │
                              │    │       │              │               │         │
                              │    │  CRYSTALLIZER   ROLE_EMERGENCE       │         │
                              │    │   技能结晶        角色涌现            │         │
                              │    └──────────────────────────────────────┘         │
                              └─────────────────────────────────────────────────────┘

        图例:  ──► 单向链路     ★分叉★ 路由分发点     ◄──► 双向/回路
```

**人类的生物类推**：打字(感官输入) → 丘脑(分叉路由) → 大脑皮层(深度思考) → 小脑(运动协调) → 手部(输出回应)。两个闭环：
- **闭环 A (感知-推理-输出)**：EARS → THALAMUS → HIPPOCAMPUS → CEREBRUM → CEREBELLUM → MOUTH
- **闭环 B (稳态维护)**：HYPOTHALAMUS → HIPPOCAMPUS (记忆衰减) → self-loop

---

## 四层抽象 Four-Layer Architecture

```
  Organ ──► Path ──► Chain ──► Loop ──► LoopSequence
  单器官    一条信号   命名Path     Chain +    多个Loop
  单元      配方        序列        触发/退出    编排
```

| 层 | 模块 | 概念 | 数量 |
|----|------|------|------|
| **Organ** | `anatomy.py` | 20 个默认器官 (THALAMUS, HIPPOCAMPUS, CEREBRUM...) | **20** |
| **Path** | `path.py`    | 26 条内置原子链路 ("locate", "deep_reason"...) | **26** |
| **Chain** | `chain.py`   | 6 条内置链路串 (MEMORY_SEARCH_CHAIN, WORKFLOW_CHAIN...) | **6** |
| **Loop** | `loops.py`   | 5 个默认闭环 (CONVERSATION_LOOP, TOOL_EXECUTION_LOOP...) | **5** |
| **LoopSeq** | `loops.py` | 1 个闭环编排 (DAILY_MAINTENANCE_SEQ) | **1** |
| **Reflex** | `reflex.py`  | 2 个内置反射路径 (text_dialogue, danger) | **2** |

**总计**：20 器官 + 26 链路 + 6 链路串 + 5 闭环 + 1 编排 = **一键可用**

---

## 一键可用 Quick Start

```bash
pip install meowcat
```

### 简装修默认 (开箱即用)

```python
from meowcat.defaults import create_cat, KW_BILINGUAL, PROMPT_ZH

class MyBrain:
    name = "cerebrum"
    async def generate(self, prompt, system_prompt=None, **kw) -> str:
        return f"喵! 你说: {prompt[:50]}"

# 一键创建：20个器官全部简装修，双语关键词，中文提示词
cat = create_cat("小喵", cerebrum=MyBrain(),
                 keyword=KW_BILINGUAL, prompt=PROMPT_ZH)

# 直接用 — 链路
result = await cat.path_registry.run("locate", query="天气")

# 直接用 — 链路串
result = await cat.chain_registry.run("full_reasoning", prompt="天为什么是蓝的?")

# 直接用 — 闭环 (触发 → 执行 → 退出)
result = await cat.run_loop("conversation", message="你好!")
```

### 行业预设 (5 个行业)

```python
from meowcat.defaults import create_cat, KW_TECH, PROMPT_TECH   # 技术
from meowcat.defaults import KW_MEDICAL, PROMPT_MEDICAL          # 医疗
from meowcat.defaults import KW_FINANCE, PROMPT_FINANCE          # 金融
from meowcat.defaults import KW_LEGAL, PROMPT_LEGAL              # 法律
from meowcat.defaults import KW_EDUCATION, PROMPT_EDUCATION      # 教育

cat = create_cat("代码猫", cerebrum=my_llm,
                 keyword=KW_TECH, prompt=PROMPT_TECH)
# deploy→action, docker→action, 调试→chat, 自动安全检测
```

### 自定义预设 (你的项目/行业)

```python
from meowcat.defaults import create_cat, KeywordPreset, PromptPreset

cat = create_cat("my-bot", cerebrum=my_llm,
    keyword=KeywordPreset(
        name="物流行业",
        stop_words=frozenset({"嗯", "啊", "的", "了"}),
        command_patterns={"发货": "action", "查单": "memory", "退换": "chat"},
        danger_patterns=[],  # 你的安全规则
        priority_keywords=["发货", "物流", "快递"],
    ),
    prompt=PromptPreset(
        name="物流",
        templates={"chat": "你是物流助手。领域: {domain}。语言: {language}。"},
        pre_prompt="你是专业的物流行业AI。",
        post_prompt="不要承诺具体的配送时间。",
    ),
)

# 查看插头风格
from meowcat import ImplementationStyle
print(cat.organ("brain", "amygdala").impl_style)  # ImplementationStyle.ALGORITHM
```

---

## 器官=插槽, 实现=插头

每个器官是**插槽(slot)** — 定义了入口出口 Protocol + 引脚(in/out edges) + 支持的插头类型。
开发者选择**插头(plug)** 填充器官 — 可在 algorithm/rule/model/hybrid 中任选，支持多插头按序匹配(fallback)。

| 插头风格 | 含义 | 例子 |
|----------|------|------|
| `ALGORITHM` | 纯代码 | 正则、字典、字符串、subprocess |
| `RULE` | 声明式规则 | 黑白名单、阈值触发 |
| `MODEL` | ML 模型 | LLM、分类器、嵌入 |
| `HYBRID` | 混合 | 规则优先 → 模型兜底 |

20 个器官中 **仅 CEREBRUM 强制 MODEL**，其他 19 个至少支持 ALGORITHM。

> 📋 完整器官+链路+闭环逐一列出 → **[CATALOG.md](CATALOG.md)**

---

## 完整链路清单

### 26 条 Path (原子链路)

| # | 链路名 | 信号 | 方向 |
|---|--------|------|------|
| 1 | `locate` | THALAMUS → THALAMUS (自环) | 记忆检索 |
| 2 | `hear` | EARS → THALAMUS | 输入接收 |
| 3 | `decide_route` | THALAMUS → THALAMUS (自环) | **路由分叉** |
| 4 | `assess_safety` | AMYGDALA → AMYGDALA (自环) | 安全检查 |
| 5 | `deep_reason` | THALAMUS → CEREBRUM | 深度推理 |
| 6 | `speak` | CEREBELLUM → MOUTH | 文本输出 |
| 7 | `execute_tool` | CEREBELLUM → PAWS | 工具执行 |
| 8 | `synthesize` | BRAINSTEM → CORTEX | 世界观合成 |
| 9-13 | `remember`, `get_entity`, `get_all`, `fts_search`, `get_related` | BRAINSTEM/THALAMUS → HIPPOCAMPUS | 记忆存储/检索 |
| 14-16 | `add_entity`, `add_episode`, `connect` | BRAINSTEM → HIPPOCAMPUS | 记忆写入 |
| 17-19 | `decay`, `weaken_connections`, `cleanup_orphans` | HYPOTHALAMUS → HIPPOCAMPUS | 记忆维护 |
| 20-23 | `record_access`, `set_dormant`, `append_content`, `set_last_seen` | BRAINSTEM → HIPPOCAMPUS | 记忆操作 |
| 24 | `update_importance` | BRAINSTEM → HIPPOCAMPUS | 重要性更新 |
| 25-26 | `workflow_create`, `workflow_resume` | BRAINSTEM → HIPPOCAMPUS | 工作流 |

### 6 条 Chain (链路串)

| 链路串 | 链路序列 | 用途 |
|--------|----------|------|
| `memory_search` | `locate` | 记忆检索 |
| `full_reasoning` | `deep_reason` → `speak` | 推理→输出 |
| `tool_exec` | `execute_tool` | 工具执行 |
| `maintenance` | `decay` → `cleanup_orphans` | 记忆维护 |
| `diagnostic` | (空 — Stethoscope 体检) | 诊断检查 |
| `workflow_chain` | `workflow_create` → `execute_tool` → `workflow_checkpoint` | 长工作流 |

### 5 条 Loop (闭环)

| 闭环 | 链路串 | 触发事件 | 描述 |
|------|--------|----------|------|
| `conversation` | hear→decide_route→locate→deep_reason→speak→remember | `perceive.start` | **闭环 A: 感知-推理-输出** |
| `tool_execution` | hear→decide_route→execute_tool→speak→remember | `orchestrate.start` | 工具执行闭环 |
| `danger_response` | assess_safety | `amygdala.alert` | 安全应急闭环 |
| `maintenance` | decay→cleanup_orphans | `heartbeat.tick` | **闭环 B: 稳态维护** |
| `diagnostic` | (空) | None (手动触发) | 健康检查 |

### 2 条 Reflex (反射弧)

| 反射 | 路径 (器官序列) | 触发条件 |
|------|-----------------|----------|
| `text_dialogue` | EARS → THALAMUS → BRAINSTEM → CEREBRUM → CEREBELLUM → MOUTH | 文本消息 |
| `danger` | EARS → THALAMUS → AMYGDALA → MOUTH (绕过大脑) | 检测到危险 |

### 1 条 LoopSequence (闭环编排)

`DAILY_MAINTENANCE_SEQ`：maintenance → diagnostic (维护→体检，顺序执行)

---

## 器官清单 (20个)

### 大脑 Brain (9)
| 器官 | 坐标 | 角色 | 简装修 |
|------|------|------|--------|
| **THALAMUS** | `(brain, thalamus)` | **★路由分叉点★** — 所有输入先经过 | 关键词路由 `/命令` 检测 |
| **HIPPOCAMPUS** | `(brain, hippocampus)` | 海马体记忆 — 存储、查找、忘记 | 内存图谱 + 关键词索引 |
| **CEREBRUM** | `(brain, cerebrum)` | A脑 — 深度推理 (需要配LLM) | callable 适配器 |
| **CEREBELLUM** | `(brain, cerebellum)` | B脑 — 快速响应，所有输出前最后站 | callable 适配器 |
| **AMYGDALA** | `(brain, amygdala)` | 杏仁核 — 安全检查、威胁检测 | 中英文正则安全扫描 |
| **FRONTAL** | `(brain, frontal)` | 额叶 — 注意力/话题检测 | 关键词话题跟踪 |
| **HYPOTHALAMUS** | `(brain, hypothalamus)` | 下丘脑 — 稳态维护、记忆衰减 | TTL可配置衰减 |
| **CORTEX** | `(brain, cortex)` | 皮层 — 世界观沉淀 | 4层世界观内存 |
| **BRAINSTEM** | `(brain, brainstem)` | 脑干 — 总调度 hub | 系统 prompt 构建 |

### 感知 Senses (4)
| 器官 | 坐标 | 简装修 |
|------|------|--------|
| **EARS** | `(sense, ears)` | 文本标准化 + 关键词提取 + zh/en检测 |
| **EYES** | `(sense, eyes)` | 图片格式检测 (PNG/JPEG/GIF/BMP/WebP) |
| **WHISKERS** | `(sense, whiskers)` | 输入/输出感知 + 漂移检测 |
| **PAWS** | `(sense, paws)` | 工具注册表集成 + 安全前置 |

### 输出 Voice (3)
| 器官 | 坐标 | 简装修 |
|------|------|--------|
| **MOUTH** | `(voice, mouth)` | stdout 打印 + 日志 |
| **PURR** | `(voice, purr)` | 流式状态跟踪 |
| **TAIL** | `(voice, tail)` | 状态栏渲染 |

### 生长 Growth (4) — 闭环 C 进化回路
| 器官 | 坐标 | 简装修 |
|------|------|--------|
| **ANOMALY_GROWTH** | `(growth, anomaly_growth)` | 异常日志 |
| **CORRECTION_GROWTH** | `(growth, correction_growth)` | 校正日志 |
| **CRYSTALLIZER** | `(growth, crystallizer)` | 技能命中计数 |
| **ROLE_EMERGENCE** | `(growth, role_emergence)` | 行为模式日志 |

---

## 关键词与提示词预设 (二语 行业 可挂载)

### 内置预设

| 预设 | 类型 | 说明 |
|------|------|------|
| `KW_EN` / `KW_ZH` / `KW_BILINGUAL` | 关键词 | 英文/中文/中英双语 |
| `KW_TECH` / `KW_FINANCE` / `KW_MEDICAL` | 关键词 | 技术/金融/医疗行业 |
| `KW_LEGAL` / `KW_EDUCATION` | 关键词 | 法律/教育行业 |
| `PROMPT_DEFAULT` / `PROMPT_ZH` | 提示词 | 默认/中文 |
| `PROMPT_TECH` / `PROMPT_FINANCE` / `PROMPT_MEDICAL` | 提示词 | 技术/金融/医疗 |
| `PROMPT_LEGAL` / `PROMPT_EDUCATION` | 提示词 | 法律/教育 |

### 双轨模式

| 模式 | 说明 | 使用 |
|------|------|------|
| **简装修** (默认) | 20个器官全部预装可用默认 | `create_cat(..., renovated=True)` |
| **毛坯** | 纯 Noop 空壳，自己装修 | `create_cat(..., renovated=False)` |
| **混合** | 部分简装，部分毛坯 | `create_cat(..., bare_organs={"amygdala"})` |

---

## 架构建议 Architecture Suggestions

当前已实现：
- ✅ 20器官 26链路 6链路串 5闭环 1闭环编排
- ✅ 双语关键词预设 (中/英) + 5行业预设
- ✅ 毛坯/简装双轨 + 每器官可独立选择
- ✅ 丘脑分叉路由 (Thalamus fan-out)

建议后续扩展：
1. **显式 Router 层** — 在 Path 和 Chain 之间增加 Branch/Router 概念，让 THALAMUS 的 `decide_route` 从隐式变为显式的分叉决策点，支持 `{match: route}` 规则引擎
2. **更多 LoopSequence** — 如 `STARTUP_SEQ`(health→maintenance)、`CONVERSATION_WITH_SAFETY`(conversation+danger 并行)
3. **Reflex 扩展** — 目前只有 text_dialogue 和 danger，可增加 `visual`(视觉)、`action_order`(工具指令) 反射
4. **简装修器官的反射适配** — 如 `safety_first` 反射: EARS→THALAMUS→AMYGDALA→(安全)CEREBRUM 或 (危险)MOUTH

---

## 示例

```bash
python -m meowcat.examples.01_organ_host_only   # OrganHost as typed container
python -m meowcat.examples.02_wiring_validation  # Wiring safety validation
python -m meowcat.examples.03_event_bus_only     # EventBus standalone
python -m meowcat.examples.04_custom_cat         # Build a cat from 5 subsystems
python -m meowcat.examples.05_minimal_chat_cat   # Minimal chat cat in <80 lines
python -m meowcat.examples.06_custom_organ       # Write + mount a custom organ
python -m meowcat.examples.07_custom_organ       # Custom organ + Path/Chain/Loop
```

---

## 版本历史

| Version | Date    | Highlights                                                   |
| ------- | ------- | ------------------------------------------------------------ |
| v1.1.0 | 2026-05 | **破而后立**: renovated organs (简装修/毛坯), bilingual presets (8+7), ImplementationStyle slot/plug, CATALOG.md, 移除 pathways.py + GrowthProtocol |
| v1.0.18 | 2026-05 | Renovated organs: 20 organs with minimal useful defaults + bilingual presets |
| v1.0.17 | 2026-05 | Pipeline Stage base class + 6 Noop* Stage stubs               |
| v1.0.16 | 2026-05 | 6 missing Noop* organ stubs (Cerebrum, Cerebellum, 4x Growth) |
| v1.0.15 | 2026-05 | Long-running workflows with checkpoint/resume                |
| v1.0.14 | 2026-05 | Lifecycle hooks (on_start / on_shutdown)                     |
| v1.0.13 | 2026-05 | Signal middleware pipeline                                   |
| v1.0.12 | 2026-05 | Colony federation transports (TCP/Redis)                     |
| v1.0.11 | 2026-05 | Synthesize path + Loop sequence registry                     |
| v1.0.10 | 2026-05 | Gateway abstraction (CLI / HTTP / WebSocket / Webhook / IPC) |
| v1.0.9  | 2026-05 | CLI facade methods (search_memory, memory_stats, etc.)       |
| v1.0.8  | 2026-05 | Growth organs named (Anomaly/Correction/Crystallizer/Role)   |
| v1.0.7  | 2026-05 | Pluggable component system                                   |
| v1.0.6  | 2026-05 | In-memory stores (GraphStore, VectorStore, SharedStore)      |
| v1.0.5  | 2026-05 | Pipeline + Building blocks                                   |
| v1.0.4  | 2026-05 | Loop sequences (meta-loops)                                  |
| v1.0.3  | 2026-05 | Chain rollback + wiring visualization                        |
| v1.0.2  | 2026-05 | Colony multi-cat management                                  |
| v1.0.1  | 2026-05 | Cat isolation (parent_id, allowed_organs, forbidden_methods) |
| v1.0.0  | 2026-05 | Initial framework release                                    |

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

_Built with the biological blueprint of a cat. The framework layer of [MeowAgent](https://github.com/Axonant/MeowAgent)._
