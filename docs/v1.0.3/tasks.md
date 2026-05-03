# meowcat v1.0.3 — 任务拆解

## Part A: Wiring 可视化

### T1: `render_wiring` 函数

| 项   | 文件                  | 内容                                 |
| ---- | --------------------- | ------------------------------------ |
| 扩展 | `meowcat/diagnose.py` | `render_wiring(wiring, format)` 函数 |

**验收**: 空 wiring / 完整 wiring / 含禁止边 / mermaid + dot 格式正确

### T2: CatBase 快捷方法

| 项   | 文件                  | 内容                          |
| ---- | --------------------- | ----------------------------- |
| 扩展 | `meowcat/assembly.py` | `wiring_diagram(format)` 方法 |

**验收**: `cat.wiring_diagram()` 返回有效字符串

## Part B: Chain 事务性

### T3: Chain 数据类扩展

| 项   | 文件               | 内容                               |
| ---- | ------------------ | ---------------------------------- |
| 修改 | `meowcat/chain.py` | `Chain` 新增 `rollback_paths` 字段 |

**验收**: `Chain("x", ("a",), rollback_paths=("r",))` 可创建

### T4: ChainRegistry.run() 事务包装

| 项   | 文件               | 内容                             |
| ---- | ------------------ | -------------------------------- |
| 修改 | `meowcat/chain.py` | `run()` 新增 try/except 回滚逻辑 |

**验收**: 成功不触发 / 失败逆序回滚 / 空 rollback 无影响 / 回滚异常不掩盖原异常

### T5: 测试

| 项       | 文件                                        | 内容      |
| -------- | ------------------------------------------- | --------- |
| 测试文件 | `meowcat/tests/test_v103_wiring_viz.py`     | ~6 条测试 |
| 测试文件 | `meowcat/tests/test_v103_chain_rollback.py` | ~7 条测试 |

**验收**: 新增测试全通过，回归全绿

## 进度

| 任务 | 状态 |
| ---- | ---- |
| T1   | ✅   |
| T2   | ✅   |
| T3   | ✅   |
| T4   | ✅   |
| T5   | ✅   |
