# 🐱 meowcat · Bio-Neural AI Agent Framework

[![中文文档](https://img.shields.io/badge/文档-中文-red.svg)](README_CN.md)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![version](https://img.shields.io/badge/version-1.3.2-lightgrey.svg)](https://pypi.org/project/MeowCat/)
[![pypi](https://img.shields.io/badge/pypi-meowcat-orange.svg)](https://pypi.org/project/meowcat/)

> 🐱 **Pure personal project** — if this helps you, a ⭐ star ⭐ would mean a lot!

An AI agent framework built on a cat's biological blueprint. Define your organs, wire their nerves, and the cat comes alive.

> 📖 **[AGENTS_EN.md](AGENTS_EN.md)** — app developer entry (mental model in 3 min)
>
> **Framework defines the skeleton. You choose the materials.**
>
> 20 organs · 31 paths · 8 chains · 7 loops · full default config reference → **[CATALOG.md](CATALOG.md)**

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
         mount/validate  multi-cat     Noop stubs/Renovated
```

- **Zero I/O core** — framework has no file/network I/O, pure abstractions
- **Slot-Plug separation** — framework defines Slots (Protocols), you provide Plugs (implementations)
- **Optional batteries** — `pip install meowcat[plus]` gets you browser, ChromaDB, MCP, gateways

---

## ✨ Why "Cat"?

meowcat models an AI agent after a **cat's biological nervous system** — a proven architecture refined by millions of years of evolution:

| Biological Reality                      | meowcat Equivalent                                     |
| :-------------------------------------- | :----------------------------------------------------- |
| Thalamus routes all sensory input       | `Thalamus` — single sensory relay hub                  |
| Cerebrum handles deep reasoning         | `Cerebrum` — LLM-powered deep thinking                 |
| Cerebellum coordinates fast action      | `Cerebellum` — sole gateway to effectors               |
| Amygdala triggers fear responses        | `Amygdala` — safety bypass (can act without reasoning) |
| Hippocampus stores memories             | `Hippocampus` — entity graph memory                    |
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
| **Memory**            | Vector store + chat history          | Hippocampus entity graph + Cortex L0→L3 worldview distillation         |
| **Growth**            | Fine-tuning / prompt optimization    | Inner loop (self-evolution) + Outer loop (collective intelligence)     |
| **Multi-agent**       | Group chat / router→worker           | Colony (shared storage + collective growth + role emergence)           |

Harness-style frameworks answer **"how to make LLMs work"**. meowcat answers **"what should an agent be"**. You can absolutely implement harness patterns on top of meowcat — but not the other way around. meowcat is one level of abstraction above.

---

## 🎯 Highlights

<table>
<tr>
<td width="50%">

### 🧬 Bio-Neural Blueprint

Modeled after real neuroanatomy. 20 organs in 5 categories (BRAIN / SENSE / VOICE / STORAGE / GROWTH). Each organ has entry/exit rules, read/write permissions, and supported implementation styles — just like real biological constraints.

### 🔌 Slot-Plug Architecture

Framework defines the **Slot** (Protocol interface + OrganSpec contract). You provide the **Plug** (concrete implementation). 4 plug styles: `ALGORITHM` | `RULE` | `MODEL` | `HYBRID`. Mix and match per organ.

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

### 📦 Zero I/O Core + Optional Plus

`pip install meowcat` → pure framework, zero file/network I/O. `pip install meowcat[plus]` → browser, ChromaDB, MCP, gateway adapters, crystallizer — all I/O lives in the optional `plus/` package.

</td>
</tr>
</table>

---

## 🏗️ Architecture at a Glance

```
                             ┌────────────────────┐
  External World ──────────► │  Gateway (Skin)     │  HTTP / WebSocket / CLI / IPC / Webhook
                             └────────┬───────────┘
                                      │
  ┌───────────────────────────────────▼───────────────────────────────────┐
  │                         cat.perceive()                                │
  │                                                                       │
  │   ┌──────────┐    ┌──────────┐    ┌──────────────────────────────┐   │
  │   │ SENSES   │───►│ THALAMUS │───►│         BRAIN REGIONS        │   │
  │   │ Ears     │    │ (Relay)  │    │ Cerebrum Cerebellum Amygdala  │   │
  │   │ Eyes     │    └──────────┘    │ Frontal Hippocampus Cortex    │   │
  │   │ Whiskers │                    │ Hypothalamus Brainstem        │   │
  │   └──────────┘                    └──────────────┬───────────────┘   │
  │                                                  │                    │
  │                              ┌───────────────────▼───────────────┐   │
  │                              │           EFFECTORS               │   │
  │                              │  Mouth (speak)  Purr (stream)     │   │
  │                              │  Tail (status)  Paws (tools)      │   │
  │                              └───────────────────────────────────┘   │
  │                                                                       │
  │   ┌──────────────────────────────────────────────────────────────┐   │
  │   │  GROWTH: PinealGland · AnomalyGrowth · CorrectionGrowth     │   │
  │   │          Crystallizer · RoleEmergence                        │   │
  │   └──────────────────────────────────────────────────────────────┘   │
  └───────────────────────────────────────────────────────────────────────┘
                                      │
                             ┌────────▼───────────┐
                             │  Colony (Multi-Cat) │  SharedStorage · Federation · Cross-Cat Signals
                             └────────────────────┘
```

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

# ✅ Option 1: Real LLM (OpenAI example)
# Framework stores no model names — only provider + API; resolved at bind time
from openai import AsyncOpenAI

class OpenAICerebrum:
    """OpenAI cerebrum — no hardcoded model, fetched from provider on first call."""
    name = "cerebrum"

    def __init__(self, *, api_key=None):
        """api_key not stored in framework — injected via env or config center."""
        self.client = AsyncOpenAI(api_key=api_key)
        self._model = None  # lazy bind, resolved on first call

    async def _resolve_model(self) -> str:
        """Fetch available models from provider, pick latest chat model."""
        models = await self.client.models.list()
        chat = sorted(
            [m.id for m in models.data if m.id.startswith("gpt-")],
            reverse=True,
        )
        return chat[0] if chat else "gpt-4o-mini"

    async def generate(self, prompt, system_prompt=None, **kw) -> str:
        if self._model is None:
            self._model = await self._resolve_model()
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": prompt})
        r = await self.client.chat.completions.create(
            model=self._model, messages=msgs
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

# Fully assembled: 20 organs + wiring + reflex arcs
cat = create_cat(container=colony, cerebrum=OpenAICerebrum(), name="Kitty")

# ✅ Option 2: Minimal mock (no API key, for testing wiring)
# class EchoCerebrum:
#     name = "cerebrum"
#     async def generate(self, prompt, system_prompt=None, **kw) -> str:
#         return f"Meow! {prompt[:100]}"
#     async def stream_generate(self, prompt, system_prompt=None,
#                               temperature=0.7, max_tokens=None):
#         result = await self.generate(prompt, system_prompt=system_prompt)
#
#         async def _stream():
#             yield result
#         return _stream()
#     def reload_config(self) -> None:
#         pass
# cat = create_cat(container=colony, cerebrum=EchoCerebrum(), name="Kitty")

# Direct organ invocation — simplest working path
async def main():
    # Chain: deep reasoning (brain generates reply directly)
    result = await cat.path_registry.run(cat, "deep_reason", prompt="Why is the sky blue?")
    print(result)

    # Path: memory retrieval
    result = await cat.path_registry.run(cat, "locate", msg="weather in Tokyo", session_id="default")

    # perceive(): unified perception entry (needs custom Stage impl to produce output)
    async for event in cat.perceive("What's the weather today?"):
        pass

import asyncio
asyncio.run(main())
```

---

## 🔬 Slot-Plug Model

The framework only defines the **Slot** — what an organ looks like, what it can connect to, what it can read/write, what implementations it supports. You provide the **Plug** — the actual implementation.

```python
from meowcat.defaults import create_cat
from meowcat.colony import Colony
from meowcat.anatomy import ImplementationStyle

colony = Colony()

# cerebrum (mock for demonstration)
class MockBrain:
    name = "cerebrum"
    async def generate(self, prompt, system_prompt=None, **kw) -> str:
        return f"[thinking: {prompt[:50]}]"

    async def stream_generate(self, prompt, system_prompt=None,
                              temperature=0.7, max_tokens=None):
        result = await self.generate(prompt, system_prompt=system_prompt)

        async def _stream():
            yield result
        return _stream()

    def reload_config(self) -> None:
        pass

# You provide the PLUG — must satisfy AmygdalaProtocol
class MyAmygdala:
    name = "amygdala"
    impl_style = ImplementationStyle.RULE
    async def assess_safety(self, input, **kw):
        return {"safe": True, "risk_level": 0}

cat = create_cat(container=colony, cerebrum=MockBrain(),
                 amygdala=MyAmygdala(), name="Kitty")
```

**Plug styles per organ** — framework validates compatibility:

| Style       | Description              | Example Organs                     |
| :---------- | :----------------------- | :--------------------------------- |
| `ALGORITHM` | Deterministic, no LLM    | Ears, Mouth, Purr, Tail, Brainstem |
| `RULE`      | Rule-based decision      | Amygdala, Cortex                   |
| `MODEL`     | LLM-powered              | Cerebrum, Cerebellum               |
| `HYBRID`    | Algorithm + LLM combined | Hippocampus, Frontal               |

---

## 🔗 Four-Layer Execution Model

| Layer               | Primitive                            | Description                                                          |
| :------------------ | :----------------------------------- | :------------------------------------------------------------------- |
| **L1 Path**         | `source → target.method`             | Atomic organ-to-organ signal. 26 built-in paths.                     |
| **L2 Chain**        | `[path1, path2, ...] + rollback`     | Named path sequence. Previous result fed to next. 6 built-in chains. |
| **L3 Loop**         | `Chain + trigger_event + exit_event` | Autonomous closed loop. 5 built-in loops.                            |
| **L4 LoopSequence** | `[loop1, loop2, ...]`                | Sequential or concurrent loop orchestration.                         |

```python
# L1: Path
await cat.path_registry.run("deep_reason", prompt="...")

# L2: Chain with rollback
await cat.chain_registry.run("full_reasoning", prompt="...")
# = deep_reason → speak  (if speak fails, nothing to roll back)

await cat.chain_registry.run("maintenance")
# = decay → cleanup_orphans

# L3: Loop — event-driven autonomous execution
await cat.loop_registry.start("conversation")
# Runs on perceive.start event, exits on conversation.end

# L4: LoopSequence
await cat.loopseq_registry.run("daily_maintenance")
# = maintenance → diagnostic  (sequential)
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
| **Cerebrum**     | Deep reasoning      | LLM-powered, only MODEL/HYBRID       |
| **Cerebellum**   | Fast response       | Sole gateway to ALL effectors        |
| **Hippocampus**  | Memory graph        | Entity-association storage           |
| **Amygdala**     | Safety bypass       | Can trigger output without reasoning |
| **Frontal**      | Focus & planning    | Topic tracking, task decomposition   |
| **Hypothalamus** | Homeostasis         | Memory decay, orphan cleanup         |
| **Cortex**       | Worldview distiller | L0→L3 cognition pipeline             |
| **Brainstem**    | Master dispatch     | Coordinates ALL brain regions        |

### 4 Senses + 3 Voice + 4 Growth

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

# Define cerebrum (see Quick Start above)
class TaskBrain:
    name = "cerebrum"
    async def generate(self, prompt, system_prompt=None, **kw) -> str:
        return f"[thinking: {prompt[:50]}]"

    async def stream_generate(self, prompt, system_prompt=None,
                              temperature=0.7, max_tokens=None):
        result = await self.generate(prompt, system_prompt=system_prompt)

        async def _stream():
            yield result
        return _stream()

    def reload_config(self) -> None:
        pass

# Spawn cats into the colony
analyst  = create_cat(container=colony, cerebrum=TaskBrain(), name="analyst")
executor = create_cat(container=colony, cerebrum=TaskBrain(), name="executor")

# 1:1 inter-cat communication (use cat_uid)
data = "DELETE FROM orders"
await colony.signal_between(analyst.cat_uid, executor.cat_uid,
    "brain", "amygdala", "assess_safety", user_input=data)

# 1:N broadcast
await colony.broadcast("alert", level="high")

# Shared storage (namespace ns_set / ns_get)
await colony.ns_set("knowledge", "weather", {"city": "NYC"})
result = await colony.ns_get("knowledge", "weather")

# Federation — cross-host colony communication
await colony.federate(transport)
await colony.signal_remote("other-colony", "cat-3", ...)
```

| Feature               | Description                                                          |
| :-------------------- | :------------------------------------------------------------------- |
| **Cross-cat signals** | 1:1 (`signal_between`), 1:N (`broadcast_request`), N:N (`broadcast`) |
| **Shared storage**    | Namespaced: `owner/` `rules/` `knowledge/` `growth/` `cats/`         |
| **Federation**        | Cross-host colony P2P communication (request-response, 30s timeout)  |
| **Collective growth** | Cats learn from each other's anomalies and corrections               |
| **Role emergence**    | Behavior patterns → implicit role specialization                     |

---

## 🛠️ Apps Built on meowcat

Full AI Agent implementation built on meowcat → **[MeowAgent](https://github.com/Axonant/MeowAgent)** ([Website](http://www.meowagent.top)) — real organs, SQLite production storage, Discord/Telegram adapters. One `Cat(CatBase)` inheritance and it runs.

---

## 📬 Contact

- **Website:** http://www.meowagent.top (coming soon)
- **Email:** qyiun666@163.com
- **GitHub:** https://github.com/Axonant/MeowAgent — production Agent built on meowcat (coming soon)

Have feature ideas or want to collaborate? We'd love to hear from you — pull requests, feature suggestions, and partnership inquiries are all welcome.

---

## 📊 Version History (Key Milestones)

| Version    | Date       | Highlights                                                                                                                                                                                                       |
| :--------- | :--------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **v1.3.x** | 2026.05.06 | Task delegation delegate_async / await_task, auto-generated colony UID with CALL_SIGN watermark, Growth +4 Paths +2 Chains +2 Loops                                                                              |
| **v1.2.x** | 2026.05.05 | CatSelf unified self model, Circuit breaker, Telemetry (Tracer+Metrics), Event payload types, Colony config, Middleware refactor                                                                                 |
| **v1.1.x** | 2026.05.03 | Crystallizer L1-L3, PinealGland epiphany fusion, ScribblePad, Cortex L0-L3 worldview, ActiveGrowth, Colony federation, Pluggable hooks                                                                           |
| **v1.0.x** | 2026.05.02 | Colony multi-cat container, SharedStorage, Group chat, Cross-cat signals, Gateway adapters (HTTP/WS/CLI/IPC/Webhook)                                                                                             |
| **v0.5.x** | 2026.05.01 | Extracted from MeowAgent as standalone framework · CatBase facade · Dual brain architecture · OrganHost/Wiring/Nervous subsystem split · Reflex arc · Slot-Plug model · ImplementationStyle · 20-organ blueprint |

---

## 📦 Installation

```bash
# Core framework (zero I/O)
pip install meowcat

# With optional batteries (browser, ChromaDB, MCP, gateway adapters)
pip install meowcat[plus]

# Development
pip install -e ".[plus,dev]"
pytest tests/
```

**Requirements**: Python 3.10+, `pydantic>=2.0`, `anyio>=4.0`

---

## 📂 Package Map

| Module                | Purpose                                                      |
| :-------------------- | :----------------------------------------------------------- |
| `meowcat/anatomy.py`  | Organ coordinates, categories, ImplementationStyle           |
| `meowcat/biology/`    | OrganSpec SSOT, CatSelf, Cortex, PinealGland, Fusion, Growth |
| `meowcat/assembly.py` | CatBase — compose 5 subsystems into a living cat             |
| `meowcat/host.py`     | OrganHost — mount/unmount/find organs, protocol validation   |
| `meowcat/wiring.py`   | Wiring — directed nerve graph (allow + forbid)               |
| `meowcat/nervous.py`  | Nervous — signal dispatch with middleware + circuit breaker  |
| `meowcat/reflex.py`   | ReflexArc — stimulus→response, zero-LLM paths                |
| `meowcat/tools/`      | Tool/Skill/Paws core (zero I/O abstractions)                 |
| `meowcat/plus/`       | Optional I/O: browser, ChromaDB, MCP, gateway, crystallizer  |
| `meowcat/colony/`     | Colony multi-cat container + federation                      |
| `meowcat/defaults/`   | Noop stubs, Renovated implants, presets, factory             |

---

## 📄 License

[MIT](LICENSE) © 2025-2026 Axonant — built with curiosity and cat-like instincts.
