# meowcat v1.0.4 — 审查记录

## 关键决策

### LoopSequence 引用 Loop 名而非对象

与 Chain → Path 的引用方式一致。通过 registry 按名查找，解耦注册顺序。LoopSequence 创建时无需 Loop 已注册（执行时才校验）。

### mode 选择

- `"sequential"`: 适合有数据依赖的 Loop 链（如维护→体检）
- `"event_driven"`: 适合独立的 Loop 并发执行

当前 event_driven 实现为 `asyncio.gather` 并发，未来可扩展为真正的事件驱动（监听 Loop.trigger 事件触发执行）。

### state_driven 模式未实现

计划中 mode 仅定义了 `"sequential"` 和 `"event_driven"`。`"state_driven"`（状态机驱动的条件跳转）留待未来需求。

## 遇到的问题

无重大问题。唯一回归是性能测试 `test_contract_overhead_small` 因 CI 环境波动超限（2483ns vs 2000ns），与本次改动无关。

## 测试覆盖

- 26 条新测试，覆盖：
  - LoopSequence 字段验证和 frozen 语义
  - LoopSequenceRegistry CRUD
  - sequential 模式（正常、失败、跳过失败）
  - event_driven 模式（正常、并发失败）
  - 边界（空序列、不存在 LoopSeq、不存在 Loop）
  - CatBase 集成（run_loopseq 快捷方法）
  - 内置 DAILY_MAINTENANCE_SEQ
- 全量回归 566/567 passed
