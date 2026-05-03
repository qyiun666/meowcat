# v1.0.14 — Cat Lifecycle Hooks（生命周期钩子）

> 创建日期: 2026-05-03 | 基版本: v1.0.13
> 原则: 一版一事；框架层只放"每只猫都需要的东西"；不污染器官体系

## 定位

Organ 的 Protocol 定义了 `build_system_prompt()` / `cancel_current()` 等生命周期方法，但都在器官内部。Cat 级别缺少 "启动时做什么" "关闭时做什么" 的统一入口。

Lifecycle Hooks 为 CatBase 提供 `on_start(hook)` / `on_shutdown(hook)` 两个注册点，让初始化 Gateway、连接 DB、保存状态等操作有了框架级的挂载位置。

## 改动规模

| 指标     | 值                           |
| -------- | ---------------------------- |
| 修改文件 | `assembly.py`, `__init__.py` |
| 新增文件 | 无                           |
| 代码量   | ~40 行                       |
| 测试量   | 12 个                        |
| 破坏性   | 无（纯新增机制）             |

## 进度

- [x] design.md
- [x] 开发
- [x] 测试
- [ ] review.md

## 相关文档

- [design.md](design.md) — 架构设计、接口定义
- [tasks.md](tasks.md) — 任务拆解 + 验收清单
