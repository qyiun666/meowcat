# meowcat v1.0.1 — 审查记录

## 关键决策

### D1: `_allowed_organs` 初始化顺序

**问题**: `__getattribute__` 在 `__init__` 中首次访问 `self.path_registry` 时就被调用，但此时 `_allowed_organs` 尚未赋值，导致 `AttributeError`。

**初次尝试**: 将 `_allowed_organs` 置顶赋值 → 但此时其他 `self.xxx` 属性还未设置，`allowed_organs` 有限制时会拦截 `path_registry` 等内部属性。

**最终方案**: 三阶段初始化：
1. `__init__` 开头设 `_allowed_organs = None`（全部放行）
2. 依次设置所有 `self.xxx` 属性（registries, organs, etc.）
3. `__init__` 末尾设 `_allowed_organs = allowed_organs`（真实值）

这样既避免了 `AttributeError`（属性总存在），又避免了过早拦截（None = 全部放行）。

### D2: `_ALWAYS_ALLOWED` 白名单

**问题**: `allowed_organs` 是器官名的 allowlist，但 `cat_id`、`parent_id` 等 CatBase 自身 property 不是器官名，不应被拦截。

**决策**: 添加类级别的 `_ALWAYS_ALLOWED` frozenset，包含 CatBase 核心属性：
- `cat_id`, `parent_id` — 标识属性
- `tool_registry`, `skill_registry`, `path_registry`, `chain_registry`, `loop_registry` — 注册中心
- `wiring`, `reflexes`, `events` — 子系统

这些属性在任何 `allowed_organs` 配置下都永不禁用。

### D3: meowagent 适配最小化

**决策**: `KittenAgent` 只传 `parent_id` + `forbidden_methods`，不传 `allowed_organs`。

**理由**: KittenAgent 不直接持有主猫器官属性（使用 `RestrictedCatProxy` 间接访问），`allowed_organs=None` 足够。分身猫的隔离靠"根本没给父猫对象引用"实现，而非属性拦截。

## 遇到的问题

### 测试被 `__getattribute__` 大量拦截

第一版 `__getattribute__` 过于激进，`allowed_organs=frozenset({"cerebrum"})` 时连 `cat_id` 都被拦截。解决：加入 `_ALWAYS_ALLOWED` 白名单。

### `_allowed_organs` 初始化顺序导致的 `AttributeError`

第一版将 `_allowed_organs` 放到 `__init__` 末尾 → `register_builtin_paths(self.path_registry)` 触发 `__getattribute__` → `_allowed_organs` 不存在 → `AttributeError`。解决：三阶段初始化（见 D1）。

## 回归验证

- 491/491 测试通过
- `from meowcat import KittenBase` → `ImportError`
- `CatBase("x", parent_id="main", allowed_organs=frozenset({"cerebrum"}))` 创建成功
- `assembly.py` 483 行（满足 ≤500 行限制）
