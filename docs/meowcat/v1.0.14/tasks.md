# v1.0.14 任务清单 — Cat Lifecycle Hooks

> 创建日期: 2026-05-03 | 基版本: v1.0.13

---

## 任务拆解

- [x] 1. `assembly.py` 定义 CatHook 类型别名
- [x] 2. `assembly.py` CatBase.\_\_init\_\_ 新增 \_start_hooks / \_shutdown_hooks 列表
- [x] 3. `assembly.py` CatBase 新增 on_start(hook) / on_shutdown(hook) 方法
- [x] 4. `assembly.py` 修改 start() — emit 后依次调用 on_start hooks
- [x] 5. `assembly.py` 修改 shutdown() — 逆序调用 on_shutdown hooks 后 emit
- [x] 6. `__init__.py` 导出 CatHook
- [x] 7. 创建 v1.0.14 文档（design / tasks / README）
- [x] 8. 编写测试（12 个）
- [x] 9. 运行全部测试验证零回归

---

## 验收清单

- [x] CatHook 类型正确：`Callable[[CatBase], Awaitable[None]]`
- [x] on_start(hook) 注册后 start() 依次调用
- [x] on_shutdown(hook) 注册后 shutdown() 逆序调用
- [x] start() 先发射 lifecycle.start 事件，后执行 hooks
- [x] shutdown() 先执行 hooks，后发射 lifecycle.shutdown 事件
- [x] 无 hooks 时 start()/shutdown() 行为完全不变（向后兼容）
- [x] hook 接收到正确的 CatBase 实例引用
- [x] CatHook 可从 `meowcat` 正确导入
- [x] 全部现有测试通过（零回归）
- [x] 新测试全部通过 (12 passed)
