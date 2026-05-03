# meowcat v1.0.3 — 审查记录

## 审查项

### ✅ render_wiring 函数

支持 mermaid 和 dot 两种格式，允许边实线、禁止边红色虚线、孤立节点灰色。

```python
from meowcat.diagnose import render_wiring
w = Wiring()
w.connect(("brain", "cerebellum"), ("sense", "paws"))
w.forbid(("brain", "cerebrum"), ("sense", "paws"))
print(render_wiring(w))  # mermaid
print(render_wiring(w, format="dot"))  # dot
```

### ✅ CatBase.wiring_diagram() 快捷方法

```python
cat.wiring_diagram()               # → mermaid
cat.wiring_diagram(format="dot")   # → dot
```

wiring 禁用时抛 `AttributeError`。

### ✅ Chain 支持 rollback_paths

```python
Chain("x", ("a", "b"), rollback_paths=("rb", "ra"))
```

### ✅ ChainRegistry.run() 事务包装

成功路径不变，失败时逆序执行 rollback_paths，回滚异常不掩盖原始异常。

### ✅ 测试全绿

新增 25 passed（12 wiring viz + 13 chain rollback），回归 541 passed，0 failed。

## 关键决策

| 决策                         | 理由                                                     |
| ---------------------------- | -------------------------------------------------------- |
| render_wiring 加 organs 参数 | 支持孤立节点检测，wiring_diagram 自动传入 mounted organs |
| 回滚逆序执行                 | 与 Python context manager 精神一致：后执行的先回滚       |
| 回滚异常 pass 不抛           | 回滚中某步失败不阻止后续回滚，也不掩盖原始异常           |
| Chain.rollback_paths 默认 () | 完全向后兼容                                             |

## 发现的问题

无。
