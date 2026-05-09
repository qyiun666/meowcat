# plan_1.3.9 — 代码健康整理

> 版本: v1.3.9 | 类型: 纯整理（零新功能） | 创建: 2026-05-09
> 来源: 综合分析报告 — 12 文件超标 + 10 处 deprecated + 文档缺失

## 目标

1. 12 个 >500 行文件拆至 ≤500 行（符合 G-02 编码规范）
2. 移除 10 处 deprecated 标记代码
3. 补齐 v1.3.8 版本文档
4. 会议驱动要求: 只改框架层 (meowcat/)，零 meowagent 依赖

## 子任务表

| 子任务 | 能力域   | 依赖      | 并发 | 行改动上限 | 一句话                                |
| ------ | -------- | --------- | ---- | ------ | ------------------------------------- |
| T-01   | 架构设计 | 无        | —    | —      | 产出 design.md + plan（当前会话）     |
| T-02   | 代码生成 | T-01      | —    | ≤150   | deprecated 清理: LLMConfig/L6StorageProtocol/Paws 旧方法 |
| T-03   | 代码生成 | T-01      | [∥]  | ≤200   | colony/__init__.py 971→≤500 拆分      |
| T-04   | 代码生成 | T-01      | [∥]  | ≤200   | defaults 大文件拆分 (organs/brain 804 + renovated/brain 903 + presets 530) |
| T-05   | 代码生成 | T-01      | [∥]  | ≤200   | biology 大文件拆分 (cat_self 712 + __init__ 597) |
| T-06   | 代码生成 | T-01      | [∥]  | ≤200   | 其他超标文件分布式拆分 (_exports 661 + adapters/brain 566 + assembly 777) |
| T-07   | 代码生成 | T-01      | [∥]  | ≤200   | 剩余接近超标文件精简 (task_orchestrator 549 + nervous 534 + loops 529) |
| T-08   | 文档更新 | T-02~T-07 | —    | —      | 产出 v1.3.9 README/tasks/review + 同步 AGENTS/CATALOG |
| T-09   | 代码审查 | T-02~T-07 | —    | —      | ruff + mypy + pytest tests/ -v 全绿 |
| T-10   | 最终     | T-08,T-09 | —    | —      | 更新 version + git tag + push |

## 并发说明

- T-02 必须串行先做: deprecated 清理影响 adapters/sense.py 和 defaults/renovated/brain.py，避免后续拆分产生冲突
- T-03~T-07 全部 [∥] 可并行: 各自操作独立包/独立文件，零冲突
  - T-03: 仅动 colony/ 包
  - T-04: 仅动 defaults/ 包
  - T-05: 仅动 biology/ 包
  - T-06: 动 _exports.py + adapters/brain.py + assembly.py（顶层 + adapters 子包）
  - T-07: 动 task_orchestrator.py + nervous.py + loops.py（顶层）
- T-08: 等全部代码改动完成后串行写文档
- T-09: 等全部代码改动完成后串行验证
- T-10: 最终发布

## 计划生命周期

```
T-01 [x] → T-02 [ ] → T-03~T-07 [ ] [∥] 并行 → T-08 [ ] → T-09 [ ] → T-10 [ ]
                                                                        └─ release: v1.3.9
```

## 风险提示

- `assembly.py` (777 行) 是 CatBase 单类文件，硬拆可能损害可读性；优先提取 helper 函数而非拆类
- `_exports.py` (661 行) 主要是 `__all__` 列表 + `_LAZY_MAP` 字典，可提取为数据文件
- 已存在 2 个未提交的 ruff 格式化修改 (organs/brain.py, organs/sense.py)，需先处理
