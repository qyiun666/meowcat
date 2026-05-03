# v1.0.9 任务拆解 + 进度跟踪

> 来源: `.qoder/plans/meowcat深版分析_版本拆分计划.md` v1.0.9 章节

## 任务清单

### ✅ CatBase 门面方法: assembly.py

- [x] `search_memory(query, limit=5)` — chain_registry.run("memory_search", msg=query, session_id=cat_id)
- [x] `memory_stats()` — signal(BRAINSTEM, HIPPOCAMPUS, "stats")
- [x] `run_maintenance(country_code=None)` — run_loopseq("daily_maintenance")

### ✅ Colony 别名: colony.py

- [x] `adopt(cat)` → register(cat)
- [x] `release(cat_id)` → unregister(cat_id)

### ✅ 测试: test_v109_facade.py (25 tests)

- [x] TestSearchMemory (3): empty / with_limit / returns_dict
- [x] TestMemoryStats (3): empty / after_episode / returns_dict
- [x] TestRunMaintenance (3): no_country / with_country / missing_seq
- [x] TestColonyAliases (6): registers / removes / nonexistent / multiple / workflow / storage
- [x] TestNewWiringEdges (10): 6 条新增允许边 + 2 条禁止边 + 2 已有边

### ✅ 版本号

- [x] meowcat/pyproject.toml: 1.0.8 → 1.0.9

### ✅ 文档

- [x] docs/meowcat/v1.0.9/README.md
- [x] docs/meowcat/v1.0.9/design.md
- [x] docs/meowcat/v1.0.9/tasks.md（本文件）
- [x] docs/meowcat/v1.0.9/review.md

## 验收清单

- [x] 635 tests passed (0 failures)
- [x] `__version__` 动态读取 pyproject.toml 正确返回 "1.0.9"
- [x] search_memory / memory_stats / run_maintenance 可从 CatBase 调用
- [x] adopt / release 别名行为与 register / unregister 一致
- [x] v1.0.8 wiring 新边集成测试全部通过

## 参数映射修正

| 计划                               | 实际                                  | 原因                                                 |
| ---------------------------------- | ------------------------------------- | ---------------------------------------------------- |
| `run_loop("memory_search")`        | `chain_registry.run("memory_search")` | memory_search 是 Chain 而非 Loop                     |
| `query=query`                      | `msg=query`                           | ThalamusProtocol.locate 签名为 (msg, session_id)     |
| `country_code=country_code` (传入) | 移除传入                              | 维护链 path 间 kwargs 传递会导致参数泄漏到不相关方法 |
| `limit=limit` (传入)               | 移除传入                              | ThalamusProtocol 不接受 limit 参数                   |
