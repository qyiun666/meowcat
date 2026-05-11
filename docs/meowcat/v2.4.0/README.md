# meowcat v2.4.0 — 架构精简：公开 API 认知模型重写

> 发布日期: 2026-05-11 | 上一版本: [v2.3.0](../v2.3.0/) | 非破坏性增量（代码层面）

## 一句话

把框架对外认知模型从三层的 Path/Chain/Loop 精简为两层的 `perceive()`（打工循环）+ `ReflectionLoop`（成长循环）。**不改代码逻辑，改认知模型。**

## 做了什么

### 公开 API 精简

- `CONVERSATION_LOOP` 和 `TOOL_EXECUTION_LOOP` 从 `from meowcat import` 公开导出中移除
- 两个常量代码不删除，仍定义在 `loops.py`，`run_loop("conversation")` 字符串方式仍可用
- `from meowcat.loops import CONVERSATION_LOOP` 内部仍可访问

### AGENTS.md 重写（三层 → 两层教学）

**移除**（约 200 行）：

- §5 23 条 Path 详细表格（7 个子节）
- §6 8 条 Chain 详细表格
- §7 7 条 Loop 详细表格（简化为 5 条旁路速查）

**新增**（约 30 行）：

- §5.1 打工循环 `perceive()` + `do_task()` 教学
- §5.2 成长循环 `ReflectionLoop` 三种模式
- §5.3 旁路 Loop 速查（5 个独立价值的 Loop）
- §5.4 Path/Chain 降级为内部基础设施

### CATALOG.md 升级为权威参考

- Path/Chain/Loop 详细表移至 CATALOG §高级参考
- `conversation` / `tool_execution` Loop 标注 "v2.4.0: 内部使用，perceive()/do_task() 取代"

### 代码标注

- `loops.py` 中 CONVERSATION_LOOP / TOOL_EXECUTION_LOOP 上方添加 `🔻 降级为内部实现（v2.4.0）` docstring

## 兼容性

- **代码层面完全兼容**：所有 131 个 `.py` 文件的功能逻辑未变
- **理论破坏性变更**：如果应用层写了 `from meowcat import CONVERSATION_LOOP`，v2.4.0 会 ImportError。替代：`cat.perceive()`。全局搜索确认 meowagent 无此依赖
- 所有 Path/Chain/Loop 运行时注册表不变，`BUILTIN_LOOPS` 仍包含全部 7 个 Loop

## 文件清单

```
meowcat/
├── _exports.py              # __all__ 移除 2 个常量 (-2 行)
├── _lazy_map.py             # _LAZY_MAP 移除 2 个条目 (-2 行)
├── loops.py                 # __all__ 精简 + docstring 标注 (~5 行)
├── AGENTS.md                # Path/Chain/Loop 三层 → perceive() + ReflectionLoop 两层 (-200 +30 行)
├── CATALOG.md               # Path/Chain/Loop 详细表 + 降级标注 (+60 行)
└── docs/meowcat/v2.4.0/
    ├── design.md            # 架构设计文档
    ├── README.md            # 本文件
    └── review.md            # 审查记录
```

## 净代码变化

| 类型     | 变化    |
| -------- | ------- |
| 代码 net | -9 行   |
| 文档 net | -110 行 |

## 认知模型对比

```
v2.3.0 (三层教学)                  v2.4.0 (两层教学)
┌─ Path × 23 (教学)               ┌─ perceive() / do_task() — 打工循环
├─ Chain × 8 (教学)               │  cat.perceive("你好")
├─ Loop × 7 (教学)                │  cat.do_task("写函数")
└─ perceive()                     │
                                  ├─ ReflectionLoop — 成长循环
                                  │  mode="conversation" / "task" / "learn"
                                  │
                                  ├─ 旁路 × 5 — 事件驱动
                                  │
                                  └─ Path/Chain — CATALOG 高级参考
```

## 子任务进度

| 子任务 | 状态 | 描述                                    |
| ------ | ---- | --------------------------------------- |
| T-01   | ✅   | 产出 v2.4.0 design.md                   |
| T-02   | ✅   | 精简 `_exports.py` `__all__`            |
| T-03   | ✅   | 精简 `_lazy_map.py`                     |
| T-04   | ✅   | 更新 `loops.py`                         |
| T-05   | ✅   | 重写 `AGENTS.md`                        |
| T-06   | ✅   | 更新 `CATALOG.md`                       |
| T-07   | ✅   | pytest 1981 passed                      |
| T-08   | ✅   | 产出 review.md + README.md + 版本号同步 |
