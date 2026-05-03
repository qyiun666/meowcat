# meowcat v1.0.1 — 版本总览

> 前置重构：统一 CatBase 模型，删除 KittenBase。为 v1.0.2 Colony 铺路。

## 子版本进度

| 子版本 | 内容 | 状态 |
|---|---|---|
| v1.0.1 | CatBase 统一（删除 KittenBase） | ✅ |

## v1.0.1 交付

### 1. CatBase 统一

- KittenBase + _KittenParentProxy 删除，分身猫 = `CatBase(parent_id=..., allowed_organs=..., forbidden_methods=...)`
- CatBase 新增 3 个构造参数：`parent_id`（字符串标识）、`allowed_organs`（器官 allowlist）、`forbidden_methods`（方法黑名单）
- `__getattribute__` 拦截：`allowed_organs` 有值时阻止非允许器官属性访问
- `_ALWAYS_ALLOWED` 白名单保护 CatBase 自身属性永不被拦截

### 2. biology.py 清理

- 移除 `KITTEN_FORBIDDEN_METHODS`、`apply_kitten_wiring()`
- 分身猫的 wiring 裁剪由应用层自行管理

### 3. KittenProtocol 降级

- 移除 `@runtime_checkable`，保留为纯文档 Protocol
- 权限控制由 CatBase 的 `allowed_organs` + `forbidden_methods` 负责

### 4. meowagent 适配

- `KittenAgent(KittenBase)` → `KittenAgent(CatBase)`
- 传入 `parent_id` + `forbidden_methods`，不传 `allowed_organs`

## 验收

- [x] `from meowcat import KittenBase` → `ImportError`
- [x] `KittenBase` 类不存在于 `meowcat/assembly.py`
- [x] `_KittenParentProxy` 类不存在
- [x] `KITTEN_FORBIDDEN_METHODS` 不存在于 `biology.py`
- [x] `apply_kitten_wiring()` 不存在
- [x] `CatBase("x", parent_id="main", allowed_organs=frozenset({"cerebrum"}))` 创建成功
- [x] 491 个测试全部通过
- [x] `assembly.py` 483 行 (≤500)
