# meowcat v1.0.4 — 设计文档

## 动机

已有四层组合模型：

```
Path → Chain → Loop
```

Loop 是 Chain + 触发/退出事件的封装，但多个 Loop 之间的编排（如"先维护、再体检"）需要应用层额外编写编排逻辑。LoopSequence 填补这个空白，提供框架级的 Loop 组合能力。

## 设计

### LoopSequence 数据类

```python
@dataclass(frozen=True)
class LoopSequence:
    name: str
    description: str = ""
    loops: tuple[str, ...] = ()          # Loop 名称序列
    mode: str = "sequential"             # "sequential" | "event_driven"
    stop_on_error: bool = True
```

### LoopSequenceRegistry

```python
@dataclass
class LoopSequenceRegistry:
    def register(self, seq: LoopSequence) -> None
    def get(self, name: str) -> LoopSequence | None
    def list_all(self) -> list[LoopSequence]
    async def run(self, cat, name, **initial_input) -> dict
```

### 执行模式

**sequential**:

1. 按 `loops` 顺序逐个执行 `cat.loop_registry.run(loop_name, **current_input)`
2. 前一步返回值（dict）作为下一步的 kwargs
3. `stop_on_error=True` 时任何 Loop 失败立即抛异常；`False` 时跳过失败继续

**event_driven**:

1. 所有 Loop 通过 `asyncio.gather` 并发执行
2. 各自获得相同的 `initial_input`
3. 返回 `{loop_name: result, ...}` 字典
4. `stop_on_error=True` 任一失败整体抛异常；`False` 时返回 `{"_error": str}`

### CatBase 集成

- `cat.loopseq_registry`: LoopSequenceRegistry 实例
- `cat.run_loopseq(name, **inputs)`: 委托给 `loopseq_registry.run()`
- `loopseq_registry` 在 `_ALWAYS_ALLOWED` 中，分身猫不受限

### 内置 LoopSequence

```python
DAILY_MAINTENANCE_SEQ = LoopSequence(
    "daily_maintenance",
    "日常维护 — 自维护后体检",
    loops=("maintenance", "diagnostic"),
    mode="sequential",
)
```

## 关键决策

- **LoopSequence 引用 Loop 名而非对象**：与 Chain → Path 的引用方式一致，通过 registry 按名查找，解耦注册顺序
- **mode 校验在 `__post_init__`**：非法 mode 在创建时即报错
- **event_driven 的并发中止**：`stop_on_error=True` 用 `asyncio.gather`，任一失败即取消其余 task
- **空 loops 返回 `{"": dict(initial_input)}`**：与空 Chain 语义一致

## API 兼容性

- 完全新增，不影响现有 API
- `from meowcat import LoopSequence` 新增导入
- 所有旧测试零修改通过
