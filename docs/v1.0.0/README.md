# meowcat v1.0.0 — 首个独立版本

> meowcat 与 meowagent 版本号从此分离。meowcat 从 1.0.0 起步，
> meowagent 继续 0.5.x 线（当前 0.5.32）。

## 子版本进度

| 子版本 | 内容                                | 状态 |
| ------ | ----------------------------------- | ---- |
| v1.0.0 | 版本独立 + 公开 API 清理 + 文档重组 | ✅   |
| v1.0.1 | CatBase 统一（删除 KittenBase）     | ✅   |
| v1.0.2 | Colony 猫群容器                     | ✅   |

## v1.0.0 交付

### 1. 版本解耦

- `meowcat/pyproject.toml`: version 设为 `1.0.0`，`requires-python` 降为 `>=3.10`
- `meowcat/__init__.py`: 从自身 `pyproject.toml` 读取版本号，不再依赖 meowagent

### 2. 公开 API 清理

- **移除** `Pathways` 从公开导出（v0.5.27 已废弃，`pathways.py` 自身保留供向后兼容）
- `meowcat/__init__.py` `__all__` 中移除 `"Pathways"`

### 3. Bug 修复

- `meowcat/__main__.py`: 脚手架模板 `cat.process_message()` → `cat.run_loop("conversation", ...)`（`process_message` 不存在于 CatBase）

### 4. PEP 561 类型标记

- 新增 `meowcat/py.typed` 空文件，使 mypy/pyright 能对该包做类型检查

### 5. 文档重组

- 所有旧版本文档移入 `docs/meowagent/`（因历史版本号均为 meowagent 线）
- `docs/meowcat/` 下从 v1.0.0 开始维护独立版本记录
- `docs/架构/` 中接入指南 API 示例已修正

## 验收

- [x] `meowcat.__version__` → `"1.0.0"`
- [x] `"Pathways" in meowcat.__all__` → `False`
- [x] 530 个测试全部通过
- [x] `python -m meowcat new test-cat` 生成代码可运行
