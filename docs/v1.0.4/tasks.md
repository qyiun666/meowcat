# meowcat v1.0.4 — 任务拆解

## T1: LoopSequence 数据类

| 项   | 文件               | 内容                                                          |
| ---- | ------------------ | ------------------------------------------------------------- |
| 修改 | `meowcat/loops.py` | `LoopSequence` dataclass（frozen）+ `__post_init__` mode 校验 |

**验收**: `LoopSequence("x", mode="sequential")` 可创建；非法 mode 抛 ValueError；frozen 不可变

## T2: LoopSequenceRegistry

| 项   | 文件               | 内容                                                         |
| ---- | ------------------ | ------------------------------------------------------------ |
| 修改 | `meowcat/loops.py` | `LoopSequenceRegistry` dataclass + register/get/list_all/run |

**验收**: CRUD 正常；sequential + event_driven 两种 mode；stop_on_error 语义正确

## T3: CatBase 集成

| 项   | 文件                  | 内容                                                                 |
| ---- | --------------------- | -------------------------------------------------------------------- |
| 修改 | `meowcat/assembly.py` | `loopseq_registry` 初始化 + `run_loopseq()` 方法 + `_ALWAYS_ALLOWED` |

**验收**: `cat.loopseq_registry` 可用；`cat.run_loopseq(name)` 执行

## T4: 内置 LoopSequence

| 项   | 文件               | 内容                                         |
| ---- | ------------------ | -------------------------------------------- |
| 修改 | `meowcat/loops.py` | `DAILY_MAINTENANCE_SEQ` + `BUILTIN_LOOPSEQS` |

**验收**: `DAILY_MAINTENANCE_SEQ.loops == ("maintenance", "diagnostic")`

## T5: 公开 API 注册

| 项   | 文件                  | 内容                                                                       |
| ---- | --------------------- | -------------------------------------------------------------------------- |
| 修改 | `meowcat/__init__.py` | 导入并导出 `LoopSequence`, `LoopSequenceRegistry`, `DAILY_MAINTENANCE_SEQ` |

**验收**: `from meowcat import LoopSequence` 可用

## T6: 测试

| 项       | 文件                                 | 内容      |
| -------- | ------------------------------------ | --------- |
| 测试文件 | `meowcat/tests/test_v104_loopseq.py` | 26 条测试 |

**验收**: 新增测试全通过，回归全绿

## 进度

| 任务 | 状态 |
| ---- | ---- |
| T1   | ✅   |
| T2   | ✅   |
| T3   | ✅   |
| T4   | ✅   |
| T5   | ✅   |
| T6   | ✅   |
