# v1.3.9 任务拆解 + 进度跟踪

> 来源: `.qoder/plans/plan_1.3.9.md`
> 类型: 代码健康整理 — 零新功能、零 API 变更

## 任务清单

### T-01: 架构设计 — plan + design

- [x] 综合分析报告: 12 文件超标 + 10 处 deprecated + v1.3.8 文档缺失
- [x] 产出 `plan_1.3.9.md` (子任务表 + 并发说明)
- [x] 产出 `design.md` (拆分方案 + deprecated 清单 + 风险提示)
- [x] 各模块拆分边界确定: 只拆不重构、公共 API 不变

### T-02: Deprecated 清理

- [x] 移除 `LLMConfig = ModelConfig` 别名 (`models.py`)
- [x] 移除 `L6StorageProtocol` (v1.3.6 起 deprecated)
- [x] 清理 Paws 旧方法: `interact_with_tool` / `run_command` / `touch_file`
- [x] 同步清理 `adapters/sense.py` / `defaults/organs/voice.py` / `defaults/renovated/brain.py` 中关联引用
- [x] 验证: 搜全框架零残留引用

### T-03: colony/**init**.py 拆分 (971→422)

- [x] Colony 主类精简 — 保留核心初始化 + 重导出
- [x] cat 管理 / 通信方法已在 `cat_ops.py` / `communication.py` / `llm_shelf.py` 中
- [x] 验证: `__init__.py` ≤ 500 行，所有导入路径不变

### T-04: defaults 大文件拆分

- [x] `organs/brain.py` (804): 提取 Hippocampus → `organs/hippocampus.py`
- [x] `renovated/brain.py` (903): 提取 Hippocampus → `renovated/hippocampus.py`
- [x] `renovated/brain.py`: 提取 BrainStem → `renovated/brainstem.py`
- [x] `renovated/brain.py`: 提取 Cerebrum → `renovated/cerebrum.py`
- [x] `presets.py` (530): 拆为 `presets/_classes.py` + `presets/_data.py`
- [x] 验证: 所有文件 ≤ 500 行

### T-05: biology 大文件拆分

- [x] `cat_self.py` (712→381): 提取 DefaultLoop 实现 → `cat_self_loops.py`
- [x] `__init__.py` (597→210): 提取器官规格定义 → `organ_spec.py`
- [x] 验证: CatSelf 单类保留，API 不变

### T-06: \_exports + adapters + assembly 拆分

- [x] `_exports.py` (661→235): 提取 `__all__` + `_LAZY_MAP` → `_lazy_map.py`
- [x] `adapters/brain.py` (566→375): 提取 Hippocampus 适配器 → `adapters/hippocampus.py`
- [x] `assembly.py` (777→438): 提取辅助方法 → `assemblers.py` + `assembly_signals.py`
- [x] 验证: CatBase 单类不拆，只提取 helper

### T-07: 接近超标文件精简

- [x] `task_orchestrator.py` (549→473): 提取 `_validate_dag()` + `_resolve_deps()` helper
- [x] `nervous.py` (534→492): 提取 `_prepare_signal()` + `_dispatch()` helper
- [x] `loops.py` (529→496): 提取 `_ensure_registry()` + dupe 逻辑外提
- [x] 验证: 三文件均 ≤ 500 行

### T-08: 版本文档产出

- [x] 更新 `v1.3.9/README.md` — 最终行数 + 子任务状态
- [x] 创建 `v1.3.9/tasks.md` — 本文档
- [x] 创建 `v1.3.9/review.md` — 审查报告
- [x] 同步 `CATALOG.md` — 版本号 + 文件索引更新
- [x] `AGENTS.md` — 零变更（v1.3.9 无新功能无 API 变更）

### T-09: 质量门

- [ ] `ruff check meowcat/ tests/` — 零错误
- [ ] `mypy meowcat/` — 零新增错误
- [ ] `pytest tests/ -v` — 全绿

### T-10: 发布

- [ ] 更新 `pyproject.toml` version → 1.3.9
- [ ] `git add -A && git commit -m "release: v1.3.9"`
- [ ] `git tag v1.3.9`
- [ ] `git push --follow-tags`

---

## 验收清单

- [x] 12 个超标文件全部 ≤ 500 行
- [x] 10 处 deprecated 代码全部移除
- [x] 零 API 变更 — 所有 `from meowcat.xxx import` 路径不变
- [x] 零新功能 — 纯整理，无逻辑变更
- [x] 6 个新文件: `_lazy_map.py` / `adapters/hippocampus.py` / `assemblers.py` / `assembly_signals.py` / `biology/cat_self_loops.py` / `biology/organ_spec.py`
- [x] 版本文档 3 件套: README / tasks / review
- [ ] ruff + mypy + pytest 全绿
- [ ] release v1.3.9

## 执行顺序

```
T-01 (plan + design)
  │
T-02 (deprecated 清理 — 必须串行先做)
  │
T-03 [∥] T-04 [∥] T-05 [∥] T-06 [∥] T-07 [∥]  (并行拆分)
  │
T-08 (文档 — 依赖 T-02~T-07)
  │
T-09 (质量门)
  │
T-10 (发布)
```
