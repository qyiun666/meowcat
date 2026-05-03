# meowcat v1.0.2 — Colony 猫群容器

> 实现框架层多猫协作容器，Colony 作为猫群的创建容器 + 共享存储持有者。

## 子版本进度

| 子版本 | 内容               | 状态 |
| ------ | ------------------ | ---- |
| v1.0.0 | 版本独立 + API 清理 | ✅   |
| v1.0.1 | CatBase 统一       | ✅   |
| v1.0.2 | Colony 猫群容器    | ✅   |
| v1.0.3 | Viz + Chain 事务   | ❌   |
| v1.0.4 | LoopSequence       | ❌   |
| v1.0.5 | 超行拆分（可选）   | ❌   |

## v1.0.2 交付

### T1: Colony 类实现

**新文件**: `meowcat/colony.py` (350 行)

- `Colony(colony_id, storage, cross_wiring_allowed, cross_wiring_forbidden)` — 猫群容器
- `create_cat(cat_id, parent_id, allowed_organs, memory_snapshot)` — 创建猫并自动注册
- `register(cat)` / `unregister(cat_id)` / `get_cat(cat_id)` / `list_cats()` — 注册/查找
- `deliver_result(parent_id, from_kitten, result)` — 分身旁回传结果
- `broadcast(event, **data)` — 广播事件到所有猫
- `health_check_all()` — 全猫体检
- `signal_between(from_id, to_id, to_category, to_name, method, ...)` — 猫间 signal
- `cat_count` 属性

### T2: 跨猫 wiring 隔离

- `cross_wiring_allowed` / `cross_wiring_forbidden` — 白名单/黑名单跨猫边
- `allow_cross(from_cat, to_cat)` / `forbid_cross(from_cat, to_cat)` — 声明跨猫边
- `_assert_cross_allowed()` — 校验跨猫边，违反抛 `IllegalNeuralPathError`
- 未设置 cross_wiring → 全部放行（默认）

### T3: SharedStorage 命名空间隔离

- `storage_get/set/delete(cat_id, key)` — `cat_id` 前缀自动隔离
- `storage_list_keys(cat_id)` — 列出该猫的所有 key（去名前缀）
- `storage_watch(cat_id, pattern)` — 监听 key 变更
- `InMemorySharedStore` 新增 `list_keys()` / `watch()` / watcher 通知机制

### T4: 公开 API

- `meowcat/__init__.py` 导出 `Colony`
- `from meowcat import Colony` 可用

## 验收

- [x] `from meowcat import Colony` 可用
- [x] `colony.create_cat("k1", parent_id="main", allowed_organs={...})` 创建分身旁
- [x] 分身旁通过 `parent_id` 追踪，无父猫对象引用
- [x] `deliver_result()` 父猫可接收结果
- [x] `signal_between` 跨猫通信成功
- [x] 禁止的跨猫边抛 `IllegalNeuralPathError`
- [x] 新增测试 25 条，全部通过
- [x] 回归: 516 条测试全部通过
