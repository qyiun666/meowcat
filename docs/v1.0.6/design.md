# v1.0.6 设计

## 背景

v1.0.5 将源码移至 `meowcat/meowcat/` 子目录以适配 PyPI wheel 打包规范，
但遗漏了 `__init__.py` 中版本号查找路径的更新。

## 根因分析

```
meowcat/                          ← pyproject.toml 在此
└── meowcat/                      ← __init__.py.__file__ 在此
    └── __init__.py               ← _pyproject 路径计算

修复前: __file__.parent        = meowcat/meowcat/  ❌ (无 pyproject.toml)
修复后: __file__.parent.parent = meowcat/          ✅ (正确)
```

## 影响范围

- `__init__.py` L150: `_pyproject` 路径常量
- `pyproject.toml`: 版本号 1.0.5 → 1.0.6

## 兼容性

无破坏性变更。API 不变，version 号正常升级。
