# meowcat v1.0.2 — 设计

> 本版本实现 Colony 猫群容器（架构文档 §13 已设计 API）。

## 核心决策

### 1. Colony 作为创建容器

**决策**: `colony.create_cat()` 是创建猫的主要入口，创建的猫自动注册到 colony 并共享存储。

**理由**:
- Colony 拥有共享存储，猫在 colony 内创建时自动获得存储访问
- 分身旁和主猫通过 `parent_id` 追踪关系
- 结果通过 `colony.deliver_result()` 写入共享存储回传

### 2. 跨猫 wiring 独立于猫内 wiring

**决策**: Colony 维护独立的 `cross_wiring_allowed` / `cross_wiring_forbidden` 边集合，与每只猫自身的 Wiring 正交。

**理由**:
- Cat A 的 wiring 不校验 Cat B 的器官 — wiring 跨猫隔离
- 猫间 signal 需要明确的跨猫授权
- 不设置 cross_wiring → 全部放行（默认向后兼容）

### 3. 命名空间隔离在 Colony 层实现

**决策**: Colony 的 `storage_get/set/delete` 方法在 key 前自动添加 `cat_id/` 前缀，底层存储无需感知命名空间。

**理由**:
- 底层 `SharedStorageProtocol` 保持简单的 `get(key)/set(key,value)` 接口
- 隔离逻辑集中在一处（Colony），不侵入存储层
- 猫只能读写自己的 `cat_id/` 前缀数据

### 4. watch 通知机制

**决策**: `InMemorySharedStore` 新增 `watch(pattern)` 异步迭代器 + watcher 通知。

**理由**:
- 分身旁等待父猫分配任务时可通过 `watch` 监听 `tasks/` 变更
- 简单实现：`asyncio.Queue` per pattern，`set()` 时 `put_nowait` 通知
- 适合单进程原型，生产环境需替换为 Redis pub/sub 等

## API 设计

```python
class Colony:
    def __init__(self, colony_id, storage, *, cross_wiring_allowed=None, cross_wiring_forbidden=None)

    # 创建
    def create_cat(cat_id, *, parent_id=None, allowed_organs=None, memory_snapshot=None, **kw) -> CatBase

    # 注册
    def register(cat) -> None
    def unregister(cat_id) -> None
    def get_cat(cat_id) -> CatBase
    def list_cats() -> list[str]

    # 共享存储（命名空间隔离）
    async def storage_get(cat_id, key) -> Any
    async def storage_set(cat_id, key, value) -> None
    async def storage_delete(cat_id, key) -> None
    async def storage_list_keys(cat_id) -> list[str]
    async def storage_watch(cat_id, pattern) -> AsyncIterator

    # 结果回传
    async def deliver_result(parent_id, from_kitten, result) -> None

    # 广播
    async def broadcast(event, **data) -> list[Any]
    async def health_check_all() -> dict[str, dict]

    # 猫间通信
    async def signal_between(from_id, to_id, to_category, to_name, method, **kw) -> Any

    # 跨猫 wiring
    def allow_cross(from_cat, to_cat) -> None
    def forbid_cross(from_cat, to_cat) -> None
```

## 未解决问题

- `SharedStorageProtocol` 未包含 `list_keys` / `watch` 方法声明（结构类型当前可工作）
- `deliver_result` 和 `storage_get` 依赖异步语义，同步场景需注意
