# meowcat v1.0.2 — 任务拆解

## 任务清单

### T1: Colony 类实现

| 项     | 文件               | 内容                                              |
| ------ | ------------------ | ------------------------------------------------- |
| 新文件 | `meowcat/colony.py` | Colony 类，含 create_cat/register/signal_between 等 |

**验收**: `from meowcat import Colony` 可用 ✓

### T2: 跨猫 wiring 隔离

| 项          | 文件               | 内容                                    |
| ----------- | ------------------ | --------------------------------------- |
| cross_wiring | `meowcat/colony.py` | allow_cross/forbid_cross/_assert_cross_allowed |

**验收**: 禁止的跨猫边抛 `IllegalNeuralPathError` ✓

### T3: SharedStorage 增强 + 隔离

| 项          | 文件                          | 内容                              |
| ----------- | ----------------------------- | --------------------------------- |
| list_keys   | `meowcat/defaults/stores.py`  | `InMemorySharedStore.list_keys()` |
| watch       | `meowcat/defaults/stores.py`  | `InMemorySharedStore.watch()`    |
| 命名空间隔离 | `meowcat/colony.py`           | `storage_*` 方法 `cat_id/` 前缀   |

**验收**: 不同猫的 `storage_get` 各自隔离 ✓

### T4: 公开 API

| 项     | 文件                  | 内容                |
| ------ | --------------------- | ------------------- |
| import | `meowcat/__init__.py` | `from meowcat.colony import Colony` |
| __all__ | `meowcat/__init__.py` | 加入 `"Colony"`    |

**验收**: `"Colony" in meowcat.__all__` ✓

### T5: 测试

| 项        | 文件                                  | 内容       |
| --------- | ------------------------------------- | ---------- |
| 测试文件  | `meowcat/tests/test_v102_colony.py`   | 25 条测试  |

**验收**: 25 passed ✓

## 进度

| 任务 | 状态 |
| ---- | ---- |
| T1   | ✅   |
| T2   | ✅   |
| T3   | ✅   |
| T4   | ✅   |
| T5   | ✅   |
