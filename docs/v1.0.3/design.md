# meowcat v1.0.3 — 设计文档

## Part A: Wiring 可视化

### 动机

Wiring 图（有向图）存储了猫的神经通路约束，但开发者只能通过代码 `wiring.edges()` / `wiring.forbids()` 查看，缺乏直观的可视化输出。

### 设计

在 `meowcat/diagnose.py` 中新增 `render_wiring()` 函数：

```python
def render_wiring(wiring: Wiring, format: str = "mermaid") -> str:
    """生成 wiring 图的可视化表示。

    返回: mermaid 或 dot 格式的图描述字符串。
    - 允许边: 实线箭头 `-->`
    - 禁止边: 红色虚线 `-.->|forbidden|`
    - 无连线器官: 灰色孤立节点
    """
```

**mermaid 格式规则**：

- 节点: `(category:name)` 标识
- 允许边: `A --> B`
- 禁止边: `A -.->|"✗"| B`，带红色样式
- 孤立节点: 单独列出，灰色 `style X fill:#ddd`

**dot 格式规则**：

- 允许边: 实线箭头
- 禁止边: 红色虚线 `[color=red, style=dashed]`

在 `CatBase` 上新增快捷方法 `wiring_diagram()`：

```python
cat.wiring_diagram()               # → mermaid 字符串
cat.wiring_diagram(format="dot")   # → graphviz dot 字符串
```

### API 设计

```python
# 函数
from meowcat.diagnose import render_wiring
diagram = render_wiring(cat.wiring)
diagram = render_wiring(cat.wiring, format="dot")

# CatBase 快捷方法
diagram = cat.wiring_diagram()
diagram = cat.wiring_diagram(format="dot")
```

---

## Part B: Chain 事务性

### 动机

Chain 执行是多步 Path 序列。当前某步失败时没有回滚机制——前置步骤的副作用已写入（如记忆存储、实体添加），数据可能处于不一致状态。

### 设计

**Chain 数据类扩展**：新增 `rollback_paths` 字段：

```python
@dataclass(frozen=True)
class Chain:
    name: str
    path_names: tuple[str, ...] = ()
    description: str = ""
    rollback_paths: tuple[str, ...] = ()  # 失败时逆序执行的回滚 Path
```

**ChainRegistry.run() 事务包装**：

```python
async def run(self, cat, name, **kwargs):
    chain = self.get(name)
    try:
        for path_name in chain.path_names:
            result = await self._path_registry.run(cat, path_name, **kwargs)
            kwargs = result if isinstance(result, dict) else {"_result": result}
        return kwargs
    except Exception:
        for rollback_name in reversed(chain.rollback_paths):
            try:
                await self._path_registry.run(cat, rollback_name, **kwargs)
            except Exception:
                pass  # 回滚失败不掩盖原始异常
        raise
```

**关键决策**：

- 回滚按逆序执行（后执行的先回滚，与 Python context manager 精神一致）
- 回滚中某步失败不阻止后续回滚，也不掩盖原始异常
- 空 `rollback_paths` 行为不变（无回滚）
- 回滚的 kwargs 使用主链最后已知的 `current_input`

### API 兼容性

- `Chain` 新增字段有默认值 `()`，完全向后兼容
- `ChainRegistry.run()` 行为增强但语义兼容（成功路径不变）
