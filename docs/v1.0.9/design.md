# v1.0.9 设计文档

> 来源: `.qoder/plans/meowcat深版分析_版本拆分计划.md` v1.0.9 章节

## 设计目标

为 CatBase 和 Colony 添加面向 CLI 使用者的便捷方法，降低直接操作信号系统的门槛。

## CatBase 门面方法

### search_memory(query, limit=5)

**输入**: 搜索关键词 `query`，结果上限 `limit`
**内部流程**: `chain_registry.run("memory_search", msg=query, session_id=self.cat_id)`
**Chain**: `memory_search` → `locate` Path（THALAMUS 自环 → `thalamus.locate(msg, session_id)`）
**返回值**: LocateResultShape（dict）

> 参数映射：`query` → `msg`（匹配 ThalamusProtocol.locate 签名），`session_id` 自动填充 `self.cat_id`。

### memory_stats()

**输入**: 无
**内部流程**: `signal(BRAINSTEM, HIPPOCAMPUS, "stats")`
**返回值**: 记忆统计 dict（entities / episodes / connections）

> BRAINSTEM → HIPPOCAMPUS 是 wiring 允许边，"stats" 是 HippocampusProtocol 声明的 read_method。

### run_maintenance(country_code=None)

**输入**: 可选 `country_code`（当前未使用，预留接口）
**内部流程**: `run_loopseq("daily_maintenance")`
**元闭环**: `DAILY_MAINTENANCE_SEQ` — maintenance loop → diagnostic loop
**返回值**: 最后一步结果 dict

> `country_code` 参数保留在签名中但暂不传递（框架层 ThalamusProtocol 不暴露区域策略），为未来扩展预留。

## Colony 别名

### adopt(cat)

```
def adopt(self, cat: CatBase) -> None:
    self.register(cat)
```

语义别名：收养一只猫 → 注册到猫群。

### release(cat_id)

```
def release(self, cat_id: str) -> None:
    self.unregister(cat_id)
```

语义别名：释放一只猫 → 从猫群移除。

## 参数映射决策

| 决策                                   | 原因                                                                 |
| -------------------------------------- | -------------------------------------------------------------------- |
| `search_memory` 不传 `limit` 到 locate | ThalamusProtocol.locate(msg, session_id) 不接受 limit                |
| `run_maintenance` 不传 `country_code`  | 维护链的 decay/cleanup 路径会在步骤间传递 kwargs，不应暴露未定义参数 |
| `memory_stats` 无参数                  | stats() 是只读方法的典型模式                                         |

## 改动范围

| 文件                                | 改动                | 行数 |
| ----------------------------------- | ------------------- | ---- |
| `meowcat/assembly.py`               | CatBase +3 门面方法 | +45  |
| `meowcat/colony.py`                 | Colony +2 别名      | +21  |
| `meowcat/pyproject.toml`            | 版本 1.0.8 → 1.0.9  | 1    |
| `meowcat/tests/test_v109_facade.py` | 25 个测试           | +350 |
