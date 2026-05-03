# v1.0.5 任务跟踪

> 纯重构，不涉及功能变更。

## 任务列表

| #   | 任务                                                 | 状态            |
| --- | ---------------------------------------------------- | --------------- |
| T1  | 创建 `meowcat/protocols_storage.py`（存储协议）      | ✅              |
| T2  | 创建 `meowcat/protocols_brain.py`（脑区+LLM+Growth） | ✅              |
| T3  | 创建 `meowcat/protocols_sense.py`（感官协议）        | ✅              |
| T4  | 修改 `meowcat/protocols.py`（re-export 保持兼容）    | ✅              |
| T5  | 确认 `meowcat/__init__.py` 无需变更                  | ✅              |
| T6  | 全量测试通过                                         | ✅ (567 passed) |
| T7  | 创建版本文档                                         | ✅              |

## 验收清单

- [x] `protocols_brain.py` ≤ 500 行 (288)
- [x] `protocols_sense.py` ≤ 500 行 (92)
- [x] `protocols_storage.py` ≤ 500 行 (83)
- [x] `protocols.py` ≤ 500 行 (229)
- [x] `from meowcat import Diagnosable, OrganProtocol, ...` 全部 25 个可用
- [x] `from meowcat.protocols import *` 全部 25 个可用
- [x] 全量测试 567 passed, 0 failed
