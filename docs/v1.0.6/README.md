# meowcat v1.0.6 — P0 路径修复

> Bugfix release。修复 v1.0.5 引入的 `__version__` 读取路径错误。

## 概述

`meowcat/__init__.py` 中 `__version__` 从 `pyproject.toml` 动态读取版本号。
v1.0.5 目录重构后路径未更新，导致 meowcat 完全无法 import。

## 修复内容

| 文件                          | 变更                                 |
| ----------------------------- | ------------------------------------ |
| `meowcat/__init__.py` L150    | `.parent` → `.parent.parent`         |
| `pyproject.toml`              | version 1.0.5 → 1.0.6               |

- 根因: 源码从 `meowcat/` 根目录移至 `meowcat/meowcat/` 子目录后，
  `__init__.py` 的 `pyproject.toml` 查找路径少了一层。
- 影响: `from meowcat import ...` 抛 `FileNotFoundError`，全部 567 个
  测试无法运行。
- 修复: `pathlib.Path(__file__).resolve().parent.parent` 正确指向
  `meowcat/pyproject.toml`。

## 子版本进度

| 子版本 | 主题             | 状态 |
| ------ | ---------------- | ---- |
| —      | P0 version path  | ✅   |
