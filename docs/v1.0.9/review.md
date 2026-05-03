# v1.0.9 审查记录

> 审查日期: 2026-05-02 | 审查者: AI

## 关键决策

### 1. search_memory 使用 Chain 而非 Loop

**决策**: `chain_registry.run("memory_search")` 替代计划中的 `run_loop("memory_search")`。

**原因**: `memory_search` 是以 Chain 注册的（非 Loop）。Loop 需要 trigger/exit 事件，而 CLI 门面只需直接执行。使用 Chain 更简洁，且无需注册新 Loop。

### 2. 参数映射 query → msg

**决策**: facade 接收 `query`（面向用户），内部转为 `msg`（匹配 ThalamusProtocol）。

**原因**: ThalamusProtocol.locate 签名为 `(msg: str, session_id: str)`。直接传 `query` 会导致 TypeError。

### 3. run_maintenance 不传 country_code

**决策**: `country_code` 保留在 facade 签名中（面向未来），但不传入 chain。

**原因**: 维护链 `decay→cleanup_orphans` 的 chain 执行会将前一步返回值作为 kwargs 传给下一步。传入 `country_code` 会导致 `NoopHippocampus.decay(country_code=...)` TypeError。框架层当前不需要此参数。

### 4. search_memory 不传 limit

**决策**: `limit` 参数保留在 facade 签名中但不传入 chain。

**原因**: 同上述，ThalamusProtocol 不接受 `limit`。应用层的 Thalamus 实现可自行处理分页。

## 遇到的问题

| 问题                                                        | 解决方案                                                       |
| ----------------------------------------------------------- | -------------------------------------------------------------- |
| `locate` Path 是 THALAMUS 自环，非 THALAMUS→HIPPOCAMPUS     | 测试 mock 使用 NoopThalamus（自带 locate）                     |
| 维护链 kwargs 传递：decay 结果 → cleanup_orphan_connections | mock 海马体接受 \*\*kwargs（与 v1.0.4 测试模式一致）           |
| EARS→THALAMUS signal("hear") 被方法级权限拒绝               | 改用 path_registry 验证 Path 存在性                            |
| NoopCortex 无 `record` 方法（生长器官无 Noop 实现）         | 创建 \_MockGrowth 类                                           |
| DAILY_MAINTENANCE_SEQ 未注册到 loopseq_registry             | 测试中手动注册；框架层 CatBase.**init** 未自动注册（已知设计） |

## 改动总结

```
 meowcat/meowcat/assembly.py       | +49  (search_memory + memory_stats + run_maintenance)
 meowcat/meowcat/colony.py         | +21  (adopt + release)
 meowcat/pyproject.toml            |   1  (version bump)
 meowcat/tests/test_v109_facade.py | +350 (25 new tests)
 docs/meowcat/v1.0.9/              |   4  (README + design + tasks + review)
```

## 三版总览

| 版本   | 测试数 |
| ------ | ------ |
| v1.0.6 | 567    |
| v1.0.8 | 610    |
| v1.0.9 | 635    |

三个阶段共 +68 tests，零回归。
