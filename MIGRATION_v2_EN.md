# MeowCat v1.x → v2.0 Migration Guide

> This document lists all removals and changes in v2.0, for meowagent and other application-layer adapters.
> v2.0 is a breaking change release.

---

## 一、Deleted Files (remove from imports)

| File                                | Lines     | Replacement / Notes                           |
| ----------------------------------- | --------- | --------------------------------------------- |
| `meowcat/colony/delegation.py`      | 233       | Removed (zero usage)                          |
| `meowcat/colony/federation.py`      | 238       | Removed (framework doesn't handle cross-host) |
| `meowcat/colony/transports.py`      | 401       | Removed (framework doesn't handle networking) |
| `meowcat/colony/registry.py`        | 188       | Removed (zero usage)                          |
| `meowcat/colony/llm_shelf.py`       | 115       | Removed (merged into models_shelf.py)         |
| `meowcat/defaults/renovated/`       | 21+ files | Merged into defaults/organs/                  |
| `meowcat/cli/`                      | 6 files   | Moved to application layer                    |
| `meowcat/plus/gateway/`             | 6 files   | Moved to application layer (adapters)         |
| `meowcat/plus/tools/`               | 6 files   | Moved to application layer                    |
| `meowcat/plus/browser.py`           | 251       | Moved to application layer                    |
| `meowcat/plus/mcp_client.py`        | 361       | Moved to application layer                    |
| `meowcat/biology/fusion_cycle.py`   | 115       | Merged into PinealGland                       |
| `meowcat/biology/metacognition.py`  | 186       | Merged into CatSelf                           |
| `meowcat/biology/roles.py`          | 228       | Merged into growth.py                         |
| `meowcat/biology/cat_self_loops.py` | 367       | Rewritten (3 types → 1 type)                  |

---

## 二、Removed Classes / Functions

| v1.x                                     | v2.0 Replacement                      |
| ---------------------------------------- | ------------------------------------- |
| `SkillOrgan`                             | `AgentOrgan`                          |
| `ImplementationStyle.RULE`               | `ImplementationStyle.ALGORITHM`       |
| `ImplementationStyle.HYBRID`             | Removed (enum not needed)             |
| `create_cat(renovated=True/False)` param | Removed (single Default organ set)    |
| `RENOVATED_ORGAN_MAP`                    | Removed                               |
| `Colony.ns_append()`                     | Removed                               |
| `Colony.ns_search()`                     | Removed                               |
| `Colony.ns_clear()`                      | Removed                               |
| `Colony.ns_list_keys()`                  | Removed                               |
| `ColonyRules.check()`                    | Removed                               |
| `ColonyRules.on_check` hook              | Removed                               |
| `Colony.broadcast_request()`             | Removed                               |
| `Colony.receive_external()`              | Removed                               |
| `spawn_cat()`                            | Removed                               |
| `HttpAdapter`                            | Moved to application layer            |
| `WsAdapter`                              | Moved to application layer            |
| `CliAdapter`                             | Moved to application layer            |
| `IpcAdapter`                             | Moved to application layer            |
| `WebhookAdapter`                         | Moved to application layer            |
| `DefaultConversationLoop`                | `ReflectionLoop(mode="conversation")` |
| `DefaultTaskLoop`                        | `ReflectionLoop(mode="task")`         |
| `DefaultLearnLoop`                       | `ReflectionLoop(mode="learn")`        |
| `FusionCycle.on_full()`                  | `PinealGland.on_full()`               |
| `FusionCycle.on_timer()`                 | `PinealGland.on_timer()`              |
| `FusionCycle.on_event()`                 | `PinealGland.on_event()`              |
| `Metacognition` standalone class         | Built into `CatSelf`                  |

---

## 三、API Signature Changes

| v1.x                                           | v2.0                                                |
| ---------------------------------------------- | --------------------------------------------------- |
| `create_cat(name, cerebrum, renovated=True)`   | `create_cat(name, cerebrum)`                        |
| `cat.path_registry.run("deep_reason")`         | Internal API, prefer `cat.run_loop("conversation")` |
| `cat.chain_registry.run("conversation_chain")` | `cat.run_loop("conversation")`                      |
| `SkillOrgan(skill)`                            | `AgentOrgan(skill)`                                 |
| `Colony("name").llm_shelf`                     | `Colony("name").model_shelf` (models_shelf.py)      |
| `Colony("name").ns_get("rules/", key)`         | namespace 6→3, `rules/` no longer available         |
| `Colony("name").ns_get("growth/", key)`        | Merged into ColonyGrowth                            |

---

## 四、New APIs

```python
# KnowledgeTree (v2.0)
from meowcat.tree import TreeNode

cat.hippocampus.get_tree(entity_id: str) → TreeNode | None
cat.hippocampus.build_tree(entity_id: str, root: TreeNode) → int
cat.hippocampus.delete_tree(entity_id: str) → None
cat.hippocampus.search_tree(entity_id: str, keyword: str, limit: int = 5) → list[TreeNode]
cat.hippocampus.query_subtree(entity_id: str, node_id: str, max_depth: int = 2) → list[TreeNode]
cat.hippocampus.check_tree_stale(entity_id: str) → list[str]

# Unified ReflectionLoop
from meowcat.biology.cat_self_loops import ReflectionLoop

loop = ReflectionLoop(mode="conversation", fusion_trigger="event")
loop = ReflectionLoop(mode="task", fusion_trigger="full:50")
loop = ReflectionLoop(mode="learn", fusion_trigger="immediate")
```

---

## 五、Concept Changes

| v1.x                                | v2.0                                           |
| ----------------------------------- | ---------------------------------------------- |
| Noop / Renovated two sets           | Single Default organ set                       |
| Path/Chain public API               | Internal API (still usable via `cat.signal()`) |
| 4 ImplementationStyle types         | 2 (MODEL/ALGORITHM)                            |
| conversation_chain 6 steps          | 3 steps                                        |
| Colony namespace 6 areas            | 3 (owner/knowledge/cats)                       |
| CLI in framework                    | CLI in application layer                       |
| 8 built-in tools in framework       | Tools in application layer                     |
| plus/gateway/ adapters in framework | Adapters in application layer                  |

---

## 六、Adaptation Checklist (meowagent)

- [ ] Remove imports from `delegation/federation/transports/registry/llm_shelf`
- [ ] Replace all `Noop*/Renovated*` imports with new Default classes
- [ ] `create_cat(renovated=...)` → `create_cat(...)`
- [ ] `SkillOrgan` → `AgentOrgan`
- [ ] `ImplementationStyle.RULE/HYBRID` → `ALGORITHM/MODEL`
- [ ] `cat.path_registry.run()` → `cat.run_loop()` or `cat.signal()`
- [ ] `FusionCycle.*` → `PinealGland.*`
- [ ] `Metacognition` → `CatSelf`
- [ ] Move CLI logic from framework import to local code
- [ ] Move plus/tools/ implementations to application layer
- [ ] Move plus/gateway/ adapters to application layer
- [ ] `DefaultConversationLoop` → `ReflectionLoop`
- [ ] `Colony.ns_get("rules/", ...)` → Remove
- [ ] `Colony.llm_shelf` → `Colony.model_shelf`
- [ ] Integrate KnowledgeTree API (optional)
