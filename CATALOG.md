# MeowCat v1.2.23 — Full Catalog

> 20 organs + 26 paths + 6 chains + 5 loops + 3 default loops + 2 reflexes + 1 loop sequence + epiphany pipeline + telemetry + circuit breaker + WorkerScheduler

---

## Core Concepts

```
Organ = Slot (typed contract)    ← Protocol defining in/out edges + method permissions
Impl  = Plug (fill style)        ← internal style: algorithm / rule / model / hybrid

★ Epiphany Pipeline: ScribblePad → PinealGland → meditate → fuse_to_self / fuse_to_colony
★ Two Closed Loops: Inner (CatSelf → Cortex/Metacognition) + Outer (PinealGland → SharedStorage → other cats)
```

### Plug Styles (ImplementationStyle)

| Style       | Value       | Meaning          | Typical Example                |
| ----------- | ----------- | ---------------- | ------------------------------ |
| `ALGORITHM` | `algorithm` | Pure code        | regex, dict, subprocess        |
| `RULE`      | `rule`      | Declarative rule | allowlist/blocklist, threshold |
| `MODEL`     | `model`     | ML model         | LLM, classifier, embedding     |
| `HYBRID`    | `hybrid`    | Mixed            | rule-first → model fallback    |

---

## I. Organ Catalog (20 organs)

### Brain (9)

#### 1. THALAMUS — Route Fork Point

```
Slot:          (brain, thalamus)
Protocol:      ThalamusProtocol
Role:          Route decision — all input passes through me first

Entry Rules:
  - Can receive signal from: EARS, EYES, WHISKERS
  - Self-loop allowed: locate(), decide_route() callable without wiring check
  - Protocol check: must implement ThalamusProtocol

Exit Rules:
  - Can signal to: CEREBRUM, BRAINSTEM, AMYGDALA, HIPPOCAMPUS
  - Cannot signal to: CEREBELLUM (forbidden edge)
  - All out-edges wired at assembly time

Read Methods:   locate, decide_route
Supported Plugs: [algorithm, rule, model, hybrid]
Renovated Plug:  ALGORITHM (keyword match + /command detection)
Noop Plug:       ALGORITHM (always returns route=chat)
```

#### 2. HIPPOCAMPUS — Memory

```
Slot:          (brain, hippocampus)
Protocol:      HippocampusProtocol
Role:          Memory — single entry for store, find, forget

Entry Rules:
  - Read from: CEREBRUM, FRONTAL, HYPOTHALAMUS, BRAINSTEM, THALAMUS
  - Write from: BRAINSTEM, HYPOTHALAMUS (only these two may write)
  - Write callers enforced by OrganSpec.write_callers

Exit Rules:
  - Can signal to: CEREBRUM, CORTEX
  - Terminal for writes (read-only output to CORTEX)

Read Methods:   entities, episodes, locate, get_entity, get_all, get_by_name,
                get_related, stats, fts_search, to_dict
Write Methods:  remember, add_entity, add_episode, connect, decay,
                weaken_connections, cleanup_orphan_connections, from_dict,
                record_access, set_dormant, append_content,
                update_importance, set_last_seen
Write Permissions: BRAINSTEM, HYPOTHALAMUS (enforced by wiring)
Supported Plugs: [algorithm, model, hybrid]
Renovated Plug:  ALGORITHM (InMemoryGraphStore + keyword index)
Noop Plug:       ALGORITHM (empty dict/list)
```

#### 3. CEREBRUM — Deep Reasoning (A-Brain)

```
Slot:          (brain, cerebrum)
Protocol:      LLMBrainProtocol
Role:          Deep reasoning — invokes LLM for complex thinking

Entry Rules:
  - Can receive signal from: THALAMUS, HIPPOCAMPUS, FRONTAL, BRAINSTEM
  - Requires MODEL or HYBRID plug (only organ with this restriction)

Exit Rules:
  - Can signal to: HIPPOCAMPUS, CEREBELLUM, FRONTAL
  - Cannot signal to: PAWS (brain→paws forbidden), MOUTH (brain→mouth forbidden)

Methods:       generate(), stream_generate(), reload_config(), diagnose()
Supported Plugs: [model, hybrid]
Renovated Plug:  MODEL (callable LLM adapter)
Noop Plug:       ALGORITHM (returns empty string)
```

#### 4. CEREBELLUM — Fast Response (B-Brain)

```
Slot:          (brain, cerebellum)
Protocol:      LLMBrainProtocol
Role:          Fast response — sole upstream for all effectors

Entry Rules:
  - Can receive signal from: CEREBRUM, AMYGDALA, BRAINSTEM
  - Cannot receive from: THALAMUS (forbidden edge)

Exit Rules:
  - Can signal to: PAWS, MOUTH, PURR, TAIL (all EFFECTORS)
  - Sole gateway to effectors — nothing else can drive output directly
  - Cannot signal back to: CEREBRUM (forbidden — cerebellum does not feed back to cerebrum)

Methods:       generate(), stream_generate(), reload_config(), diagnose()
Supported Plugs: [model, algorithm, hybrid]
Renovated Plug:  MODEL (callable LLM adapter)
Noop Plug:       ALGORITHM (returns empty string)
```

#### 5. AMYGDALA — Safety

```
Slot:          (brain, amygdala)
Protocol:      AmygdalaProtocol
Role:          Safety review — danger detection + risk assessment

Entry Rules:
  - Can receive signal from: THALAMUS, BRAINSTEM, EARS, EYES, WHISKERS
  - Bypass path: SENSORS → AMYGDALA (fast fear bypass, no thalamus routing)
  - assess_safety() is a self-loop (no wiring, direct method call)

Exit Rules:
  - Can signal to: CEREBELLUM, MOUTH, CEREBRUM, ANOMALY_GROWTH, CORRECTION_GROWTH
  - Cannot signal to: HIPPOCAMPUS (amygdala does not directly access memory)
  - Danger output can bypass reasoning: AMYGDALA → MOUTH directly

Methods:       is_rejection, classify_rejection, parse_correction,
               handle_rejection, handle_correction, assess_safety, assess_tool_risk
Supported Plugs: [algorithm, rule, model, hybrid]
Renovated Plug:  ALGORITHM (bilingual regex safety scan)
Noop Plug:       ALGORITHM (always returns safe=True)
```

#### 6. FRONTAL — Focus / Planning

```
Slot:          (brain, frontal)
Protocol:      FrontalCortexProtocol
Role:          Focus/Planning — topic management + task decomposition

Entry Rules:
  - Can receive signal from: CEREBRUM, BRAINSTEM

Exit Rules:
  - Can signal to: CEREBRUM, HIPPOCAMPUS, BRAINSTEM

Methods:       detect_shift, is_continue, archive_focus, update_focus, save, load
Supported Plugs: [algorithm, model, hybrid]
Renovated Plug:  ALGORITHM (keyword overlap topic detection)
Noop Plug:       ALGORITHM (always returns False)
```

#### 7. HYPOTHALAMUS — Homeostasis

```
Slot:          (brain, hypothalamus)
Protocol:      HypothalamusProtocol
Role:          Self-maintenance — memory decay + orphan cleanup

Entry Rules:
  - Can receive signal from: BRAINSTEM
  - Has write permission to HIPPOCAMPUS (enforced by OrganSpec.write_callers)

Exit Rules:
  - Can signal to: HYPOTHALAMUS (self-loop), HIPPOCAMPUS, CORTEX
  - run_maintenance() is self-loop; decay/cleanup go to HIPPOCAMPUS

Methods:       run_maintenance, decay_memories, compress_long_history
Supported Plugs: [algorithm, rule]
Renovated Plug:  ALGORITHM (TTL-configurable decay)
Noop Plug:       ALGORITHM (returns zero counts)
```

#### 8. CORTEX — Worldview

```
Slot:          (brain, cortex)
Protocol:      CortexProtocol
Role:          Worldview — distill cognition from experience

Entry Rules:
  - Can receive signal from: HIPPOCAMPUS, HYPOTHALAMUS, BRAINSTEM
  - L0-L3 pipeline: facts → rules → beliefs → metacognition

Exit Rules:
  - None — terminal organ, only read

Methods:       ingest, record_weakness, weaknesses, synthesize,
               extract_rules, promote_to_belief, challenge_belief
Supported Plugs: [algorithm, model, hybrid]
Renovated Plug:  ALGORITHM (4-layer worldview dict)
Noop Plug:       ALGORITHM (returns empty)
```

#### 9. BRAINSTEM — Master Dispatch Hub

```
Slot:          (brain, brainstem)
Protocol:      BrainStemProtocol
Role:          Coordination hub — lifecycle + flow orchestration

Entry Rules:
  - Can receive signal from: THALAMUS
  - Acts as central coordinator — the only organ that can send to all others

Exit Rules:
  - Can signal to: THALAMUS, HIPPOCAMPUS, CEREBRUM, CEREBELLUM, AMYGDALA,
    FRONTAL, HYPOTHALAMUS, CORTEX, ANOMALY_GROWTH, CORRECTION_GROWTH,
    CRYSTALLIZER, ROLE_EMERGENCE, EARS, EYES, WHISKERS, MOUTH, PURR, TAIL
  - Has write permission to HIPPOCAMPUS (enforced)
  - All lifecycle events originate from here

Methods:       build_system_prompt, cancel_current, diagnose
Supported Plugs: [algorithm, rule, model, hybrid]
Renovated Plug:  ALGORITHM (PromptPreset template builder)
Noop Plug:       ALGORITHM (returns empty)
```

---

### Senses (4)

#### 10. EARS — Text Input

```
Slot:          (sense, ears)
Protocol:      EarsProtocol
Role:          Text input — CLI/API/Discord/Telegram

Entry Rules:
  - Pure input terminal — no incoming wiring edges
  - Receives raw input from application layer

Exit Rules:
  - Can signal to: THALAMUS, AMYGDALA
  - Output is standardized text + keywords + language tag

Methods:       hear, extract_keywords, detect_language, tag_emotion
Supported Plugs: [algorithm]
Renovated Plug:  ALGORITHM (text normalization + keyword + zh/en detection)
Noop Plug:       ALGORITHM (returns as-is)
```

#### 11. EYES — Visual Input

```
Slot:          (sense, eyes)
Protocol:      EyesProtocol
Role:          Visual input — images/video

Entry Rules:
  - Pure input terminal — no incoming wiring edges

Exit Rules:
  - Can signal to: THALAMUS, AMYGDALA

Methods:       see
Supported Plugs: [algorithm, model, hybrid]
Renovated Plug:  ALGORITHM (magic bytes format detection)
Noop Plug:       ALGORITHM (returns empty dict)
```

#### 12. WHISKERS — Environment Sensing

```
Slot:          (sense, whiskers)
Protocol:      WhiskersProtocol
Role:          Environment sensing — I/O anomaly detection

Entry Rules:
  - Pure input terminal — no incoming wiring edges

Exit Rules:
  - Can signal to: THALAMUS, AMYGDALA, ANOMALY_GROWTH
  - Direct path to ANOMALY_GROWTH for anomaly recording (bypass thalamus)

Methods:       feel_input, feel_output, detect_drift, check_hallucination
Supported Plugs: [algorithm, model, hybrid]
Renovated Plug:  ALGORITHM (input/output sensing + drift detection)
Noop Plug:       ALGORITHM (returns empty)
```

#### 13. PAWS — Tool Execution

```
Slot:          (sense, paws)
Protocol:      PawsProtocol
Role:          Tool execution — Skill/MCP/commands

Entry Rules:
  - Can receive signal from: CEREBELLUM (ONLY)
  - Brain→PAWS is a forbidden edge — tool calls must route through cerebellum

Exit Rules:
  - None — terminal executor

Methods:       execute, touch_file, run_command, interact_with_tool
Supported Plugs: [algorithm, rule, hybrid]
Renovated Plug:  ALGORITHM (tool_registry integration + safety pre-check)
Noop Plug:       ALGORITHM (returns ok=False)
```

---

### Voice (3)

#### 14. MOUTH — Text Output

```
Slot:          (voice, mouth)
Protocol:      MouthProtocol
Role:          Voice output — TTS + text reply

Entry Rules:
  - Can receive signal from: CEREBELLUM, AMYGDALA, BRAINSTEM
  - AMYGDALA→MOUTH is the danger bypass path (no reasoning)

Exit Rules:
  - None — terminal output organ

Methods:       speak, diagnose
Supported Plugs: [algorithm]
Renovated Plug:  ALGORITHM (stdout print + log)
Noop Plug:       ALGORITHM (returns empty string)
```

#### 15. PURR — Streaming

```
Slot:          (voice, purr)
Protocol:      PurrProtocol
Role:          Streaming status — progress indication

Entry Rules:
  - Can receive signal from: CEREBELLUM, BRAINSTEM

Exit Rules:
  - None — terminal output organ

Methods:       stream, diagnose
Supported Plugs: [algorithm]
Renovated Plug:  ALGORITHM (streaming status tracker)
Noop Plug:       ALGORITHM (returns None)
```

#### 16. TAIL — Status Bar

```
Slot:          (voice, tail)
Protocol:      TailProtocol
Role:          Status bar — CLI/TUI health signal

Entry Rules:
  - Can receive signal from: CEREBELLUM, BRAINSTEM

Exit Rules:
  - None — terminal output organ

Methods:       render, diagnose
Supported Plugs: [algorithm]
Renovated Plug:  ALGORITHM (status bar render)
Noop Plug:       ALGORITHM (no-op)
```

---

### Growth (4) — Loop C: Evolution Circuit

#### 17. ANOMALY_GROWTH — Anomaly Sedimentation

```
Slot:          (growth, anomaly_growth)
Protocol:      AnomalyGrowthProtocol
Role:          Anomaly sedimentation — user-flagged anomalies → persistent

Entry Rules:
  - Can receive signal from: BRAINSTEM, AMYGDALA, WHISKERS

Exit Rules:
  - Can signal to: HIPPOCAMPUS, CORTEX

Methods:       record, diagnose
Supported Plugs: [algorithm, model, hybrid]
Renovated Plug:  ALGORITHM (in-memory anomaly log)
Noop Plug:       ALGORITHM (no-op)
```

#### 18. CORRECTION_GROWTH — Correction Solidification

```
Slot:          (growth, correction_growth)
Protocol:      CorrectionGrowthProtocol
Role:          Correction solidification — user corrections → permanent fixes

Entry Rules:
  - Can receive signal from: BRAINSTEM, AMYGDALA

Exit Rules:
  - Can signal to: HIPPOCAMPUS, CORTEX

Methods:       record, diagnose
Supported Plugs: [algorithm, model, hybrid]
Renovated Plug:  ALGORITHM (in-memory correction log)
Noop Plug:       ALGORITHM (no-op)
```

#### 19. CRYSTALLIZER — Skill Crystallization

```
Slot:          (growth, crystallizer)
Protocol:      CrystallizerProtocol
Role:          Experience crystallization — frequent ops → reusable skills

Entry Rules:
  - Can receive signal from: BRAINSTEM

Exit Rules:
  - None — terminal

Methods:       crystallize, hotspots, diagnose
Supported Plugs: [algorithm, model, hybrid]
Renovated Plug:  ALGORITHM (hit counter + hotspot detection)
Noop Plug:       ALGORITHM (returns False/empty)
```

#### 20. ROLE_EMERGENCE — Role Emergence

```
Slot:          (growth, role_emergence)
Protocol:      RoleEmergenceProtocol
Role:          Role emergence — behavior patterns → implicit roles

Entry Rules:
  - Can receive signal from: BRAINSTEM

Exit Rules:
  - None — terminal

Methods:       record, diagnose
Supported Plugs: [algorithm, model, hybrid]
Renovated Plug:  ALGORITHM (behavior pattern log)
Noop Plug:       ALGORITHM (no-op)
```

---

## II. Epiphany Pipeline (v1.1.23–v1.2.0)

### ScribblePad — Private Scratchpad

```
Component:    Pluggable (not in OrganHost)
Mount Point:  cat.cat_self.scribble_pad
Role:         Fragment accumulation buffer — store only, no judgment. Socket design.
Capacity:     200 items (default)
Plug Slots:   on_scribble / on_drain / post_filter
Presets:      DefaultScribbleFilter (dedup) / DefaultScribbleLogger (log)
```

### PinealGland — Epiphany Organ (Hub)

```
Component:    Pluggable (not in OrganHost)
Mount Point:  cat.cat_self.pineal_gland
Role:         Junction of two loops — fragments → insights, bidirectional fusion
Flow:         drain → meditate(merger→contradiction→filter) → fuse_to_self + fuse_to_colony
Plug Slots:   merger / contradiction / filter
Presets:      DefaultMerger / DefaultContradiction / DefaultInsightFilter
Fusion Hooks: on_fuse_self (app sets → Cortex) / on_fuse_colony (app sets → SharedStorage)
```

### FusionCycle — Trigger Strategies

| Strategy      | Trigger Condition      | Usage                                                  |
| ------------- | ---------------------- | ------------------------------------------------------ |
| `on_full(n)`  | ScribblePad at n items | `trigger_if(FusionCycle.on_full(50))`                  |
| `on_timer(m)` | Every m minutes        | `trigger_if(FusionCycle.on_timer(30))`                 |
| `on_event(e)` | Event fired            | `trigger_if(FusionCycle.on_event("conversation_end"))` |

### Cortex — Four-Layer Worldview

```
L0: Raw Facts (Hippocampus entities)
L1: Inferred Rules (extract_rules: frequency stats → {if, then, confidence})
L2: Beliefs (promote_to_belief / challenge_belief → challengeable, revisable)
L3: Metacognition (Metacognition.self_assess → capable/incapable/unknown)
```

### Metacognition — Self-Knowledge L3

```
Role:        Cat's self-awareness — what I can / cannot / don't know
Methods:     self_assess(domain) → {capable, confidence, evidence} or {suggestion: "explore"}
Driven by:   BlindSpotDetector curiosity → record_capability
```

### Active Growth — Three Components

| Component              | Function                           | Drives To                         |
| ---------------------- | ---------------------------------- | --------------------------------- |
| **BlindSpotDetector**  | Detect knowledge gaps from queries | → Metacognition.record_capability |
| **ToolFailureLearner** | Record tool failure patterns       | → AnomalyGrowth.record()          |
| **HotPathObserver**    | Track high-frequency reflex paths  | → Crystallizer.crystallize()      |

### CatSelf — Unified Self Meta-Organ

```
Component:    Pluggable (meta-organ, outside OrganHost/Wiring)
Mount Point:  cat.cat_self
Role:         Single entry for all organ reads/writes — ultimate start + ultimate end
Holds:        Personality / Cortex / Metacognition / Skills / Reflexes / ScribblePad / PinealGland
Loop Nodes:   before_act(freeze snapshot) → action → after_act(scribble fragment)
Default Loops: conversation / task / learn (three presets, plug-and-play)
```

### CollectiveGrowth + CollectiveEmergence

| Component               | Location            | Function                                     |
| ----------------------- | ------------------- | -------------------------------------------- |
| **CollectiveGrowth**    | `biology/growth.py` | Cross-cat anomaly/correction → SharedStorage |
| **CollectiveEmergence** | `biology/roles.py`  | Behavior pattern analysis → role emergence   |

---

## III. Forbidden Edges

| Forbidden Edge               | Reason                                                   |
| ---------------------------- | -------------------------------------------------------- |
| CEREBRUM → PAWS              | Brain does not directly control limbs                    |
| CEREBRUM → MOUTH             | Brain does not directly drive speech                     |
| CEREBRUM → ANOMALY_GROWTH    | Brain does not directly trigger growth                   |
| CEREBRUM → CORRECTION_GROWTH | Brain does not directly trigger correction               |
| CEREBRUM → CRYSTALLIZER      | Brain does not directly crystallize skills (v1.2.17)     |
| CEREBRUM → ROLE_EMERGENCE    | Brain does not directly trigger role emergence (v1.2.17) |
| CEREBELLUM → CEREBRUM        | Cerebellum does not feed back to cerebrum                |
| AMYGDALA → HIPPOCAMPUS       | Amygdala does not directly access memory                 |
| THALAMUS → CEREBELLUM        | Thalamus does not bypass cerebrum                        |

---

## IV. Path Catalog (26 paths)

Each Path = `from_organ → to_organ.method` atomic signal recipe.

### Self-Loop Paths (no wiring, direct method call)

| #   | Path            | Signal                            | Mode | Description   |
| --- | --------------- | --------------------------------- | ---- | ------------- |
| P1  | `locate`        | THALAMUS → THALAMUS.locate        | read | Memory search |
| P2  | `decide_route`  | THALAMUS → THALAMUS.decide_route  | read | Route fork    |
| P3  | `assess_safety` | AMYGDALA → AMYGDALA.assess_safety | read | Safety check  |

### Cross-Organ Paths

#### Input Domain (Sense → Brain)

| #   | Path   | Signal               | Mode | Description |
| --- | ------ | -------------------- | ---- | ----------- |
| P4  | `hear` | EARS → THALAMUS.hear | read | Text input  |

#### Reasoning Domain (Brain Internal)

| #   | Path          | Signal                       | Mode | Description    |
| --- | ------------- | ---------------------------- | ---- | -------------- |
| P5  | `deep_reason` | THALAMUS → CEREBRUM.generate | read | Deep reasoning |

#### Output Domain (Brain → Voice)

| #   | Path    | Signal                   | Mode  | Description |
| --- | ------- | ------------------------ | ----- | ----------- |
| P6  | `speak` | CEREBELLUM → MOUTH.speak | write | Text output |

#### Tool Domain (Brain → Paws)

| #   | Path           | Signal                               | Mode  | Description |
| --- | -------------- | ------------------------------------ | ----- | ----------- |
| P7  | `execute_tool` | CEREBELLUM → PAWS.interact_with_tool | write | Tool exec   |

#### Memory Domain (Brain ↔ Hippocampus)

| #   | Path                | Signal                                    | Mode  | Description        |
| --- | ------------------- | ----------------------------------------- | ----- | ------------------ |
| P8  | `remember`          | BRAINSTEM → HIPPOCAMPUS.remember          | write | Store memory       |
| P9  | `get_entity`        | THALAMUS → HIPPOCAMPUS.get_entity         | read  | Read entity        |
| P10 | `get_all`           | THALAMUS → HIPPOCAMPUS.get_all            | read  | Read all entities  |
| P11 | `fts_search`        | THALAMUS → HIPPOCAMPUS.fts_search         | read  | Full-text search   |
| P12 | `add_entity`        | BRAINSTEM → HIPPOCAMPUS.add_entity        | write | Add entity         |
| P13 | `add_episode`       | BRAINSTEM → HIPPOCAMPUS.add_episode       | write | Add episode        |
| P14 | `connect`           | BRAINSTEM → HIPPOCAMPUS.connect           | write | Connect entities   |
| P15 | `record_access`     | BRAINSTEM → HIPPOCAMPUS.record_access     | write | Record access      |
| P16 | `set_dormant`       | BRAINSTEM → HIPPOCAMPUS.set_dormant       | write | Set dormant        |
| P17 | `append_content`    | BRAINSTEM → HIPPOCAMPUS.append_content    | write | Append content     |
| P18 | `update_importance` | BRAINSTEM → HIPPOCAMPUS.update_importance | write | Update importance  |
| P19 | `set_last_seen`     | BRAINSTEM → HIPPOCAMPUS.set_last_seen     | write | Set last seen time |

#### Maintenance Domain (Hypothalamus → Hippocampus)

| #   | Path                 | Signal                                                | Mode  | Description        |
| --- | -------------------- | ----------------------------------------------------- | ----- | ------------------ |
| P20 | `decay`              | HYPOTHALAMUS → HIPPOCAMPUS.decay                      | write | Memory decay       |
| P21 | `weaken_connections` | HYPOTHALAMUS → HIPPOCAMPUS.weaken_connections         | write | Weaken connections |
| P22 | `cleanup_orphans`    | HYPOTHALAMUS → HIPPOCAMPUS.cleanup_orphan_connections | write | Cleanup orphans    |

#### Synthesis Domain (Brain → Cortex)

| #   | Path         | Signal                        | Mode | Description         |
| --- | ------------ | ----------------------------- | ---- | ------------------- |
| P23 | `synthesize` | BRAINSTEM → CORTEX.synthesize | read | Worldview synthesis |

#### Workflow Domain

| #   | Path                  | Signal                                 | Mode  | Description      |
| --- | --------------------- | -------------------------------------- | ----- | ---------------- |
| P24 | `workflow_create`     | BRAINSTEM → HIPPOCAMPUS.add_entity     | write | Create workflow  |
| P25 | `workflow_checkpoint` | BRAINSTEM → HIPPOCAMPUS.append_content | write | Write checkpoint |
| P26 | `workflow_resume`     | BRAINSTEM → HIPPOCAMPUS.get_entity     | read  | Resume workflow  |

---

## V. Chain Catalog (6 chains)

Each Chain = named Path sequence. Previous result passed as kwargs to next.

| #   | Chain            | Path Sequence                                              | Description          |
| --- | ---------------- | ---------------------------------------------------------- | -------------------- |
| C1  | `memory_search`  | `locate`                                                   | Memory search        |
| C2  | `full_reasoning` | `deep_reason` → `speak`                                    | Deep reason → output |
| C3  | `tool_exec`      | `execute_tool`                                             | Tool execution       |
| C4  | `maintenance`    | `decay` → `cleanup_orphans`                                | Memory maintenance   |
| C5  | `diagnostic`     | (empty — Stethoscope)                                      | Health check         |
| C6  | `workflow_chain` | `workflow_create` → `execute_tool` → `workflow_checkpoint` | Long workflow        |

---

## VI. Loop Catalog

### 6.1 LoopRegistry Loops (5) — Organ-to-Organ Signal Orchestration

Each Loop = Chain + trigger event + exit event.

```
★ CONVERSATION_LOOP — Loop A: Perceive-Reason-Output
├─ trigger:  perceive.start
├─ chain:    hear → decide_route → locate → deep_reason → speak → remember
└─ path:     EARS→THALAMUS→CEREBRUM→CEREBELLUM→MOUTH→HIPPOCAMPUS
```

| #   | Loop              | Chain                                               | Trigger             | Description             |
| --- | ----------------- | --------------------------------------------------- | ------------------- | ----------------------- |
| L1  | `conversation`    | hear→decide_route→locate→deep_reason→speak→remember | `perceive.start`    | Loop A: perceive-output |
| L2  | `tool_execution`  | hear→decide_route→execute_tool→speak→remember       | `orchestrate.start` | Tool execution loop     |
| L3  | `danger_response` | assess_safety                                       | `amygdala.alert`    | Emergency safety loop   |
| L4  | `maintenance`     | decay→cleanup_orphans                               | `heartbeat.tick`    | Loop B: homeostasis     |
| L5  | `diagnostic`      | (empty)                                             | (manual)            | Health check            |

### 6.2 CatSelf Default Loops (3) — Self-Awareness Growth

CatSelf provides three prefab default loops, imperative orchestration (not declarative Loop):

```
★ Inner Loop: Single-Cat Self-Evolution
  before_act(freeze snapshot) → action → after_act(scribble) → PinealGland.trigger_if() → fuse_to_self → Cortex/Metacognition

★ Outer Loop: Collective Intelligence Fusion
  ScribblePad → PinealGland.trigger_if(on_full/on_timer) → fuse_to_colony → SharedStorage → other cats
```

| Loop           | Flow                                         | Fusion Trigger                 | Description                    |
| -------------- | -------------------------------------------- | ------------------------------ | ------------------------------ |
| `conversation` | read self→chat→reply→scribble→reflect        | `on_event("conversation_end")` | Most common — evolve in dialog |
| `task`         | read self→analyze→execute→observe→scribble   | `on_full(50)`                  | Task-driven evolution          |
| `learn`        | read self→blind spot→explore→verify→scribble | `trigger()` immediate          | Curiosity-driven learning      |

---

## VII. Reflex Catalog (2)

Reflex = trigger (match condition) + path (organ sequence) + stages (optional).

### R1 — text_dialogue

```
trigger:     modality == "text"
path:        EARS → THALAMUS → BRAINSTEM → CEREBRUM → CEREBELLUM → MOUTH
hops:        5
description: Standard text dialogue full path
```

### R2 — danger

```
trigger:     content matches danger pattern
path:        EARS → THALAMUS → AMYGDALA → MOUTH (bypass brain!)
hops:        3
description: Amygdala emergency reflex — danger detected → output directly, no reasoning
```

---

## VIII. LoopSequence (1)

| #   | Name                | Loop Sequence            | Mode       | Description                      |
| --- | ------------------- | ------------------------ | ---------- | -------------------------------- |
| LS1 | `daily_maintenance` | maintenance → diagnostic | sequential | Daily maintain → check, in order |

---

## IX. Presets Catalog

### Keyword Presets (3)

| Preset         | Stop Words   | Commands | Danger Rules | Description      |
| -------------- | ------------ | -------- | ------------ | ---------------- |
| `KW_EN`        | 70 English   | 28       | 8 regex      | English base     |
| `KW_ZH`        | 70 Chinese   | 36       | 9 regex      | Chinese base     |
| `KW_BILINGUAL` | zh+en merged | 64       | 17 regex     | Bilingual merged |

### Prompt Presets (2)

| Preset           | Templates    | Description     |
| ---------------- | ------------ | --------------- |
| `PROMPT_DEFAULT` | 7 route      | Default English |
| `PROMPT_ZH`      | 7 route (CN) | Default Chinese |

---

## X. Quick Reference

```python
from meowcat import create_cat, ImplementationStyle
from meowcat.defaults import KW_BILINGUAL, PROMPT_ZH

# Renovated cat (default, 20 organs pre-furnished)
cat = create_cat("bot", cerebrum=MyCerebrum())

# Renovated + bilingual + Chinese prompts
cat = create_cat("bot", cerebrum=MyLLM(), keyword=KW_BILINGUAL, prompt=PROMPT_ZH)

# Noop cat (all bare stubs)
cat = create_cat("bot", cerebrum=MyLLM(), renovated=False)

# Mixed: renovated but amygdala bare
cat = create_cat("bot", cerebrum=MyLLM(), bare_organs={"amygdala"})

# Check plug style per organ
print(cat.organ("brain", "amygdala").impl_style)  # ImplementationStyle.ALGORITHM

# Path
await cat.path_registry.run("locate", query="weather")
await cat.path_registry.run("deep_reason", prompt="Why is the sky blue?")

# Chain
await cat.chain_registry.run("full_reasoning", prompt="...")
await cat.chain_registry.run("maintenance")

# Loop
await cat.run_loop("conversation", message="Hello!")
await cat.run_loop("maintenance")
await cat.run_loopseq("daily_maintenance")
```

---

## XI. File Index

| Concept                  | File                                                                        |
| ------------------------ | --------------------------------------------------------------------------- |
| Public API (lazy)        | `meowcat/__init__.py` + `meowcat/_exports.py`                               |
| Organ coordinates        | `meowcat/anatomy.py`                                                        |
| Organ specs (slots)      | `meowcat/biology.py`                                                        |
| Organ role descriptions  | `meowcat/organ_roles.py`                                                    |
| Noop impls (plugs)       | `meowcat/defaults/organs.py`                                                |
| Renovated impls          | `meowcat/defaults/renovated.py`                                             |
| Keyword & prompt presets | `meowcat/defaults/presets.py`                                               |
| Factory function         | `meowcat/defaults/factory.py`                                               |
| Tool abstractions        | `meowcat/tools/` (tool/skill/paws/matcher)                                  |
| Tool batteries (plus)    | `meowcat/plus/` (tools/browser/mcp/chroma/skill/gateway)                    |
| Storage ref impls        | `meowcat/defaults/stores.py`                                                |
| Path                     | `meowcat/path.py`                                                           |
| Chain                    | `meowcat/chain.py`                                                          |
| Loop                     | `meowcat/loops.py`                                                          |
| Reflex                   | `meowcat/reflex.py`                                                         |
| Wiring                   | `meowcat/wiring.py`                                                         |
| Nervous system           | `meowcat/nervous.py` (signal + circuit breaker)                             |
| Middleware               | `meowcat/middleware.py`                                                     |
| Event payload types      | `meowcat/events_payloads.py` (v1.2.18)                                      |
| Telemetry                | `meowcat/telemetry.py` — Tracer + Metrics (v1.2.21)                         |
| Plug style enum          | `meowcat/anatomy.py` (ImplementationStyle)                                  |
| Biology subsystem        | `meowcat/biology/` (cat_self/pineal_gland/cortex...)                        |
| Colony container         | `meowcat/colony/`                                                           |
| Worker / Scheduler       | `meowcat/worker/` (v1.2.22: +WorkerScheduler)                               |
| Gateway I/O              | `meowcat/gateway/` (Protocol) + `meowcat/plus/gateway/` (adapters, v1.2.22) |
