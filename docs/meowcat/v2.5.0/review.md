# v2.5.0 审查记录

> 审查日期: 2026-05-11

## 审查结论

**通过，可上线。**

## 测试结果

- 全量测试: **2015 passed**, 0 failed
- Persona 专项: **34 passed**
- Mypy: 仅 yaml stubs 缺失（项目预存问题）
- Ruff: 0 errors (2 个 lint 问题已修复)

## 发现的问题及修复

| # | 问题 | 状态 |
|---|------|------|
| 1 | pyproject.toml version 未更新 | ✅ 已修复 |
| 2 | v2.5.0 版本文档缺失 | ✅ 已创建 |
| 3 | CATALOG.md unwear 描述错误（说删除工具，实际不删） | ✅ 已修复 |
| 4 | CATALOG.md PersonaLoader rglob 模式描述错误 | ✅ 已修复 |
| 5 | CATALOG.md KnowledgeSeed API 示例用 data= 而非 name+properties | ✅ 已修复 |
| 6 | Ruff N806: _RISK_MAP → _risk_map | ✅ 已修复 |
| 7 | Ruff F401: unused Any import | ✅ 已修复 |

## 关键决策

1. **unwear 不删除工具/知识** — 知识和技能持久保留，符合"面具脱下但知识留下"的直觉
2. **personality 字段级覆写** — `apply_persona` 只覆盖面具指定的字段，保留未涉及的 key
3. **capable/incapable 为 None 时 snapshot fallback** — 如果面具未设置能力列表，使用 metacognition 的原有能力

## 架构一致性检查

- ✅ `_PersonaMixin` 正确集成到 Colony Mixin 链
- ✅ `"personas"` namespace 在 `_registered_ns` 中注册
- ✅ CatBase wear/unwear 正确编排多器官应用流程
- ✅ CatSelf 备份/还原逻辑正确处理多次切换
- ✅ PersonaLoader 错误处理完善（无效 YAML/非 dict/缺失 name 回退）
- ✅ 懒加载导出在 `_exports.py` 正确注册

## 经验教训

无阻塞问题。审查发现主要是文档不一致（CATALOG.md 与代码行为不匹配），这是典型的"代码改了文档没跟"问题。
