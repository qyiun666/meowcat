# meowcat v1.0.1 — 设计

> 前置重构：统一 CatBase 模型，删除 KittenBase。Colony 依赖此统一后的 CatBase。

## 核心决策

### ADR-1: CatBase/KittenBase 统一

**决策**: 删除 `KittenBase` 类，统一为单一 `CatBase`。分身猫 = 一只带了 `parent_id` 且器官/方法权限受限的 `CatBase`。

**理由**:

- 分身猫就是猫。区别仅在于配置——挂载了哪些器官、允许哪些方法、有没有父猫 ID
- 分身猫是子进程独立运行，**不持有父猫对象引用**（只有 `parent_id` 字符串）。父猫通过 plan 分配上下文切片给分身猫，分身猫的隔离靠"根本没给"而不是代理拦截
- `_KittenParentProxy` 拦的"分身猫访问父猫器官"在正确设计里根本不会发生
- 代码量减少：删除 `KittenBase` (~80行)、`_KittenParentProxy` (~40行)、`KITTEN_FORBIDDEN_METHODS` (~15行)、`apply_kitten_wiring()` (~15行)

**模型**:

```
父猫 plan → 切片上下文 + 任务数据 → 分身猫（子进程 CatBase）
                                      │
                                     parent_id="main-cat"（仅标识）
                                     allowed_organs={cerebrum, cerebellum, paws, ...}
                                     memory_snapshot=父猫分配的切片
                                      │
                                     ← MergeProposal 回传结果
```

### API 变更

**CatBase 新增构造参数**:

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `parent_id` | `str \| None` | `None` | 父猫标识（纯字符串，无对象引用） |
| `allowed_organs` | `frozenset[str] \| None` | `None` | 允许访问的器官属性名。None=全部允许 |
| `forbidden_methods` | `frozenset[str]` | `frozenset()` | 方法级黑名单，signal 时校验 |

**删除**:

| 删除项 | 原位置 | 替代 |
|---|---|---|
| `KittenBase` 类 | `meowcat/assembly.py` | `CatBase(parent_id=..., allowed_organs=..., forbidden_methods=...)` |
| `_KittenParentProxy` 类 | `meowcat/assembly.py` | 无（隔离靠"根本没给父猫引用"） |
| `KITTEN_FORBIDDEN_METHODS` | `meowcat/biology.py` | `CatBase(forbidden_methods={...})` |
| `apply_kitten_wiring()` | `meowcat/biology.py` | 应用层自行配置 wiring 禁止边 |
| `KittenProtocol` `@runtime_checkable` | `meowcat/protocols.py` | 降级为纯文档 Protocol |

**KittenProtocol 降级**: 移除 `@runtime_checkable`，保留为纯文档 Protocol。权限由 CatBase 的 `allowed_organs` + `forbidden_methods` 控制。

### `__getattribute__` 拦截设计

```python
def __getattribute__(self, name):
    if name.startswith('_'):          # _ 前缀零开销跳过
        return super().__getattribute__(name)
    if _allowed_organs is None:       # None = 全部放行
        return super().__getattribute__(name)
    if name not in _allowed_organs:
        if name not in _ALWAYS_ALLOWED:  # CatBase 自身属性永不禁用
            raise IllegalNeuralPathError(...)
    return super().__getattribute__(name)
```

`_ALWAYS_ALLOWED`: `cat_id`, `parent_id`, `tool_registry`, `skill_registry`, `path_registry`, `chain_registry`, `loop_registry`, `wiring`, `reflexes`, `events`

注意：`_allowed_organs` 在 `__init__` 开头设 `None`（允许所有 self.xxx 赋值），末尾再设为真实值。这是为了在 `__init__` 内部访问 `self.path_registry` 等时不被拦截。

### meowagent 适配

`KittenAgent(KittenBase)` → `KittenAgent(CatBase)`，`super().__init__()` 传入：

```python
super().__init__(
    self.kitten_id,
    parent_id=parent.cat_id,
    forbidden_methods=frozenset({"spawn_kitten", "absorb_merge"}),
)
```

`RestrictedCatProxy` 已是独立实现（不持有 parent 引用），无需改动。注释中的 `KittenBase.__getattribute__` 更新为 `CatBase.__getattribute__`。

## 文件影响

| 层 | 文件 | 操作 |
|---|---|---|
| 框架 | `meowcat/assembly.py` | +3 字段, +`__getattribute__`, -KittenBase, -_KittenParentProxy |
| 框架 | `meowcat/biology.py` | -KITTEN_FORBIDDEN_METHODS, -apply_kitten_wiring() |
| 框架 | `meowcat/protocols.py` | KittenProtocol 降级为纯文档 |
| 框架 | `meowcat/__init__.py` | -KittenBase 导出 |
| 应用 | `meowagent/cat/kitten.py` | KittenAgent 继承 CatBase |
| 应用 | `meowagent/cat/restricted.py` | 注释更新 |
| 测试 | `meowcat/tests/` | 删除 2, 新建 2, 更新 4 |

## 未解决问题

- `protocols.py` (619行) 仍超过 500 行限制 → v1.0.5 处理
- Colony 依赖统一后的 CatBase → v1.0.2 实现
