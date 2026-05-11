# MeowCat AGENTS_EN.md — App Developer Entry

> 🎯 **Your identity**: meowcat app developer. You `pip install meowcat`, then `from meowcat import CatBase` to build your AI Agent.
> Read this for the mental model (3 min), then check [CATALOG.md](CATALOG.md) for default config, and [README.md](README.md) for project highlights.

---

## 1. One-Liner

meowcat is a **pure-abstraction AI Agent skeleton**. It defines "what organs a cat has and how they connect" — no concrete logic. You implement each organ's behavior: LLM reasoning, memory storage, safety checks, tool execution. Standalone pip package, zero external dependencies.

---

## 2. Picture: Colony + Private Rooms

```
┌─ 🏠 Colony ──────────────────────────────────────────────┐
│                                                          │
│   ┌── Shared Board ──────────────────────────────┐      │
│   │  [Owner]   Owner info (name, language, ...)   │      │
│   │  [Rules]   Laws all cats must follow          │      │
│   │  [Knowledge] Shared knowledge (semantic search)│     │
│   │  [Cats]    Roster of resident cats            │      │
│   │  [Growth]  Cross-cat anomalies & corrections  │      │
│   │  [Custom]  App-layer can add more namespaces  │      │
│   └───────────────────────────────────────────────┘      │
│                                                          │
│   ┌─ 🐱 Room 01 ─┐  ┌─ 🐱 Room 02 ─┐  ┌─ 🐱 Room 03 ─┐ │
│   │ Board  Desk   │  │ Board  Desk   │  │ Board  Desk   │ │
│   │ Bed  [Custom] │  │ Bed  [Custom] │  │ Bed  [Custom] │ │
│   └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Colony Shared Board — Public Area

All cats can see this board. Read/write via `colony.ns_get/set("namespace", "key", value)`.

| Board Area                 | What's Stored                                        | Code                                        |
| -------------------------- | ---------------------------------------------------- | ------------------------------------------- |
| **Owner** `owner/`         | name, email, language, extra (slack_id, role, etc.)  | `ColonyOwner` dataclass                     |
| **Rules** `rules/`         | Safety policies, approval requirements, rate limits  | `ColonyRules` (supports `on_check` hook)    |
| **Knowledge** `knowledge/` | Shared knowledge, semantic search enabled            | `SharedMemoryPool` (remember/recall/forget) |
| **Cats** `cats/`           | `{uid, name, brief, capabilities}` per cat           | namespace registered, app-layer populates   |
| **Growth** `growth/`       | Cross-cat anomaly and correction records             | `CollectiveGrowth`                          |
| **[Custom]**               | App-layer: `colony.storage_plug("namespace", "xxx")` | —                                           |

---

## 3.5 Colony Gate (Gateway + FrontDesk) — Sole External Entry

The Colony interacts with the outside world through a Gateway. **1 Colony : 1 Gateway : N Adapters.**

```
External World (HTTP/WS/CLI/IPC/Webhook)
    │
    ▼
┌─ Gateway ──────────────────────┐
│  ┌─ FrontDesk ─────────────┐  │
│  │  on_route plugin chain:   │  │
│  │  → security gate          │  │
│  │  → audit log              │  │
│  │  → rate limit             │  │
│  │  → custom routing         │  │
│  └──────────┬───────────────┘  │
└─────────────┼──────────────────┘
              │
              ▼
     Colony.cat.perceive()
```

### Core Design

- **Gateway is not an organ**: Not mounted on OrganHost — it's an independent Colony subsystem (the skin)
- **FrontDesk is the receptionist**: Protocol + Pluggable, all external messages must pass through `route()`
- **Plugin chain first-hit**: `on_route` plugins run in registration order, first non-None return short-circuits
- **Default routing**: `ctx.target_cat` set → forward to that cat via `cat.perceive()`; unset → placeholder reply

### Usage

```python
from meowcat import Colony, Gateway
from meowcat.gateway.front_desk import DefaultFrontDesk
from meowcat.plus.gateway import HttpAdapter

colony = Colony("my-colony")

# Default front desk
fd = DefaultFrontDesk()

# Mount security gate plugin (first-hit — blocks dangerous content)
fd.plug("on_route", lambda text, ctx, colony:
    "⚠️ Dangerous operation blocked" if "DROP TABLE" in text.upper() else None)

# Mount audit log plugin
fd.plug("on_route", lambda text, ctx, colony: print(f"[audit] {ctx.user_id}: {text[:50]}"))

# Create gateway, mount adapters
gw = Gateway(colony, front_desk=fd)
gw.mount_adapter(HttpAdapter(port=8000))
await gw.start()  # blocking, all adapters run in parallel
```

### Custom FrontDesk

```python
class MyFrontDesk(DefaultFrontDesk):
    async def route(self, text, ctx, colony):
        if ctx.platform == "slack":
            return await self._slack_dispatch(text, ctx, colony)
        return await super().route(text, ctx, colony)

gw = Gateway(colony, front_desk=MyFrontDesk())
```

---

## 4. Private Room — Per-Cat Private Area

Each cat has its own room with fixed furniture:

### 4.1 Board (CatSelf) — Identity Board on the Wall

The cat checks this board before every action. May update it after.

```
┌── Board (CatSelf) ────────────┐
│                                │
│  [Personality Card]  How to talk│
│   Personality: {tone, language} │
│                                │
│  [Beliefs Card]  What to believe│
│   Cortex L2: beliefs[]         │
│   "Always parameterize SQL"    │
│   "User table id type is uuid" │
│                                │
│  [Self-Knowledge Card]         │
│   Metacognition L3:            │
│   Good at: ["SQL", "Python"]   │
│   Bad at:  ["frontend"]        │
│                                │
└────────────────────────────────┘
```

- Before action: `CatSelf.before_act(reason)` — freeze snapshot, inject organ context
- After action: PinealGland `fuse_to_self` updates beliefs and self-knowledge

### 4.2 Desk (ScribblePad) — Temporary Scratchpad

Scribbles after each action. **Temporary buffer**, cleared when full.

```
┌── Desk (ScribblePad) ────────┐
│                                │
│  📝 "User asked about schema" │
│  📝 "Replied with CREATE TABLE"│
│  📝 "User prefers Python 3.12"│
│  ... (max 200 entries)         │
│                                │
│  📒 Logbook (episodes)         │
│  Permanent, one entry per turn │
│  "5/6 14:30 | Q:xxx | A:xxx"  │
│                                │
└────────────────────────────────┘
```

- Write: `CatSelf.after_act(summary, impact)` → scribble
- Logbook: `Hippocampus.remember()` → permanent record
- Clear: `PinealGland.trigger()` → drain() desk for distillation

### 4.3 Bed (Hippocampus entities) — Entity Graph

```
┌── Entity Graph ───────────────┐
│                                │
│  users ──id_type──▶ uuid       │
│  module_A ──depends_on──▶ B    │
│  ... (structured knowledge)    │
│                                │
└────────────────────────────────┘
```

- Long-term knowledge, survives desk clearing
- Search via `Hippocampus.fts_search()`

### 4.4 PinealGland — Distiller

Takes desk scribbles → distills into insights → updates board (inner loop) + colony board (outer loop).

```
Desk drain() → PinealGland meditate() → Insight[]
                                         ├── fuse_to_self   → Board (beliefs + self-knowledge)
                                         └── fuse_to_colony → Colony Board (shared knowledge)
```

### 4.5 Body (Organs) — The Working Parts

The cat's body is made of organs, orchestrated via Path/Chain/Loop:

| Category | Organ            | What It Does                  |
| -------- | ---------------- | ----------------------------- |
| Input    | Ears             | Hear text/voice               |
| Input    | Eyes             | See images                    |
| Input    | Whiskers         | Sense environment             |
| Brain    | Thalamus         | Route decisions               |
| Brain    | Hippocampus      | Memory + entity graph         |
| Brain    | Cortex           | Worldview distillation L0→L3  |
| Brain    | Cerebrum         | Deep thinking / LLM           |
| Brain    | Cerebellum       | Fast response / matching      |
| Brain    | Amygdala         | Safety check / reject         |
| Brain    | BrainStem        | Prompt building + lifecycle   |
| Brain    | Frontal          | Focus / task breakdown        |
| Brain    | Hypothalamus     | Memory decay / maintenance    |
| Output   | Mouth            | Speak                         |
| Output   | Purr             | Stream output                 |
| Output   | Tail             | Status display                |
| Tool     | Paws             | **Sole** tool execution entry |
| Growth   | AnomalyGrowth    | Anomaly pattern learning      |
| Growth   | CorrectionGrowth | Correction solidification     |
| Growth   | Crystallizer     | Skill crystallization         |
| Growth   | RoleEmergence    | Role emergence                |

> **Forbidden**: Brain → Paws direct connection. Tool execution must go Cerebrum → Cerebellum → Paws.

### 4.6 Adapters — Organs Can Be Swapped

Each organ is a socket. Plug in external implementations:

```python
from meowcat.adapters import HippocampusAgent
cat.mount("brain", "hippocampus", HippocampusAgent(your_memory_system))
```

All 16 organs have corresponding Adapters with delegation + error wrapping.

### 4.7 [Custom]

Add new furniture: mount organs `cat.mount("brain", "xxx", MyOrgan())`, add board cards `cat.cat_self.plug("before_act", my_hook)`, desk plugins `pad.plug("on_scribble", my_logger)`.

---

## 5. Built-in Paths — Single Step: From → To.Method → Action

One Path = one `signal(from, to, "method")`. 26 BUILTIN_PATHS in `path.py`.

### 5.1 Memory Domain — 13 paths

| Path                | From      | To                              | Action             |
| ------------------- | --------- | ------------------------------- | ------------------ |
| `locate`            | Thalamus  | Thalamus.locate()               | Memory search      |
| `remember`          | Brainstem | Hippocampus.remember()          | Store memory       |
| `get_entity`        | Thalamus  | Hippocampus.get_entity()        | Read single entity |
| `get_all`           | Thalamus  | Hippocampus.get_all()           | Read all entities  |
| `fts_search`        | Thalamus  | Hippocampus.fts_search()        | Full-text search   |
| `add_entity`        | Brainstem | Hippocampus.add_entity()        | Add entity         |
| `add_episode`       | Brainstem | Hippocampus.add_episode()       | Add episode        |
| `connect`           | Brainstem | Hippocampus.connect()           | Connect entities   |
| `record_access`     | Brainstem | Hippocampus.record_access()     | Record access      |
| `set_dormant`       | Brainstem | Hippocampus.set_dormant()       | Set dormant        |
| `append_content`    | Brainstem | Hippocampus.append_content()    | Append content     |
| `update_importance` | Brainstem | Hippocampus.update_importance() | Update importance  |
| `set_last_seen`     | Brainstem | Hippocampus.set_last_seen()     | Set last seen      |

### 5.2 Reasoning Domain — 3 paths

| Path            | From     | To                       | Action            |
| --------------- | -------- | ------------------------ | ----------------- |
| `deep_reason`   | Thalamus | Cerebrum.generate()      | Deep reasoning    |
| `decide_route`  | Thalamus | Thalamus.decide_route()  | Route decision    |
| `assess_safety` | Amygdala | Amygdala.assess_safety() | Safety assessment |

### 5.3 Output Domain — 2 paths

| Path    | From       | To              | Action        |
| ------- | ---------- | --------------- | ------------- |
| `hear`  | Ears       | Thalamus.hear() | Receive input |
| `speak` | Cerebellum | Mouth.speak()   | Output reply  |

### 5.4 Tool Domain — 1 path

| Path           | From       | To             | Action       |
| -------------- | ---------- | -------------- | ------------ |
| `execute_tool` | Cerebellum | Paws.execute() | Execute tool |

### 5.5 Maintenance Domain — 3 paths

| Path                 | From         | To                                       | Action        |
| -------------------- | ------------ | ---------------------------------------- | ------------- |
| `decay`              | Hypothalamus | Hippocampus.decay()                      | Memory decay  |
| `weaken_connections` | Hypothalamus | Hippocampus.weaken_connections()         | Weaken edges  |
| `cleanup_orphans`    | Hypothalamus | Hippocampus.cleanup_orphan_connections() | Clean orphans |

### 5.6 Synthesis + Workflow — 4 paths

| Path                  | From      | To                           | Action              |
| --------------------- | --------- | ---------------------------- | ------------------- |
| `synthesize`          | Brainstem | Cortex.synthesize()          | Worldview synthesis |
| `workflow_create`     | Brainstem | Hippocampus.add_entity()     | Create workflow     |
| `workflow_checkpoint` | Brainstem | Hippocampus.append_content() | Write checkpoint    |
| `workflow_resume`     | Brainstem | Hippocampus.get_entity()     | Resume workflow     |

Usage: `cat.signal(EARS, THALAMUS, "hear", raw_input="hello")` or declarative `Path("hear", EARS, THALAMUS, "hear")`.

---

## 6. Built-in Chains — Multi-Step Sequences

One Chain = named Path sequence executed in order. 6 BUILTIN_CHAINS.

| Chain                | Path Sequence                                                 | Location | Purpose            |
| -------------------- | ------------------------------------------------------------- | -------- | ------------------ |
| `memory_search`      | locate                                                        | chain.py | Memory search      |
| `conversation_chain` | hear → decide_route → locate → deep_reason → speak → remember | loops.py | Full conversation  |
| `tool_loop_chain`    | hear → decide_route → execute_tool → speak → remember         | loops.py | Tool execution     |
| `danger_chain`       | assess_safety                                                 | loops.py | Safety assessment  |
| `maintenance`        | decay → cleanup_orphans                                       | chain.py | Memory maintenance |
| `diagnostic`         | (empty — Stethoscope scan)                                    | chain.py | Health check       |

Usage: `await cat.chain_registry.run("conversation_chain", message="hello")`.

---

## 7. Built-in Loops — Chain + Trigger + Exit

One Loop = Chain + trigger condition + exit condition. 5 built-in.

| Loop              | Trigger             | Chain              | Exit           | Purpose            |
| ----------------- | ------------------- | ------------------ | -------------- | ------------------ |
| `conversation`    | `perceive.start`    | conversation_chain | Reply complete | Full conversation  |
| `tool_execution`  | `orchestrate.start` | tool_loop_chain    | Tool result    | Tool execution     |
| `danger_response` | `amygdala.alert`    | danger_chain       | Safety check   | Emergency response |
| `maintenance`     | `heartbeat.tick`    | maintenance        | Done           | Memory cleanup     |
| `diagnostic`      | Manual trigger      | diagnostic         | Done           | Health check       |

Usage: `await cat.run_loop("conversation", message="hello")` — one line runs the full organ pipeline.

---

## 8. CatSelf Loops — Board → Act → Desk → PinealGland → Update Board

The cat's self-evolution loop. Body does work outside (§7), but after each action there's introspection:

```
Board(before_act)              PinealGland(trigger_if)
  │ Read personality/beliefs       ↑
  ▼                               │
Body executes                     │ Drain desk
  │ Chat/task/learn               │ meditate() distill
  ▼                               │
Desk(after_act) ─────────────────→┘
  │ Scribble               fuse_to_self → Update Board (beliefs/self-knowledge)
  │                 fuse_to_colony → Colony Board (shared knowledge)
```

Three built-in room loops:

| Loop           | Flow                                                 | Fusion Trigger                 |
| -------------- | ---------------------------------------------------- | ------------------------------ |
| `conversation` | Read self → chat → reply → scribble → reflect        | `on_event("conversation_end")` |
| `task`         | Read self → analyze → execute → observe → scribble   | `on_full(50)` (desk full)      |
| `learn`        | Read self → blind spot → explore → verify → scribble | `trigger()` immediately        |

**Key**: `after_act()` only writes to desk. PinealGland fusion is triggered separately — app-layer decides when (full? every turn? timer?).

Usage: `loop = cat.cat_self.loop("conversation"); await loop.run(cat, "hello")`.

---

## 9. Two Loops: Inner (Self) + Outer (Colony)

```
Inner Loop (single cat evolution):
  Desk → PinealGland.meditate() → fuse_to_self → Board (beliefs + self-knowledge)

Outer Loop (collective intelligence):
  Desk → PinealGland.meditate() → fuse_to_colony → Colony Board / shared knowledge
                                                    → Other cats read → update their boards
```

The PinealGland is the hub: one distillation, both inner and outer.

---

## 10. Key Concepts

- **Slot-Plug Pattern**: Framework defines organ interfaces (Protocols), you provide implementations. 4 plug styles: `ALGORITHM` | `RULE` | `MODEL` | `HYBRID`
- **Cat is the Assembly Point**: All organs mount on CatBase via `cat.mount()`, communicate via `cat.signal()`
- **Paws is the Sole Tool Entry**: `cerebrum → cerebellum → paws` is the only legal tool execution path. Brain cannot directly control paws.
- **Prefer Four-Tier API**: Path (atomic signal) → Chain (sequence + rollback) → Loop (closed + events) → LoopSequence (orchestration)
- **CatSelf Self-Evolution**: After each action, `after_act()` writes to desk. PinealGland periodically distills → updates beliefs and self-knowledge
- **Inner + Outer Loops**: Inner updates self board, outer feeds Colony shared knowledge
- **Persona System (v2.5.0)**: Pre-built role masks that cats can wear/remove at any time. A persona contains personality (overrides CatSelf), beliefs (injected into Cortex), knowledge seeds (injected into Hippocampus), and tools (registered in SkillRegistry). Register with `colony.register_persona()`, wear with `cat.wear_persona()`, remove with `cat.unwear_persona()`. Supports YAML batch loading via `PersonaLoader`.

> More details on forbidden edges and write permissions → [CATALOG.md](CATALOG.md)

---

## 11. Quick API Reference

```python
from meowcat.defaults import create_cat, create_colony, KW_BILINGUAL, PROMPT_ZH

# Create a cat — only need cerebrum (LLM implementation)
cat = create_cat("Kitty", cerebrum=MyLLM(), keyword=KW_BILINGUAL, prompt=PROMPT_ZH)

# Unified perception entry
reply = await cat.perceive("Hello!")

# Path — atomic signal
await cat.path_registry.run("deep_reason", prompt="...")
await cat.path_registry.run("locate", query="weather")

# Chain — path sequence
await cat.chain_registry.run("conversation_chain", message="Hello")
await cat.chain_registry.run("maintenance_chain")

# Loop — closed-loop execution
await cat.run_loop("conversation", message="Hello!")

# Mount custom organ
cat.mount("brain", "hippocampus", MyHippocampus())

# Colony multi-cat container
colony = create_colony("my-colony")
cat_a = colony.create_cat("analyst", cerebrum=AnalystBrain())
cat_b = colony.create_cat("executor", cerebrum=ExecutorBrain())
await colony.signal_between("analyst", "executor", "brain", "amygdala", "assess_safety", input=data)

# CatSelf self-evolution
snapshot = cat.cat_self.before_act("conversation")
cat.cat_self.after_act("Answered user question", {"topic": "weather"})

# Gateway + FrontDesk
from meowcat import Gateway
from meowcat.gateway.front_desk import DefaultFrontDesk
from meowcat.plus.gateway import HttpAdapter

fd = DefaultFrontDesk()
fd.plug("on_route", lambda text, ctx, colony: print(f"[audit] {ctx.user_id}: {text[:50]}"))
gw = Gateway(colony, front_desk=fd)
gw.mount_adapter(HttpAdapter(port=8000))
await gw.start()

# v2.5.0 Persona system
from meowcat import Persona, PersonaLoader, Belief
from pathlib import Path

musk = Persona(
    name="musk",
    personality={"tone": "visionary", "language": "en+zh"},
    beliefs=[Belief(key="first_principles", value="Reason from first principles", confidence=0.95)],
    capable=["engineering", "physics"],
)
await colony.register_persona(musk)
await cat.wear_persona("musk")
cat.current_persona
await cat.unwear_persona()

loader = PersonaLoader(dir=Path("./personas"))
await loader.load_all(colony)
```

> Full assembly flow and all default configs → **[CATALOG.md](CATALOG.md)**

---

## 12. Install & Test

```bash
pip install meowcat          # Core framework
pip install meowcat[plus]    # With optional batteries (browser, ChromaDB, MCP)
pip install -e ".[dev]"      # Dev mode
pytest tests/ -v              # Run tests
```

Python 3.10+, core dependencies: `pydantic>=2.0` + `anyio>=4.0`.
