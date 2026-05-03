# meowcat v1.0.4 — 多 Loop 编排 (LoopSequence)

> 在四层组合模型中新增第五层：`Path → Chain → Loop → LoopSequence`

## 概述

v1.0.4 在已有四层编排模型（Path → Chain → Loop）之上引入第五层 **LoopSequence**，
允许将多个 Loop 组合为顺序或事件驱动的元闭环。

## 新增内容

| 新增                    | 文件                  | 说明                                    |
| ----------------------- | --------------------- | --------------------------------------- |
| `LoopSequence`          | `meowcat/loops.py`    | 元闭环 dataclass（frozen）              |
| `LoopSequenceRegistry`  | `meowcat/loops.py`    | 元闭环注册中心（register/get/list/run） |
| `DAILY_MAINTENANCE_SEQ` | `meowcat/loops.py`    | 内置日常维护元闭环                      |
| `cat.loopseq_registry`  | `meowcat/assembly.py` | CatBase 集成                            |
| `cat.run_loopseq()`     | `meowcat/assembly.py` | 快捷执行方法                            |

## API

```python
from meowcat import LoopSequence, LoopSequenceRegistry, DAILY_MAINTENANCE_SEQ

# 定义元闭环
seq = LoopSequence(
    "my_sequence",
    description="My custom sequence",
    loops=("maintenance", "diagnostic"),
    mode="sequential",    # "sequential" | "event_driven"
    stop_on_error=True,
)

# 注册并执行
cat.loopseq_registry.register(seq)
result = await cat.run_loopseq("my_sequence")

# 内置
result = await cat.run_loopseq("daily_maintenance")
```

## 模式

- **sequential**: 按顺序执行 Loop，前一步结果传给下一步
- **event_driven**: 所有 Loop 并发执行，各自获得相同初始输入
- **stop_on_error**: True 时失败即停止，False 时跳过失败继续

## 子版本进度

| 子版本 | 主题         | 状态 |
| ------ | ------------ | ---- |
| —      | LoopSequence | ✅   |

## 测试

- 新增 26 条测试 (`test_v104_loopseq.py`)
- 全量回归: 566 passed, 1 failed（性能测试 CI 波动，无关）
