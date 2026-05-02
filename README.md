# meowcat 🐱

> **An agent framework built on the biological blueprint of a cat.**
>
> Framework layer: protocols, wiring, reflexes, tools — everything a cat needs.
> `pip install meowcat` gives you a complete agent framework. Bring your own LLM.

## Quick Start (5 lines)

```python
from meowcat import create_cat, MEMORY_SEARCH_CHAIN, CONVERSATION_LOOP

class MyBrain:
    name = "cerebrum"
    async def generate(self, prompt, **kw) -> str:
        return f"Meow! You said: {prompt[:50]}"

cat = create_cat("chat-cat", cerebrum=MyBrain())
await cat.chain_registry.run("memory_search", query="hello")
await cat.run_loop("conversation", message="Hello, cat!")
```

## Four-Layer Architecture

meowcat builds agents from atomic to composite:

```
  Organ (器官)  →  Path (路径)   →  Chain (链路)  →  Loop (闭环)
  single unit      one signal       named Path        Chain + trigger
                                   sequence           + exit event
```

| Layer | Module       | Concept                                                     |
| ----- | ------------ | ----------------------------------------------------------- |
| Organ | `biology.py` | 20 default organs (THALAMUS, HIPPOCAMPUS, CEREBRUM...)      |
| Path  | `path.py`    | 25 builtin atomic paths ("locate", "deep_reason"...)        |
| Chain | `chain.py`   | 5 builtin chains (MEMORY_SEARCH_CHAIN, FULL_REASONING...)   |
| Loop  | `loops.py`   | 5 default loops (CONVERSATION_LOOP, TOOL_EXECUTION_LOOP...) |

```python
from meowcat import (
    Path, MEMORY_SEARCH_CHAIN, CONVERSATION_LOOP,  # four-layer API
    CatBase, create_cat,  # skeleton
)

# Path: atomic inter-organ signal
cat.path_registry.run("locate", query="weather")   # THALAMUS → HIPPOCAMPUS

# Chain: named Path sequence
cat.chain_registry.run("full_reasoning", prompt="Why is the sky blue?")

# Loop: Chain + lifecycle triggers
await cat.run_loop("conversation", message="Hello!")
```

## Core Concepts

| Concept     | Module              | What it does                                           |
| ----------- | ------------------- | ------------------------------------------------------ |
| Protocol    | `meowcat.protocols` | Duck-typed organ blueprints (Cerebrum, Ears, Paws...)  |
| Wiring      | `meowcat.wiring`    | Neural connectivity table — who can talk to whom       |
| Signal      | `meowcat.nervous`   | Wiring-validated inter-organ calls (`signal()`)        |
| Reflex      | `meowcat.reflex`    | Stimulus → response chains (trigger + path)            |
| Stethoscope | `meowcat.diagnose`  | Full-body diagnostic probe (`probe_all()` / `probe()`) |
| Needle      | `meowcat.inject`    | Bypass-wiring write (debug/admin only)                 |
| Tools       | `meowcat.tools`     | Tool/Skill/PawsEngine — every cat has claws            |

## Install

```bash
pip install meowcat
```

Dependencies: `pydantic>=2.0` + `anyio>=4.0`. Zero other hard deps.

## Architecture

`meowcat` is the **framework layer** — pure cat anatomy. Application logic lives in `meowagent` (the cat factory above this layer).

Read the full architecture: [docs/架构/00-meowcat-框架架构.md](../docs/架构/00-meowcat-框架架构.md)

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

## License

MIT
