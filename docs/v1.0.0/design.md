# meowcat v1.0.0 — 设计

> 本版本的主题是「独立发布就绪」—— 版本解耦、API 清理、类型标记补齐。

## 核心决策

### 1. 版本号独立

**决策**: meowcat 从 1.0.0 起独立于 meowagent 版本号。

**理由**:

- meowcat 是独立可发布的 PyPI 包，应有自己的语义版本
- 历史联动导致 meowcat 版本号被 meowagent 拖着走，发布节奏不匹配
- meowcat 的 breaking change 与 meowagent 无关，反之亦然

**实现**: `meowcat/__init__.py` 从 `meowcat/pyproject.toml` 读取版本号（由 `parent.parent` 改为 `parent`）

### 2. requires-python 下调

**决策**: `>=3.12` → `>=3.10`

**理由**:

- 依赖仅 `pydantic>=2.0` + `anyio>=4.0`，均支持 3.10+
- 作为框架层应覆盖更广的 Python 用户群
- meowagent 要求 `>=3.10`，框架不应比应用更苛刻

### 3. Pathways 移除公开导出

**决策**: 从 `__init__.py` 的 `__all__` 中移除，但保留 `pathways.py` 文件。

**理由**:

- v0.5.27 起已废弃，跨越 30+ 子版本
- 1.0.0 是清理的好时机
- 保留文件使 `from meowcat.pathways import Pathways` 仍可用（向后兼容）

### 4. PEP 561 类型标记

**决策**: 新增 `meowcat/py.typed` 空文件。

**理由**: meowcat 大量使用 Protocol 类型注解，没有此标记等于自废武功——mypy/pyright 不会对该包做类型检查。

## 数据流/接口变更

无 breaking API 变更。`from meowcat import Pathways` 将报 `ImportError`（因 `__init__.py` 不再 re-export），但 `from meowcat.pathways import Pathways` 仍可用。

## 未解决问题

- Colony（猫群）架构已设计但未实现，计划 v1.1.0
- `protocols.py` (622行) 和 `assembly.py` (551行) 超过 500 行限制，暂不拆分（拆分风险大于收益）
- `pathways.py` 将在 v2.0.0 彻底移除
