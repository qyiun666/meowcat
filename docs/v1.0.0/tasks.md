# meowcat v1.0.0 — 任务拆解

## 任务清单

### T1: 版本解耦

| 项         | 文件                            | 内容                                      |
| ---------- | ------------------------------- | ----------------------------------------- |
| version    | `meowcat/pyproject.toml`        | `0.5.31` → `1.0.0`                        |
| requires   | `meowcat/pyproject.toml`        | `>=3.12` → `>=3.10`                       |
| 读版本路径 | `meowcat/__init__.py`           | `parent.parent` → `parent`                |
| P-01 规则  | `.qoder/rules/P-01-架构导航.md` | 移除"meowcat 与 meowagent 版本号永远一致" |

**验收**: `meowcat.__version__` → `"1.0.0"` ✓

### T2: 脚手架模板修复

| 项   | 文件                  | 内容                                                          |
| ---- | --------------------- | ------------------------------------------------------------- |
| 模板 | `meowcat/__main__.py` | `cat.process_message()` → `cat.run_loop("conversation", ...)` |

**验收**: 模板生成代码可运行 ✓

### T3: PEP 561 + API 清理

| 项            | 文件                  | 内容                       |
| ------------- | --------------------- | -------------------------- |
| py.typed      | `meowcat/py.typed`    | 新建空文件                 |
| 移除 Pathways | `meowcat/__init__.py` | import 和 `__all__` 中移除 |

**验收**: `py.typed` 存在，`"Pathways" not in meowcat.__all__` ✓

### T4: 文档重组

| 项             | 内容                                              |
| -------------- | ------------------------------------------------- |
| 历史版本       | `docs/v*/` → `docs/meowagent/v*/`                 |
| meowcat 文档树 | 新建 `docs/meowcat/v1.0.0/` 四件套                |
| 接入指南修正   | `docs/架构/02-应用层接入指南.md` 5处 API 示例修正 |
| 框架架构更新   | `docs/架构/00-meowcat-框架架构.md` 版本标注       |
| 过期文档清理   | `docs/meowcat/` → `docs/archive/`                 |

**验收**: 文档结构清晰，无重复内容 ✓

### T5: 回归测试

| 项   | 命令                       | 结果  |
| ---- | -------------------------- | ----- |
| 测试 | `pytest meowcat/tests/ -v` | 530 ✓ |

## 进度

| 任务 | 状态 |
| ---- | ---- |
| T1   | ✅   |
| T2   | ✅   |
| T3   | ✅   |
| T4   | ✅   |
| T5   | ✅   |
