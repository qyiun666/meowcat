# meowcat v1.0.2 — 审查记录

## 审查项

### ✅ Colony 可用

`from meowcat import Colony` 导入成功。

### ✅ create_cat 自动注册

```python
colony = Colony("test", storage=InMemorySharedStore())
cat = colony.create_cat("cat-1")
assert colony.get_cat("cat-1") is cat
assert colony.list_cats() == ["cat-1"]
```

### ✅ 跨猫 wiring 隔离

```python
colony = Colony("test", storage=InMemorySharedStore(),
                cross_wiring_forbidden={("a", "b")})
# signal_between("a", "b", ...) → IllegalNeuralPathError
```

### ✅ 命名空间隔离

```python
colony.storage_set("cat-a", "key", "va")
colony.storage_set("cat-b", "key", "vb")
assert colony.storage_get("cat-a", "key") == "va"
assert colony.storage_get("cat-b", "key") == "vb"
```

### ✅ signal_between 跨猫通信

```python
result = await colony.signal_between(
    "a", "b", "brain", "hippocampus", "locate", query="hello"
)
# → {"results": [], "query": "hello"}
```

### ✅ deliver_result 回传

结果通过共享存储读写，命名空间隔离保证不会互相覆盖。

### ✅ 测试全绿

新增 25 passed，回归 516 passed，0 failed。

## 关键决策记录

| 决策                                  | 理由                                        |
| ------------------------------------- | ------------------------------------------- |
| Colony 作为创建容器                    | 统一入口，自动共享存储                      |
| 跨猫 wiring 独立                      | Cat A 的 wiring 不校验 Cat B 的器官         |
| 命名空间隔离在 Colony 层              | 存储层保持简单，隔离逻辑集中               |
| watch 用 asyncio.Queue                | 单进程原型够用，生产可替换                  |
| `SharedStorageProtocol` 未扩展       | 结构类型当前可工作，避免协议层 breaking change |

## 发现的问题（未修复）

1. `SharedStorageProtocol` 未声明 `get/set/delete/list_keys/watch` — 当前依赖结构类型可工作，后续版本统一
2. `deliver_result` 和 `storage_get` 属异步操作，sync 场景需注意调用方在 async context 中
