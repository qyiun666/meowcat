# meowcat v1.0.3 — Wiring 可视化 + Chain 事务性

> 两个独立但同属"框架健壮性"范畴的能力，合并为一个版本。

## 子版本进度

| 子版本 | 内容             | 状态 |
| ------ | ---------------- | ---- |
| v1.0.3 | Viz + Chain 事务 | 🚧   |

## 交付物

- **Part A**: Wiring 可视化 — `render_wiring()` 函数 + `cat.wiring_diagram()` 快捷方法
- **Part B**: Chain 事务性 — `Chain.rollback_paths` + `ChainRegistry.run()` 回滚包装

## 文件变更

| 文件                                        | 变更类型 |
| ------------------------------------------- | -------- |
| `meowcat/diagnose.py`                       | 扩展     |
| `meowcat/chain.py`                          | 修改     |
| `meowcat/assembly.py`                       | 扩展     |
| `meowcat/__init__.py`                       | 导出更新 |
| `meowcat/tests/test_v103_wiring_viz.py`     | 新增     |
| `meowcat/tests/test_v103_chain_rollback.py` | 新增     |
