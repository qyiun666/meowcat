# meowcat v1.0.5 — 文件超行拆分

> 纯重构，不新增功能。来自 v1.0.0 review.md 未解决问题。

## 概述

`protocols.py`（622 行）超出 500 行限制，按类别拆分为三个独立子模块。

## 拆分方案

| 原文件         | 原行数 | 拆分为                                    | 各行数 |
| -------------- | ------ | ----------------------------------------- | ------ |
| `protocols.py` | 622    | `protocols.py` (基础+Pipeline+Kitten+Cat) | 229    |
|                |        | `protocols_brain.py` (脑区+LLM+Growth)    | 288    |
|                |        | `protocols_sense.py` (感官)               | 92     |
|                |        | `protocols_storage.py` (存储)             | 83     |

所有文件 ≤500 行。

## 兼容性

- `from meowcat import ...` 全部 25 个 Protocol 路径不变
- `from meowcat.protocols import ...` 路径不变（re-export）
- 556 regression tests passed
- 新增文件数: 3 | 删除文件数: 0

## 子版本进度

| 子版本 | 主题     | 状态 |
| ------ | -------- | ---- |
| —      | 超行拆分 | ✅   |
