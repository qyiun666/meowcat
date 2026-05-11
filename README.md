# 🐱 meowcat · Bio-Neural AI Agent Framework

[![中文文档](https://img.shields.io/badge/文档-中文-red.svg)](README_CN.md)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![version](https://img.shields.io/badge/version-2.4.0-lightgrey.svg)](https://pypi.org/project/MeowCat/)
[![pypi](https://img.shields.io/badge/pypi-meowcat-orange.svg)](https://pypi.org/project/meowcat/)

> 🐱 **Pure personal project** — if this helps you, a ⭐ star ⭐ would mean a lot!

An AI agent framework built on a cat's biological blueprint. Define your organs, wire their nerves, and the cat comes alive.

> 📖 **[AGENTS.md](AGENTS.md)** — app developer entry (mental model in 3 min)
>
> **Framework defines the skeleton. You choose the materials.**
>
> 20 organs · 23 paths · 8 chains · 7 loops · full default config reference → **[CATALOG.md](CATALOG.md)**
>
> ⚠️ **v2.0 breaking changes** — read **[MIGRATION_v2_EN.md](MIGRATION_v2_EN.md)** (English) · **[MIGRATION_v2.md](MIGRATION_v2.md)** (中文) before upgrading from v1.x.

---

## 💭 What Should an Agent Be?

What should an AI agent of the future look like?

It shouldn't be just a prompt-in, reply-out pipeline. It should feel alive — with perception, memory, safety instincts, the capacity to evolve, and the ability to collaborate with its own kind.

When a human processes a situation, different brain regions handle different jobs: the **thalamus** routes information, the **hippocampus** stores and retrieves memories, the **amygdala** bypasses reason to seize control under threat, the **cortex** distills a worldview from experience. If agents are to truly integrate into human society — or one day build their own — they need far more than reasoning.

They need **instinct** (reflex arcs — acting without thinking), **fear** (safety bypass — skipping reason when danger strikes), **intuition** (cerebellar pattern matching — zero LLM overhead for common cases), **self-awareness** (metacognition — knowing what they can and cannot do). They need to understand boundaries, learn from mistakes, and naturally form roles within a collective.

These questions led to meowcat — not another LLM wrapper, but a bio-neural architecture.

---

## 📐 What is meowcat?

meowcat is to AI agents what a skeleton is to a body — it defines the structure, the connections, the rules of signal flow.

```
          Protocols    Anatomy    Wiring    Nervous    Reflex
         organ contract blueprint nerve paths dispatch  stimulus→response
              │          │         │         │         │
              └──────────┴────┬────┴─────────┴─────────┘
                              │
                    CatBase (skeleton + lifecycle)
                              │
              ┌───────────────┼───────────────┐
              │               │               │
          OrganHost        Colony         defaults/
         mount/validate  multi-cat    Default organs
```

- **Zero I/O core** — framework has no file/network I/O, pure abstractions
- **Slot-Plug separation** — framework defines Slots (Protocols), you provide Plugs (implementations)

---

## ✨ Why "Cat"?

meowcat models an AI agent after a **cat's biological nervous system** — a proven architecture refined by millions of years of evolution:

| Biological Reality                      | meowcat Equivalent                                     |
| :-------------------------------------- | :----------------------------------------------------- |
| Thalamus routes all sensory input       | `Thalamus` — single sensory relay hub                  |
| Cerebrum handles deep reasoning         | `Cerebrum` — LLM-powered deep thinking                 |
| Cerebellum coordinates fast action      | `Cerebellum` — sole gateway to effectors               |
| Amygdala triggers fear responses        | `Amygdala` — safety bypass (can act without reasoning) |
| Hippocampus stores memories             | `Hippocampus` — entity graph + knowledge tree          |
| Hypothalamus maintains homeostasis      | `Hypothalamus` — memory decay + cleanup                |
| Cortex builds worldview from experience | `Cortex` — L0→L3 cognition pipeline                    |
| Reflex arcs bypass the brain            | `ReflexArc` — stimulus→response with zero LLM          |

**20 organs. 5 categories. 1 unified nervous system.** The cat architecture gives you biological defense layers (amygdala safety bypass, circuit breakers, forbidden edges) that a flat LLM pipeline can never have.

---

## 🧬 Beyond the Harness

Most agent frameworks follow this pattern: **take an LLM → attach tools → orchestrate into workflows → multi-agent collaboration**. The framework "puts on the harness" — routing messages, managing state, chaining tool calls.

meowcat follows a different path: **a living organism has organs → organs have roles and constraints → neural signals flow within constraints → behavior emerges**. The framework defines anatomy and neural rules, not workflows.

|                       | Harness Pattern                      | meowcat                                                                |
| :-------------------- | :----------------------------------- | :--------------------------------------------------------------------- |
| **Metaphor**          | Workshop / assembly line             | Living organism / nervous system                                       |
| **What is an agent?** | Functional unit (planner / executor) | Complete lifeform (20 organs + self + growth)                          |
| **Communication**     | Message routing / topic / queue      | Neural signals (Path → Chain → Loop, 4 layers)                         |
| **Constraints**       | Prompt guard / output validator      | Architecture-level forbidden edges (brain can't control paws directly) |
| **Safety**            | Post-hoc guardrail / validator       | Amygdala bypass (skip reasoning, act on danger instantly)              |
| **Memory**            | Vector store + chat history          | Hippocampus entity graph + knowledge tree + Cortex worldview           |
| **Growth**            | Fine-tuning / prompt optimization    | Inner loop (self-evolution) + Outer loop (collective intelligence)     |
| **Multi-agent**       | Group chat / router→worker           | Colony (shared storage + cross-cat signals)                            |

Harness-style frameworks answer **"how to make LLMs work"**. meowcat answers **"what should an agent be"**. You can absolutely implement harness patterns on top of meowcat — but not the other way around. meowcat is one level of abstraction above.

---

## 🎯 Highlights

<table>
<tr>
<td width="50%">

### 🧬 Bio-Neural Blueprint

Modeled after real neuroanatomy. 20 organs in 5 categories (BRAIN / SENSE / VOICE / STORAGE / GROWTH). Each organ has entry/exit rules, read/write permissions, and supported implementation styles — just like real biological constraints.

### 🔌 Slot-Plug Architecture

Framework defines the **Slot** (Protocol interface + OrganSpec contract). You provide the **Plug** (concrete implementation). 2 plug styles: `ALGORITHM` | `MODEL`. Mix and match per organ.

### 🧠 Four-Layer Execution Model

`Path` (atomic signal) → `Chain` (sequence + rollback) → `Loop` (trigger + exit + event) → `LoopSequence` (orchestration). From microscopic to macroscopic, layered composability.

</td>
<td width="50%">

### 🛡️ Biological Defense Layers

- **Amygdala safety bypass** — danger detected → output directly, zero LLM reasoning
- **Circuit breaker** — per (organ, method) independent breaker, consecutive failures → open circuit
- **Forbidden edges** — biologically plausible wiring restrictions (brain can't control paws directly)
- **Kittens** — fine-grained permission views (allowlisted organs + forbidden methods)

### 🔄 Double Closed Loop

- **Inner loop (CatSelf)**: freeze snapshot → act → reflect → fuse insights → evolve worldview
- **Outer loop (Colony)**: shared storage → cross-cat signals → collective growth → role emergence

### 🌳 KnowledgeTree (v2.0)

`TreeNode` dataclass + Hippocampus tree methods: build_tree, get_tree, search_tree, query_subtree, delete_tree, check_stale.

### 📋 Unified Rule Engine (v2.1)

`RuleSet` + `Rule` — attach a rule set to each cat; all LLM call sites auto-inject structured rules per route. Framework provides container, no built-in rules.

### 📝 Task Delegation (v2.2)

Multi-round brain-tool loop `do_task()`: cerebrum interleaves reasoning and tool calls until completion. `spawn_worker()` creates independent worker cats. `TaskPad` per-cat todo list.

</td>
</tr>
</table>

---

## 🏗️ Architecture at a Glance

```
Gateway → Colony → Cat
                      ├── perceive() / do_task()   ← Work Loop
                      └── ReflectionLoop           ← Growth Loop
```

meowcat presents a **two-layer model**:

- **Work Loop** — `perceive()` / `do_task()` — the cat's conscious activity. Hear → Route → Reason → Speak. Tools via brain↔paws multi-round loop.
- **Growth Loop** — `ReflectionLoop` — self-improvement. Scribbles → distill → fuse into CatSelf and Colony.

For the full 20-organ blueprint, see [AGENTS.md](AGENTS.md) and [CATALOG.md](CATALOG.md).

---

## 🚀 Quick Start

> 💡 **You need to bring your own LLM.** meowcat doesn't ship with one — provide any `generate(prompt) → str` implementation to plug in your model.

```bash
pip install meowcat
```

```python
from meowcat.defaults import create_cat
from meowcat.colony import Colony

colony = Colony()  # colony_uid auto-generated (with copyright watermark)

# Define your LLM brain
from openai import AsyncOpenAI

class DeepSeekCerebrum:
    name = "cerebrum"

    def __init__(self, *, api_key=None):
        self.client = AsyncOpenAI(
            api_key=api_key or "your-deepseek-api-key",
            base_url="https://api.deepseek.com",
        )
        self.model = "deepseek-v4-pro"

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

# One line to create a fully assembled cat
cat = create_cat(container=colony, cerebrum=DeepSeekCerebrum(), name="Kitty")

# Minimal mock for testing — no API key needed
# class EchoCerebrum:
#     name = "cerebrum"
#     async def generate(self, prompt, system_prompt=None, **kw) -> str:
#         return f"Meow! {prompt[:100]}"
#     async def stream_generate(self, prompt, system_prompt=None, **kw):
#         result = await self.generate(prompt)
#         async def _stream(): yield result
#         return _stream()
#     def reload_config(self): pass

# v2.0: CatSelf is application-layer managed
from meowcat.biology.cat_self import CatSelf
cat.cat_self = CatSelf()

async def main():
    # Path: deep reasoning (advanced API)
    result = await cat.path_registry.run(cat, "deep_reason", prompt="Why is the sky blue?")
    print(result)

    # perceive(): unified entry (yields StageEvent objects)
    async for ev in cat.perceive("What's the weather today?"):
        pass

    # KnowledgeTree (v2.0)
    from meowcat.tree import TreeNode
    root = TreeNode(id="r", entity_id="e1", parent_id=None,
                    path="/", node_type="project", name="p")
    cat.hippocampus.build_tree("e1", root)

    # Unified rule engine (v2.1)
    from meowcat.ruleset import RuleSet, Rule
    cat.rule_set = RuleSet(
        role_block="<role>Python security auditor</role>",
        always_on=[Rule("Safety first", "No dangerous operations", "critical")],
        per_route={"deep_reason": [Rule("SQL", "Use parameterized queries", "critical")]},
    )

    # Task delegation (v2.2)
    from meowcat.tools.tool_call import XmlToolCallParser
    result = await cat.do_task("Write a login function", max_rounds=5)
    print(result.final_text, result.rounds, result.tool_calls)

    # Spawn worker cat (v2.2)
    worker = cat.spawn_worker("helper", "Query user table schema")
    worker.task_pad.list_todo()

import asyncio
asyncio.run(main())
```

---

## 🧭 Data Flow: From Input to Output

```
User Input
    │
    ▼
┌──────────┐     ┌──────────┐     ┌─────────────────────────┐
│  EARS    │────►│ THALAMUS │────►│      BRAIN REGIONS      │
│ (sense)  │     │ (relay)  │     │  ┌───────────────────┐  │
└──────────┘     └──────────┘     │  │ CEREBRUM (deep)   │  │
                                  │  │    ↓              │  │
                                  │  │ CEREBELLUM (fast) │  │
                                  │  │    ↓              │  │
                                  │  │ EFFECTORS         │  │
                                  │  │ Mouth/Purr/Tail   │  │
                                  │  │ Paws (tools)      │  │
                                  │  └───────────────────┘  │
                                  └─────────────────────────┘
    │                                                     │
    │         ┌───────────────────────────┐               │
    └────────►│ AMYGDALA (safety bypass)  │───────────────┘
              │ Danger → output directly  │
              └───────────────────────────┘
```

**Two pathways exist for every input:**

1. **Reasoning path**: EARS → THALAMUS → CEREBRUM → CEREBELLUM → MOUTH (full reasoning)
2. **Emergency path**: EARS → THALAMUS → AMYGDALA → MOUTH (bypasses brain, instant safety response)

---

## 📦 Organ Catalog

### 9 Brain Regions

| Organ            | Role                | Key Trait                            |
| :--------------- | :------------------ | :----------------------------------- |
| **Thalamus**     | Sensory relay hub   | All input routes through here        |
| **Cerebrum**     | Deep reasoning      | LLM-powered, MODEL only              |
| **Cerebellum**   | Fast response       | Sole gateway to ALL effectors        |
| **Hippocampus**  | Memory + trees      | Entity graph + KnowledgeTree (v2.0)  |
| **Amygdala**     | Safety bypass       | Can trigger output without reasoning |
| **Frontal**      | Focus & planning    | Topic tracking, task decomposition   |
| **Hypothalamus** | Homeostasis         | Memory decay, orphan cleanup         |
| **Cortex**       | Worldview distiller | L0→L3 cognition pipeline             |
| **Brainstem**    | Master dispatch     | Coordinates ALL brain regions        |

### 4 Senses + 3 Voice + 5 Growth

| Category   | Organs                                                                                     |
| :--------- | :----------------------------------------------------------------------------------------- |
| **SENSE**  | Ears (text), Eyes (vision), Whiskers (anomaly), Paws (tools — also effector)               |
| **VOICE**  | Mouth (speak), Purr (streaming status), Tail (status bar)                                  |
| **GROWTH** | PinealGland (insight fusion), AnomalyGrowth, CorrectionGrowth, Crystallizer, RoleEmergence |

---

## 🐱 Colony — Multi-Cat Container

```python
from meowcat.defaults import create_cat
from meowcat.colony import Colony

colony = Colony("my-squad")

# Define a simple cerebrum
class TaskBrain:
    name = "cerebrum"
    async def generate(self, prompt, system_prompt=None, **kw) -> str:
        return f"[thinking: {prompt[:50]}]"
    async def stream_generate(self, prompt, system_prompt=None, **kw):
        result = await self.generate(prompt)
        async def _stream(): yield result
        return _stream()
    def reload_config(self): pass

# Spawn cats into the colony
analyst  = create_cat(container=colony, cerebrum=TaskBrain(), name="analyst")
executor = create_cat(container=colony, cerebrum=TaskBrain(), name="executor")

# 1:1 inter-cat communication (use cat_uid)
data = "DELETE FROM orders"
await colony.signal_between(analyst.cat_uid, executor.cat_uid,
    "brain", "amygdala", "assess_safety", user_input=data)

# Shared storage (namespace ns_set / ns_get)
await colony.ns_set("knowledge", "weather", {"city": "NYC"})
result = await colony.ns_get("knowledge", "weather")
```

| Feature               | Description                                            |
| :-------------------- | :----------------------------------------------------- |
| **Cross-cat signals** | 1:1 (`signal_between`), 1:N (`broadcast_request`)      |
| **Shared storage**    | Namespaced: `owner/` `knowledge/` `cats/`              |
| **Collective growth** | Cats learn from each other's anomalies and corrections |
| **Role emergence**    | Behavior patterns → implicit role specialization       |

---

## 🛠️ Apps Built on meowcat

Full AI Agent implementation built on meowcat → **[MeowAgent](https://github.com/Axonant/MeowAgent)** ([Website](https://qyiun666.github.io/meowagent.github.io/)) — real organs, SQLite production storage, Discord/Telegram adapters. One `Cat(CatBase)` inheritance and it runs.

---

## 📬 Contact

- **Website:** https://qyiun666.github.io/meowagent.github.io/
- **Email:** qyiun666@163.com
- **GitHub:** https://github.com/Axonant/MeowAgent

Have feature ideas or want to collaborate? We'd love to hear from you — pull requests, feature suggestions, and partnership inquiries are all welcome.

---

## 📊 Version History (Key Milestones)

| Version    | Date       | Highlights                                                                                                                                                                                   |
| :--------- | :--------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **v2.4.0** | 2026.05.11 | Architecture simplification — cognitive model compressed from Path/Chain/Loop to perceive() + ReflectionLoop · AGENTS.md 200 lines condensed to 2 sub-sections · bypass Loop quick reference |
| **v2.3.0** | 2026.05.10 | 117 review fixes — import path normalization · dead code removal · EventBus robustness · exception safety · zero logic changes across 131 files                                              |
| **v2.2.0** | 2026.05.10 | TaskPad per-cat todo list · `do_task()` brain-tool multi-round loop · `spawn_worker()` helper cats                                                                                           |
| **v2.1.0** | 2026.05.10 | RuleSet unified rule engine — attach rule set to each cat, auto-inject per route                                                                                                             |
| **v2.0.0** | 2026.05.10 | Framework slimming: 154→113 files, 40→14 concepts · Noop/Renovated merged · Conversation 6→3 steps · KnowledgeTree · Adapters/CLI/tools moved to app layer                                   |
| **v1.3.x** | 2026.05.06 | Task delegation, Gateway+FrontDesk, OrganPrompt, LLM model shelf, manager base classes, async lifecycle hooks                                                                                |
| **v1.2.x** | 2026.05.05 | CatSelf unified self model, Circuit breaker, Telemetry (Tracer+Metrics), Event payload types, Colony config, Middleware refactor                                                             |
| **v1.1.x** | 2026.05.03 | Crystallizer L1-L3, PinealGland epiphany fusion, ScribblePad, Cortex L0-L3 worldview, ActiveGrowth, Colony federation, Pluggable hooks                                                       |
| **v1.0.x** | 2026.05.02 | Colony multi-cat container, SharedStorage, Group chat, Cross-cat signals, Gateway adapters (HTTP/WS/CLI/IPC/Webhook)                                                                         |
| **v0.5.x** | 2026.05.01 | Extracted from MeowAgent as standalone framework · CatBase facade · Dual brain architecture · OrganHost/Wiring/Nervous subsystem split · Slot-Plug model · 20-organ blueprint                |

---

## 📦 Installation

```bash
# Core framework (zero I/O)
pip install meowcat

# Development
pip install -e ".[dev]"
pytest tests/
```

**Requirements**: Python 3.10+, `pydantic>=2.0`, `anyio>=4.0`

> v2.0: `pip install meowcat[plus]` no longer includes built-in tools or gateway adapters (moved to app layer).

---

## 📂 Package Map

| Module                | Purpose                                                               |
| :-------------------- | :-------------------------------------------------------------------- |
| `meowcat/anatomy.py`  | Organ coordinates, categories, ImplementationStyle                    |
| `meowcat/biology/`    | OrganSpec SSOT, CatSelf, Cortex, PinealGland, Fusion, Growth, TaskPad |
| `meowcat/ruleset/` 🆕 | RuleSet unified rule engine (v2.1)                                    |
| `meowcat/assembly.py` | CatBase — compose subsystems into a living cat                        |
| `meowcat/host.py`     | OrganHost — mount/unmount/find organs, protocol validation            |
| `meowcat/wiring.py`   | Wiring — directed nerve graph (allow + forbid)                        |
| `meowcat/nervous.py`  | Nervous — signal dispatch with middleware + circuit breaker           |
| `meowcat/reflex.py`   | ReflexArc — stimulus→response, zero-LLM paths                         |
| `meowcat/tools/`      | Tool/Skill/Paws core + ToolCall/TaskResult dataclass                  |
| `meowcat/tree.py` 🆕  | KnowledgeTree — TreeNode dataclass (v2.0)                             |
| `meowcat/colony/`     | Colony multi-cat container                                            |
| `meowcat/gateway/`    | Gateway + FrontDesk + protocol (adapters moved to app layer in v2.0)  |
| `meowcat/defaults/`   | Default organ implementations, presets, factory                       |

---

## 📄 License

[MIT](LICENSE) © 2025-2026 Axonant — built with curiosity and cat-like instincts.
