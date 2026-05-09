# MeowCat v1.x → v2.0 迁移指南

> 本文档列出 v2.0 所有删除/变更项，供 meowagent 及其他应用层适配参考。
> v2.0 是不兼容变更版本。

---

## 一、删除的文件（需从 import 中移除）

| 文件                                | 行数     | 替代/说明                        |
| ----------------------------------- | -------- | -------------------------------- |
| `meowcat/colony/delegation.py`      | 233      | 删除（零使用）                   |
| `meowcat/colony/federation.py`      | 238      | 删除（框架不关心跨主机）         |
| `meowcat/colony/transports.py`      | 401      | 删除（框架不关心网络层）         |
| `meowcat/colony/registry.py`        | 188      | 删除（零使用）                   |
| `meowcat/colony/llm_shelf.py`       | 115      | 删除（已合并到 models_shelf.py） |
| `meowcat/defaults/renovated/`       | 21+ 文件 | 合并到 defaults/organs/          |
| `meowcat/cli/`                      | 6 文件   | 移入应用层                       |
| `meowcat/plus/gateway/`             | 6 文件   | 移入应用层（适配器）             |
| `meowcat/plus/tools/`               | 6 文件   | 移入应用层                       |
| `meowcat/plus/browser.py`           | 251      | 移入应用层                       |
| `meowcat/plus/mcp_client.py`        | 361      | 移入应用层                       |
| `meowcat/biology/fusion_cycle.py`   | 115      | 合并到 PinealGland               |
| `meowcat/biology/metacognition.py`  | 186      | 合并到 CatSelf                   |
| `meowcat/biology/roles.py`          | 228      | 合并到 growth.py                 |
| `meowcat/biology/cat_self_loops.py` | 367      | 重写（3 类 → 1 类）              |

---

## 二、删除的类/函数

| v1.x                                    | v2.0 替代                             |
| --------------------------------------- | ------------------------------------- |
| `SkillOrgan`                            | `AgentOrgan`                          |
| `ImplementationStyle.RULE`              | `ImplementationStyle.ALGORITHM`       |
| `ImplementationStyle.HYBRID`            | 删除（不需要独立枚举）                |
| `create_cat(renovated=True/False)` 参数 | 删除（只有一套 Default）              |
| `RENOVATED_ORGAN_MAP`                   | 删除                                  |
| `Colony.ns_append()`                    | 删除                                  |
| `Colony.ns_search()`                    | 删除                                  |
| `Colony.ns_clear()`                     | 删除                                  |
| `Colony.ns_list_keys()`                 | 删除                                  |
| `ColonyRules.check()`                   | 删除                                  |
| `ColonyRules.on_check` hook             | 删除                                  |
| `Colony.broadcast_request()`            | 删除                                  |
| `Colony.receive_external()`             | 删除                                  |
| `spawn_cat()`                           | 删除                                  |
| `HttpAdapter`                           | 移入应用层                            |
| `WsAdapter`                             | 移入应用层                            |
| `CliAdapter`                            | 移入应用层                            |
| `IpcAdapter`                            | 移入应用层                            |
| `WebhookAdapter`                        | 移入应用层                            |
| `DefaultConversationLoop`               | `ReflectionLoop(mode="conversation")` |
| `DefaultTaskLoop`                       | `ReflectionLoop(mode="task")`         |
| `DefaultLearnLoop`                      | `ReflectionLoop(mode="learn")`        |
| `FusionCycle.on_full()`                 | `PinealGland.on_full()`               |
| `FusionCycle.on_timer()`                | `PinealGland.on_timer()`              |
| `FusionCycle.on_event()`                | `PinealGland.on_event()`              |
| `Metacognition` 独立类                  | `CatSelf` 内置方法                    |

---

## 三、API 签名变更

| v1.x                                           | v2.0                                            |
| ---------------------------------------------- | ----------------------------------------------- |
| `create_cat(name, cerebrum, renovated=True)`   | `create_cat(name, cerebrum)`                    |
| `cat.path_registry.run("deep_reason")`         | 内部 API，建议用 `cat.run_loop("conversation")` |
| `cat.chain_registry.run("conversation_chain")` | `cat.run_loop("conversation")`                  |
| `SkillOrgan(skill)`                            | `AgentOrgan(skill)`                             |
| `Colony("name").llm_shelf`                     | `Colony("name").model_shelf` (models_shelf.py)  |
| `Colony("name").ns_get("rules/", key)`         | namespace 6→3，rules/ 不再可用                  |
| `Colony("name").ns_get("growth/", key)`        | 合并到 ColonyGrowth                             |

---

## 四、新增 API

```python
# 树 (KnowledgeTree)
from meowcat.tree import TreeNode

cat.hippocampus.get_tree(entity_id: str) → TreeNode | None
cat.hippocampus.build_tree(entity_id: str, root: TreeNode) → int
cat.hippocampus.delete_tree(entity_id: str) → None
cat.hippocampus.search_tree(entity_id: str, keyword: str, limit: int = 5) → list[TreeNode]
cat.hippocampus.query_subtree(entity_id: str, node_id: str, max_depth: int = 2) → list[TreeNode]
cat.hippocampus.check_tree_stale(entity_id: str) → list[str]

# 统一房间闭环
from meowcat.biology.cat_self_loops import ReflectionLoop

loop = ReflectionLoop(mode="conversation", fusion_trigger="event")
loop = ReflectionLoop(mode="task", fusion_trigger="full:50")
loop = ReflectionLoop(mode="learn", fusion_trigger="immediate")
```

---

## 五、概念变更

| v1.x                         | v2.0                                     |
| ---------------------------- | ---------------------------------------- |
| Noop / Renovated 两套器官    | 一套 Default 器官                        |
| Path/Chain 公开 API          | 内部 API（仍可用 cat.signal() 直调器官） |
| 4 种 ImplementationStyle     | 2 种 (MODEL/ALGORITHM)                   |
| conversation_chain 6 步      | 3 步                                     |
| Colony namespace 6 个        | 3 个 (owner/knowledge/cats)              |
| CLI 在框架内                 | CLI 在应用层                             |
| 8 内置工具在框架内           | 工具在应用层                             |
| plus/gateway/ 适配器在框架内 | 适配器在应用层                           |

---

## 六、适配检查清单（meowagent）

- [ ] 移除对 `delegation/federation/transports/registry/llm_shelf` 的 import
- [ ] 将所有 `Noop*/Renovated*` import 改为新的 Default 类
- [ ] `create_cat(renovated=...)` → `create_cat(...)`
- [ ] `SkillOrgan` → `AgentOrgan`
- [ ] `ImplementationStyle.RULE/HYBRID` → `ALGORITHM/MODEL`
- [ ] `cat.path_registry.run()` → `cat.run_loop()` 或 `cat.signal()`
- [ ] `FusionCycle.*` → `PinealGland.*`
- [ ] `Metacognition` → `CatSelf`
- [ ] 将 CLI 逻辑从框架引用改为本地代码
- [ ] 将 plus/tools/ 工具实现迁移到应用层
- [ ] 将 plus/gateway/ 适配器迁移到应用层
- [ ] `DefaultConversationLoop` → `ReflectionLoop`
- [ ] `Colony.ns_get("rules/", ...)` → 移除
- [ ] `Colony.llm_shelf` → `Colony.model_shelf`
- [ ] 接入 KnowledgeTree API（可选）
