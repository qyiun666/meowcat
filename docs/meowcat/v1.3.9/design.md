# v1.3.9 — 设计文档

> 类型: 代码健康整理 | 零新功能 | 零 API 变更 | 零 meowagent 依赖
> 来源: 综合分析报告 (2026-05-09)

## 1. 背景

综合分析发现 3 类技术债:

1. **12 个文件超过 500 行** G-02 规范上限，最严重的 `colony/__init__.py` 达 971 行
2. **10 处 deprecated 标记** 未清理 (`LLMConfig`, `L6StorageProtocol`, Paws 旧方法等)
3. **v1.3.8 版本文档缺失** — 版本已发布但无 `docs/meowcat/v1.3.8/`

v1.3.9 只做这三件事，不引入任何新功能。

## 2. Deprecated 清理 (T-02)

### 2.1 清理清单

| 文件 | 内容 | 处理方式 |
|------|------|---------|
| `models.py:410` | `LLMConfig = ModelConfig` 别名 | 移除别名行，搜全框架所有 `LLMConfig` 引用改为 `ModelConfig` |
| `protocols_storage.py:59` | `L6StorageProtocol` deprecated | 移除类，搜全框架引用 |
| `protocols_storage.py:107` | `SharedStorageProtocol` deprecated | 保留文件但改 deprecation 为正文说明 |
| `protocols_sense.py:119` | Paws `interact_with_tool` / `run_command` / `touch_file` 标记 deprecated | 搜调用方，确认可安全移除后删除 |
| `adapters/sense.py` | deprecated 标记 | 同步清理 |
| `defaults/organs/voice.py` | deprecated 标记 | 同步清理 |
| `defaults/renovated/brain.py` | deprecated 标记 | 同步清理 |

### 2.2 设计约束

- **不改变任何公共 API 签名**: 只删除已标记 deprecated 的代码路径
- **搜全调用方再删**: 每个 deprecated 项先 `grep_code` 搜引用，确认无调用方或调用方已迁移后再删
- **不影响测试**: 清理后 `pytest tests/` 必须全绿

## 3. 文件拆分 (T-03~T-07)

### 3.1 拆分原则

- **公共 API 不变**: 所有 `from meowcat.colony import Colony` 等导入路径不变
- **内部实现重组**: 源代码移入子模块，原文件改为 `from .submodule import X` 重导出
- **只拆不重构**: 不趁机改逻辑、不改签名、不加功能
- **复杂单类不拆**: `assembly.py` (CatBase), `cat_self.py` (CatSelf) 等单类文件，优先提取 helper 函数而非拆类

### 3.2 各模块拆分方案

#### T-03: colony/__init__.py (971 行)

当前已拆出: `config.py`, `rules.py`, `federation.py`, `registry.py`, `memory.py`, `namespace.py`, `delegation.py`, `transports.py`

仍可提取:
- Colony 主类中的 **cat 管理方法** (`create_cat`, `adopt`, `release`, `get_cat`) → `colony/management.py`
- Colony 主类中的 **通信方法** (`broadcast`, `broadcast_request`, `signal_between`) → `colony/communication.py`
- `__init__.py` 仅保留 Colony 类定义 + 核心初始化 + 重导出

目标: `__init__.py` ≤ 500 行

#### T-04: defaults 大文件拆分

**`defaults/organs/brain.py` (804 行)** — Noop 器官实现:
- 拆为 `defaults/organs/brain_core.py` (Thalamus + Cerebrum + Cerebellum + BrainStem)
- 拆为 `defaults/organs/brain_memory.py` (Hippocampus + Frontal + Hypothalamus)
- 原 `brain.py` 改为重导出 + 保留 Amygdala/Cortex (或全移到子文件)

**`defaults/renovated/brain.py` (903 行)** — Renovated 器官实现:
- 仿照 Noop 拆法镜像拆分
- `defaults/renovated/brain_core.py` + `defaults/renovated/brain_memory.py`

**`defaults/presets.py` (530 行)** — Keyword/Prompt 预设:
- 关键词预设部分 → `defaults/presets_keywords.py`
- 提示词预设部分保留在 `presets.py` (≤300 行)

#### T-05: biology 大文件拆分

**`biology/cat_self.py` (712 行)** — CatSelf 单类:
- 提取 DefaultLoop 实现 → `biology/cat_self_loops.py`
- CatSelf 本体保留在 `cat_self.py` (≤450 行)

**`biology/__init__.py` (597 行)** — 重导出:
- 提取模块级文档 → 正文保留 20 行概要，详细文档移至 `biology/README.md` 或作为包级 docstring 精简
- 重导出逻辑精简

#### T-06: 其他超标文件

**`_exports.py` (661 行)** — `__all__` + `_LAZY_MAP`:
- `__all__` 列表和 `_LAZY_MAP` 字典 → `_exports_data.py`（纯数据文件）
- `_exports.py` 保留核心逻辑 (≤200 行)

**`adapters/brain.py` (566 行)** — 脑区适配器:
- 拆为 `adapters/brain_core.py` + `adapters/brain_memory.py`

**`assembly.py` (777 行)** — CatBase 单类:
- 提取 `_build_diagnostics()` 和 `_ensure_organs()` 等辅助方法 → `assembly_helpers.py`
- CatBase 类保留在 `assembly.py` (≤500 行)

#### T-07: 接近超标文件精简单

| 文件 | 当前 | 目标 | 方法 |
|------|------|------|------|
| `task_orchestrator.py` | 549 | ≤500 | 提取 `_validate_dag()` + `_resolve_deps()` 为 helper 函数 |
| `nervous.py` | 534 | ≤500 | 提取 `_prepare_signal()` + `_dispatch()` 或 dupe 逻辑外提 |
| `loops.py` | 529 | ≤500 | 提取 `_ensure_registry()` + LoopSequence 独立子模块 |

## 4. 文档补全 (T-08)

### 4.1 v1.3.8 缺失文档

v1.3.8 仅有 release commit 无版本文档。补全:
- `docs/meowcat/v1.3.8/README.md` — 版本总览
- `docs/meowcat/v1.3.8/review.md` — 变更回顾

### 4.2 v1.3.9 版本文档

产出标准四件套:
- `docs/meowcat/v1.3.9/README.md`
- `docs/meowcat/v1.3.9/tasks.md`
- `docs/meowcat/v1.3.9/review.md`

### 4.3 plan 归档

- 清理记忆中的 `plan_1.2.36` 活跃计划（已完成放入 `docs/plans/meowcat/` 或确认已完成）

## 5. 质量门 (T-09)

```bash
ruff check meowcat/ tests/   # 零错误
mypy meowcat/                # 零新增错误
pytest tests/ -v             # 全绿 (≥2011 passed)
```

## 6. 不改的东西

- `nervous.py` 延迟 import 耦合点（见架构文档 §23）— 已在跟踪中，非紧急
- 测试命名统一 (`test_vXXX_*` → `test_{module}_*`) — 风险大收益小，延后
- 新功能、新 API、新依赖 — 绝对不碰
- meowagent 应用层 — v1.3.9 仅框架层
