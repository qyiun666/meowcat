# meowcat v1.0.1 — 任务拆解

## 任务清单

### T1: CatBase 新增配置字段 + `__getattribute__` 拦截

| 项 | 文件 | 内容 |
|---|---|---|
| 构造参数 | `meowcat/assembly.py` | 新增 `parent_id`, `allowed_organs`, `forbidden_methods` |
| parent_id property | `meowcat/assembly.py` | 返回 `self._parent_id` |
| `__getattribute__` | `meowcat/assembly.py` | allowed_organs 拦截 + `_ALWAYS_ALLOWED` 白名单 |
| forbidden_methods | `meowcat/assembly.py` | 传给 `Nervous(forbidden_methods=...)` |
| 初始化顺序 | `meowcat/assembly.py` | `_allowed_organs=None` 先设，末尾再设真实值 |

**验收**: `CatBase("x", parent_id="main", allowed_organs=frozenset({"cerebrum"}))` 创建成功 ✓

### T2: 删除 KittenBase 及相关代码

| 项 | 文件 | 内容 |
|---|---|---|
| 删除类 | `meowcat/assembly.py` | `class _KittenParentProxy` + `class KittenBase` |
| 删除函数/常量 | `meowcat/biology.py` | `KITTEN_FORBIDDEN_METHODS` + `apply_kitten_wiring()` |
| 清理导出 | `meowcat/assembly.py`, `meowcat/biology.py` | 更新 `__all__` |

**验收**: `from meowcat import KittenBase` → `ImportError` ✓

### T3: KittenProtocol 降级

| 项 | 文件 | 内容 |
|---|---|---|
| 移除装饰器 | `meowcat/protocols.py` | 删除 `@runtime_checkable` |
| 更新文档 | `meowcat/protocols.py` | 标注 v1.0.1 降级，更新字段说明 |
| 移除 parent 字段 | `meowcat/protocols.py` | `parent: CatProtocol` → 删除（无对象引用） |

**验收**: `KittenProtocol` 仍是 `Protocol` 子类，`issubclass(KittenProtocol, Protocol)` ✓

### T4: 公开 API 更新

| 项 | 文件 | 内容 |
|---|---|---|
| 移除导入 | `meowcat/__init__.py` | `from meowcat.assembly import ...` 移除 `KittenBase` |
| 移除导出 | `meowcat/__init__.py` | `__all__` 中移除 `"KittenBase"` |

**验收**: `"KittenBase" not in meowcat.__all__` ✓

### T5: meowagent 适配

| 项 | 文件 | 内容 |
|---|---|---|
| 继承切换 | `meowagent/cat/kitten.py` | `KittenAgent(KittenBase)` → `KittenAgent(CatBase)` |
| 构造参数 | `meowagent/cat/kitten.py` | `super().__init__(..., parent_id=..., forbidden_methods=...)` |
| 注释更新 | `meowagent/cat/restricted.py` | `KittenBase.__getattribute__` → `CatBase.__getattribute__` |

**验收**: meowcat 测试覆盖 `KittenAgent` 权限行为 ✓

### T6: 测试

| 项 | 文件 | 内容 |
|---|---|---|
| 新建 | `test_v101_cat_permissions.py` | parent_id / allowed_organs / forbidden_methods 测试 (13 条) |
| 新建 | `test_v101_cat_isolation.py` | 分身猫隔离测试 (10 条) |
| 删除 | `test_v054_kitten_wiring.py` | 旧 KittenBase wiring 测试 |
| 删除 | `test_v513_kitten_isolation.py` | 旧 KittenBase 隔离测试 |
| 更新 | `test_assembly.py` | KittenBase → CatBase forbidden_methods |
| 更新 | `test_biology.py` | 移除 KITTEN_FORBIDDEN_METHODS 测试 |
| 更新 | `test_v059_backward_compat.py` | KittenBase → CatBase 新参数测试 |
| 更新 | `test_v051_protocol_checked.py` | KittenProtocol 降级测试 |

**验收**: 491 条测试全部通过 ✓

### T7: 文档

| 项 | 内容 |
|---|---|
| design.md | 架构决策 (ADR-1)、API 变更、拦截设计 |
| tasks.md | 任务拆解 + 验收 |
| review.md | 审查记录 + 遇到的问题 |
| README.md | 版本总览 |

### T8: 回归验证

| 项 | 命令 | 结果 |
|---|---|---|
| meowcat 测试 | `pytest meowcat/tests/ -v` | 491 ✓ |
| 正面验收 | `CatBase('x', parent_id='main', allowed_organs=frozenset({'cerebrum'}))` | ✓ |
| 负面验收 | `from meowcat import KittenBase` → `ImportError` | ✓ |
| 行数检查 | `assembly.py` 483 行, `biology.py` 318 行 | ✓ |

## 进度

| 任务 | 状态 |
|---|---|
| T1   | ✅ |
| T2   | ✅ |
| T3   | ✅ |
| T4   | ✅ |
| T5   | ✅ |
| T6   | ✅ |
| T7   | ✅ |
| T8   | ✅ |
