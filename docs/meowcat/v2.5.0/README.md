# meowcat v2.5.0 — Persona 面具系统

> 发布日期: 2026-05-11 | 上一版本: [v2.4.0](../v2.4.0/) | 增量功能

## 一句话

新增 Persona 面具系统，支持预设角色的一键切换（性格/信念/能力/知识/工具/行为打包注入），YAML 文件批量加载。

## 做了什么

### 新增模块

- `meowcat/persona.py` — Persona dataclass + Belief / KnowledgeSeed / ConnectionSpec / ReflexSpec 子结构
- `meowcat/colony/persona_mgr.py` — Colony namespace `personas/` 面具存储 Mixin
- `meowcat/plus/persona_loader.py` — PERSONA.yaml 文件加载器

### 修改模块

- `meowcat/biology/cat_self.py` — 新增 `apply_persona()` / `remove_persona()` 方法，snapshot 中 persona 能力覆写
- `meowcat/assembly.py` — CatBase 新增 `current_persona` / `wear_persona()` / `unwear_persona()` 三件套
- `meowcat/colony/__init__.py` — Colony 注册 `"personas"` namespace，集成 `_PersonaMixin`
- `meowcat/_exports.py` — 新增 Persona / Belief 等 6 个懒加载导出

### 文档更新

- `AGENTS.md` §8 面具系统 + §9 API 示例
- `CATALOG.md` §IX 完整 Persona 使用文档

## API 速查

```python
from meowcat import Persona, Belief, PersonaLoader

# 创建面具
musk = Persona(name="musk", personality={"tone": "visionary"},
               beliefs=[Belief(key="fp", value="第一性原理", confidence=0.95)],
               capable=["engineering"], incapable=["poetry"])

# 注册到猫舍
await colony.register_persona(musk)

# 猫戴面具
await cat.wear_persona("musk")
cat.current_persona          # Persona(name="musk", ...)

# 脱下恢复
await cat.unwear_persona()

# YAML 批量加载
loader = PersonaLoader(dir=Path("./personas"))
await loader.load_all(colony)
```

## 兼容性

- **完全兼容**：所有现有 API 不变，纯增量
- `CatSelf` 新增 `apply_persona()` / `remove_persona()` 方法名称不冲突

## 文件清单

```
meowcat/
├── persona.py               # +223 行 新增
├── colony/persona_mgr.py    # +77 行  新增
├── plus/persona_loader.py   # +116 行 新增
├── biology/cat_self.py      # +30 行  修改
├── assembly.py              # +35 行  修改
├── colony/__init__.py       # +3 行   修改
├── _exports.py              # +4 行   修改
└── tests/
    └── test_v250_persona.py # +546 行 新增
```

## 净代码变化

| 类型     | 变化    |
| -------- | ------- |
| 代码 net | +490 行 |
| 测试 net | +546 行 |
| 文档 net | +80 行  |

## 子任务进度

| 子任务 | 状态 | 描述                                 |
| ------ | ---- | ------------------------------------ |
| T-01   | ✅   | 产出 design.md + 接口定义            |
| T-02   | ✅   | 实现 Persona dataclass + 子结构      |
| T-03   | ✅   | 实现 Colony namespace 面具存储       |
| T-04   | ✅   | 实现 Cat.wear/unwear + CatSelf.apply |
| T-05   | ✅   | 实现 PersonaLoader YAML 加载器       |
| T-06   | ✅   | 面具加载/切换/序列化测试 (34 tests)  |
| T-07   | ✅   | 同步 AGENTS + CATALOG                |
