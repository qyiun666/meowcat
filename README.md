# meowcat

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-Axonant%2FMeowAgent-181717?style=flat-square&logo=github)](https://github.com/Axonant/MeowAgent)

> 🐱 **Solo indie project** — if you find this useful, a ⭐ star ⭐ would make this cat purr!

**An agent framework built on the biological blueprint of a cat.**

meowcat is the pure-framework layer of the MeowAgent ecosystem — cat anatomy:
protocols, neural wiring, reflexes, tools, and a four-layer abstraction from
atomic signals to composable closed loops. Bring your own LLM; the cat provides
everything else.

> Full catalog of 20 organs, 26 paths, 6 chains, 5 loops, entry/exit rules → **[CATALOG.md](CATALOG.md)**

---

## Big Picture

**Gateway (the cat's skin)** — sole external I/O entry/exit. All protocol adapters plug into one Gateway.

```
┌────────────────── Gateway — the cat's skin ───────────────────┐
│                                                              │
│   Outside World                                              │
│   HTTP · WebSocket · Webhook · CLI · IPC                    │
│          │                                                   │
│          ▼                                                   │
│   ┌──────────────────────────────┐                          │
│   │  Gateway._on_message()       │  ← 1 Cat : 1 Gateway    │
│   │  Gateway._on_stream()        │    : N Adapters          │
│   └──────────────┬───────────────┘                          │
│                  │                                           │
│                  ▼                                           │
│          cat.perceive()  →  enters cat's nervous system     │
│                                                              │
│   Gateway is not an organ — independent subsystem composing  │
│   with CatBase, not inheriting.                              │
│   Adapters: meowcat.plus.gateway (HTTP/WS/Webhook/CLI/IPC)   │
└──────────────────────────────────────────────────────────────┘
```

```
                        ┌──────────────────────────────────────────────────────────────┐
                        │                    THE CAT'S NERVOUS SYSTEM                     │
                        │                                                              │
   Human Input ──────► EARS ──► ╔══════════╗                                           │
   (text/voice)        (ears)    ║ THALAMUS ║──► CEREBRUM (cerebrum) ──► CEREBELLUM ─┬─► MOUTH ──► Text
                        │        ║  ★fork★  ║     deep reasoning         fast response │   (mouth)
                  ──────► EYES   ╚══╤══╤═══╝     (LLM call)            (effect router)├─► PURR  ──► Stream
                  (eyes)           │  │              │                       │          │   (purr)
                                   │  │              ▼                       ▼          ├─► TAIL  ──► Status
                  ──────► WHISKERS │  │         HIPPOCAMPUS                 PAWS       │   (tail)
                  (whiskers)       │  │         (memory graph)          (tool exec)    │
                                   │  │              │                                    │
                                   │  ├──────────────┤                                    │
                                   │  │  AMYGDALA ←──┼── fear bypass ────────────────────┤
                                   │  │  (safety)     │                                    │
                                   │  │               │                                    │
                                   │  └──► BRAINSTEM ─┴── master dispatch ────────────────┤
                                   │       (brainstem)                                     │
                                   │          │                                            │
                                   │          ▼                                            │
                                   │       FRONTAL ──► CORTEX                              │
                                   │       (focus)     (worldview L0-L3)                   │
                                   │                                                       │
                                   │    ┌─── Epiphany Pipeline ───────────────────────┐   │
                                   │    │  ScribblePad ──► PinealGland ──► meditate    │   │
                                   │    │  (fragments)      (pineal gland)   │         │   │
                                   │    │                                     ▼         │   │
                                   │    │              fuse_to_self ──► Cortex          │   │
                                   │    │              fuse_to_colony ──► SharedStorage │   │
                                   │    └──────────────────────────────────────────────┘   │
                                   │                                                       │
                                   │    ┌─── Active Growth ───────────────────────────┐   │
                                   │    │  BlindSpotDetector / ToolFailureLearner     │   │
                                   │    │  HotPathObserver / CollectiveGrowth         │   │
                                   │    └──────────────────────────────────────────────┘   │
                                   │                                                       │
                                   └─── CatSelf (unified self) ───────────────────────────┘
                                         before_act → act → after_act → scribble

   Legend:  ──► one-way    ★ fork ★ routing    ◄──► bidirectional
```

**Colony (Cat House)** — Multi-cat peer collaboration via SharedStorage.

```
┌─────────── Colony (Cat House) ──────────────────────────┐
│                                                          │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐             │
│  │  Cat A  │    │  Cat B  │    │  Cat C  │             │
│  │ (peer)  │◄──►│ (peer)  │◄──►│ (peer)  │             │
│  │ cat_uid= │    │ cat_uid= │    │ cat_uid= │             │
│  │  "a"   │    │  "b"   │    │  "c"   │             │
│  └────┬────┘    └────┬────┘    └────┬────┘             │
│       │              │              │                   │
│       └──────────────┼──────────────┘                   │
│                      │                                  │
│               ┌──────▼──────┐                           │
│               │ SharedStorage│ ← shared mem / state     │
│               └─────────────┘                           │
│                                                          │
│   Each cat internally = full nervous system (above).    │
│   Cats communicate via signal_between() + SharedStorage.│
└──────────────────────────────────────────────────────────┘
```

**Four-layer abstraction** — Path → Chain → Loop → LoopSequence — compose atomic signals into autonomous closed loops.

**Two closed loops** — Inner loop (self-evolution via CatSelf) + Outer loop (collective intelligence via Colony). The PinealGland is the hub.

> Detailed organ specs, entry/exit rules, path tables, and loop definitions → **[CATALOG.md](CATALOG.md)**

---

## Highlights

| Category              | What You Get                                                                       |
| --------------------- | ---------------------------------------------------------------------------------- |
| **Cat anatomy**       | 20 organs on a real neural blueprint (Thalamus, Hippocampus, Amygdala...)          |
| **Slot / Plug model** | Organ = typed slot (Protocol). Implementation = plug (4 styles). Swap freely.      |
| **Four-layer**        | Path (atomic) → Chain (sequence) → Loop (trigger+exit) → LoopSequence (meta)       |
| **Two closed loops**  | Inner: self-evolution. Outer: collective intelligence. PinealGland hub.            |
| **Epiphany pipeline** | ScribblePad → PinealGland → meditate → fuse_to_self / fuse_to_colony               |
| **Cortex L0-L3**      | Facts → Rules → Beliefs → Metacognition. All Pluggable.                            |
| **CatSelf**           | Unified self-model: before_act / after_act + 3 prefab default loops                |
| **Active Growth**     | BlindSpotDetector + ToolFailureLearner + HotPathObserver — the cat learns          |
| **Pluggable**         | Every organ supports runtime hook mount/unmount. 3 execution modes. Async-capable. |
| **Colony**            | Multi-cat peer collaboration: shared memory, cross-cat signal, federation          |
| **Signal safety**     | Circuit breaker per `(organ, method)` — auto-open on consecutive failures          |
| **Telemetry**         | Built-in Tracer + Metrics — zero-dependency observability for signal calls         |
| **Loop bridge**       | CatSelf DefaultLoop ↔ LoopRegistry bridge — compose both loop systems              |
| **Zero hardcoded**    | All thresholds, danger lists, language presets are constructor parameters          |
| **Lazy import**       | `import meowcat` loads only the skeleton. Full tree on first attribute access.     |
| **Zero I/O core**     | Framework has zero file/network I/O. All concrete I/O lives in `plus/`.            |
| **Dual track**        | Noop (bare shell) or Renovated (pre-furnished) — mix per organ.                    |
| **Bilingual**         | KW_EN / KW_ZH / KW_BILINGUAL keyword presets + PROMPT_DEFAULT / PROMPT_ZH          |

---

## Quick Start

```bash
pip install meowcat
```

### Renovated (furnished, 20 organs ready)

```python
from meowcat.defaults import create_cat, KW_BILINGUAL, PROMPT_ZH

class MyBrain:
    name = "cerebrum"
    async def generate(self, prompt, system_prompt=None, **kw) -> str:
        return f"Meow! You said: {prompt[:50]}"

cat = create_cat("Kitty", cerebrum=MyBrain(),
                 keyword=KW_BILINGUAL, prompt=PROMPT_ZH)

# Path — atomic signal
result = await cat.path_registry.run("locate", query="weather")

# Chain — named sequence
result = await cat.chain_registry.run("full_reasoning", prompt="Why is the sky blue?")

# Loop — closed loop with trigger/exit
result = await cat.run_loop("conversation", message="Hello!")

# LoopSequence — multi-loop orchestration
result = await cat.run_loopseq("daily_maintenance")
```

### Noop (bare shell, wire your own)

```python
cat = create_cat("Kitty", cerebrum=MyBrain(), renovated=False)
# All 20 organs are safe no-op stubs. Mount your own.
```

### Custom presets (your domain / language)

```python
from meowcat.defaults import create_cat, KeywordPreset, PromptPreset

cat = create_cat("my-bot", cerebrum=my_llm,
    keyword=KeywordPreset(
        name="logistics",
        stop_words=frozenset({"uh", "um", "the", "a"}),
        command_patterns={"ship": "action", "track": "memory"},
        danger_patterns=[],
        priority_keywords=["shipping", "logistics", "delivery"],
    ),
    prompt=PromptPreset(
        name="Logistics",
        templates={"chat": "You are a logistics AI. Domain: {domain}. Language: {language}."},
        pre_prompt="You are a professional logistics AI.",
        post_prompt="Do not promise specific delivery times.",
    ),
)
```

---

## Organ = Slot, Implementation = Plug

Every organ is a **slot** — a typed contract (Protocol) with defined in/out edges.
You pick a **plug** to fill it — algorithm, rule, model, or hybrid.

| Plug Style  | Meaning          | Example                        |
| ----------- | ---------------- | ------------------------------ |
| `ALGORITHM` | Pure code        | regex, dict lookup, subprocess |
| `RULE`      | Declarative rule | allowlist/blocklist, threshold |
| `MODEL`     | ML model         | LLM, classifier, embedding     |
| `HYBRID`    | Mixed            | rule-first → model fallback    |

Only **CEREBRUM requires MODEL**. The other 19 organs support at least ALGORITHM.

```python
from meowcat import ImplementationStyle
print(cat.organ("brain", "amygdala").impl_style)  # ImplementationStyle.ALGORITHM
```

---

## Four-Layer Architecture

```
  Organ ──► Path ──► Chain ──► Loop ──► LoopSequence
  single    atomic    named     Path+       multi-Loop
  unit      signal    Path seq  trigger     orchestration
```

| Layer       | Module       | Concept                                        | Count  |
| ----------- | ------------ | ---------------------------------------------- | ------ |
| **Organ**   | `anatomy.py` | 20 default organs (THALAMUS, CEREBRUM...)      | **20** |
| **Path**    | `path.py`    | 26 built-in atomic paths ("locate", "speak")   | **26** |
| **Chain**   | `chain.py`   | 6 built-in chains (MEMORY_SEARCH_CHAIN...)     | **6**  |
| **Loop**    | `loops.py`   | 5 built-in loops (CONVERSATION_LOOP...)        | **5**  |
| **LoopSeq** | `loops.py`   | 1 loop sequence (DAILY_MAINTENANCE_SEQ)        | **1**  |
| **Reflex**  | `reflex.py`  | 2 built-in reflex arcs (text_dialogue, danger) | **2**  |

> Full Path/Chain/Loop tables → **[CATALOG.md](CATALOG.md)**

---

## Memory Architecture — Multi-Dimensional

The cat's memory is not a single flat store — it's a **4×5×4×2** system spanning cognitive depth, functional organs, physical backends, and scope.

```
┌─── Cognitive Layers (Cortex L0→L3) ─────────────────────────────────────────┐
│                                                                              │
│   L0 Raw Facts        L1 Inferred Rules      L2 Beliefs       L3 Metacog.   │
│  ┌───────────┐    ┌──────────────────┐   ┌──────────────┐   ┌────────────┐  │
│  │Hippocampus│───→│  extract_rules   │──→│promote_belief│──→│Metacogni.  │  │
│  │ entities  │    │ "X is always Y"  │   │"Always param"│   │"I'm good X"│  │
│  │ episodes  │    │ conf 0.95        │   │conf 0.8 □    │   │"I can't Y" │  │
│  └───────────┘    └──────────────────┘   └──────────────┘   └────────────┘  │
│                                                                              │
│  Facts distilled via extract_rules → promoted to beliefs → self-awareness    │
└──────────────────────────────────────────────────────────────────────────────┘

┌─── Functional Organs (5 memory roles) ──────────────────────────────────────┐
│                                                                              │
│  Hippocampus   Hypothalamus    ScribblePad    PinealGland       Cortex      │
│  store·find     decay·clean     fragments(200) epiphany hub      worldview   │
│      ↑              ↑                ↑              ↑               ↑       │
│  BRAINSTEM writes  BRAINSTEM     CatSelf        trigger_if()     read-only   │
│      │           triggers     after_act      on_full/timer/event  terminal   │
│      └───────────────────────────┴───────────────────────────────┘           │
│                                    │                                          │
│                          Epiphany Pipeline                                    │
│                    fuse_to_self ↕ fuse_to_colony                             │
└──────────────────────────────────────────────────────────────────────────────┘

┌─── Storage Backends ──────────┐  ┌─── Scope ───────────────────────────────┐
│                               │  │                                           │
│  InMemoryStore    KV memory   │  │  Private ──── PinealGland ──── Shared    │
│  VectorStore      keyword /   │  │  Hippocampus       │       SharedStorage │
│                   semantic    │  │  ScribblePad        │       Collective*   │
│  SqliteGraphStore graph DB    │  │  Cortex             │                      │
│  JsonlL6Store     JSONL       │  │       fuse_to_self ─┴── fuse_to_colony   │
│                               │  │                                           │
└───────────────────────────────┘  └───────────────────────────────────────────┘

Legend:  ──→ data flow    ↑ write entry    ↕ bidirectional    □ challengeable
```

**Two closed loops** intersect here: **Inner** (Hippocampus → Cortex → CatSelf → ScribblePad → PinealGland → back to Cortex) for self-evolution, and **Outer** (PinealGland → SharedStorage → other cats) for collective intelligence.

---

## Organ Groups

### Brain (9)

| Organ            | Slot `(brain, ...)` | Role                                      |
| ---------------- | ------------------- | ----------------------------------------- |
| **THALAMUS**     | `thalamus`          | Route fork — all input passes through     |
| **HIPPOCAMPUS**  | `hippocampus`       | Memory — store, find, forget              |
| **CEREBRUM**     | `cerebrum`          | Deep reasoning (LLM)                      |
| **CEREBELLUM**   | `cerebellum`        | Fast response, sole upstream to effectors |
| **AMYGDALA**     | `amygdala`          | Safety review, danger detection           |
| **FRONTAL**      | `frontal`           | Focus / planning / topic tracking         |
| **HYPOTHALAMUS** | `hypothalamus`      | Homeostasis — memory decay, cleanup       |
| **CORTEX**       | `cortex`            | Worldview L0-L3, belief system            |
| **BRAINSTEM**    | `brainstem`         | Master dispatch hub, system prompt        |

### Senses (4)

| Organ        | Slot `(sense, ...)` | Role                        |
| ------------ | ------------------- | --------------------------- |
| **EARS**     | `ears`              | Text/voice input            |
| **EYES**     | `eyes`              | Image/video input           |
| **WHISKERS** | `whiskers`          | Environment sensing, drift  |
| **PAWS**     | `paws`              | Tool execution (sole entry) |

### Voice (3)

| Organ     | Slot `(voice, ...)` | Role              |
| --------- | ------------------- | ----------------- |
| **MOUTH** | `mouth`             | Text output       |
| **PURR**  | `purr`              | Streaming status  |
| **TAIL**  | `tail`              | Status bar render |

### Growth (4)

| Organ                 | Slot `(growth, ...)` | Role                      |
| --------------------- | -------------------- | ------------------------- |
| **ANOMALY_GROWTH**    | `anomaly_growth`     | Anomaly sedimentation     |
| **CORRECTION_GROWTH** | `correction_growth`  | Correction solidification |
| **CRYSTALLIZER**      | `crystallizer`       | Skill crystallization     |
| **ROLE_EMERGENCE**    | `role_emergence`     | Implicit role emergence   |

> Full organ entry/exit rules → **[CATALOG.md](CATALOG.md)**

---

## Architecture — Implemented

- 20 organs, 26 paths, 6 chains, 5 loops, 2 reflexes, 1 loop sequence
- Two closed loops: inner (CatSelf self-evolution) + outer (Colony collective intelligence)
- ScribblePad → PinealGland epiphany pipeline + Cortex L0-L3 worldview
- Active Growth: BlindSpotDetector + ToolFailureLearner + HotPathObserver
- CatSelf unified self-model + 3 prefab default loops (conversation / task / learn)
- Pluggable organ plugin system (async-capable, 3 execution modes)
- Colony multi-cat peer collaboration + GlobalColonyRegistry + WorkerScheduler
- Bilingual keyword presets (EN/ZH/Bilingual) + Noop/Renovated dual track
- Gateway I/O abstraction (HTTP/WS/Webhook/CLI/IPC adapters in `plus/gateway/`)
- Signal middleware (logger, rate-limiter, timeout, context-injector) + circuit breaker
- Built-in telemetry: Tracer + Metrics + SignalSpan (zero external dependencies)
- CatSelf DefaultLoop ↔ LoopRegistry bridge (compose both loop systems)
- Lazy import (`import meowcat` loads skeleton only)
- Zero hardcoded magic values — all thresholds/patterns are constructor parameters
- `plus/` optional batteries (file I/O, browser, MCP client, ChromaDB, skill loader, gateway)

## Future Directions

1. PinealGland fusion event broadcasting — GrowthEvent on fuse_to_self/fuse_to_colony
2. ScribblePad persistent presets — DefaultScribblePersister auto-writes to JsonlL6Store
3. `execute_tool` Path migration to unified `execute()` on PawsProtocol

---

## Version History

```
v1.2.24~v1.2.33 (2026-05-05) — Full polish: 11 bug/security fixes, 9 code-quality cleanups, 3 architecture refinements across 34 roadmap items; magic numbers extracted to constants.py, exception-swallowing audited, lazy-import coupling documented
v1.2.15~v1.2.23 (2026-05-04) — Architecture polish: hot-path perf, Pluggable async, event type-safety, circuit breaker, loop bridge, telemetry, WorkerScheduler, adapters, gateway→plus
v1.2.6~v1.2.13 (2026-05-04) — Plus refactor: 4 bugs fixed, plus/ created, industry presets removed, Renovated fully parameterized, colony split + lazy init
v1.2.0        (2026-05-04) — CatSelf unified self + ScribblePad→PinealGland pipeline + Cortex L0-L3 + Metacognition + Active Growth
v1.1.1~v1.1.29 (2026-05-03~04) — ScribblePad, PinealGland, Cortex worldview, Active Growth trio, CollectiveGrowth+Emergence, GlobalColonyRegistry
v1.1.0        (2026-05-03) — Renovated/Noop dual-track, ImplementationStyle 4 plug styles, bilingual presets, 20 organs pre-loaded, CATALOG.md
v1.0.1~v1.0.18 (2026-05-01~03) — 20 organs+26 paths+6 chains+5 loops, Pluggable system, Colony multi-cat, Gateway I/O, Middleware, Lifecycle Hooks, Workflow
v1.0.0        (2026-05-01) — Initial release: cat neural framework core, four-layer Path→Chain→Loop→LoopSeq, pip install meowcat
```

---

## Examples

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

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

_Built with the biological blueprint of a cat. The framework layer of [MeowAgent](https://github.com/Axonant/MeowAgent)._
