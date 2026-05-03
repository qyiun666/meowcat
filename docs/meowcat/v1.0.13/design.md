# v1.0.13 设计文档 — Signal Middleware（信号中间件）

> 来源: `.qoder/plans/meowcat-v1.0.10-roadmap.md` v1.0.13 章节
> 架构参考: `docs/架构/00-meowcat-框架架构.md`

---

## 1. 设计目标

`signal()` 是框架最核心的原语 — 所有器官间通信的必经之路。当前无拦截点，日志/追踪/限流全部需要侵入器官代码。Middleware 提供框架级的非侵入拦截机制。

---

## 2. 核心设计

### 2.1 SignalCall — 信号上下文

```python
@dataclass(frozen=True)
class SignalCall:
    from_organ: Organ       # (category, name)
    to_organ: Organ         # (category, name)
    method: str             # 被调方法名
    args: tuple[Any, ...]   # 位置参数
    kwargs: dict[str, Any]  # 关键字参数
    timestamp: float        # time.monotonic() 用于计算耗时
```

### 2.2 SignalMiddleware Protocol

```python
class SignalMiddleware(Protocol):
    async def before(self, ctx: SignalCall) -> SignalCall | None:
        """signal 执行前。返回 None 则短路（阻止执行）。"""
        ...

    async def after(self, ctx: SignalCall, result: Any) -> Any:
        """signal 执行后。可修改/包装返回值。"""
        ...

    async def on_error(self, ctx: SignalCall, error: Exception) -> None:
        """signal 抛出异常时调用（通知，不吞异常）。"""
        ...
```

### 2.3 集成到 Nervous.signal()

```
signal(from, to, method, *args, **kwargs)
  │
  ├── 1. 现有校验 (forbidden_methods → wiring → protocol → write_perms)
  ├── 2. 构造 SignalCall
  ├── 3. before 链: 依次调用所有 middleware.before(ctx)
  │       └── 任一返回 None → 短路，返回 None
  ├── 4. emit nerve.signal 事件
  ├── 5. 执行目标方法 (try/except)
  │       ├── 成功 → after 链: 依次调用 middleware.after(ctx, result)
  │       └── 异常 → on_error 链: 依次调用 middleware.on_error(ctx, e) → re-raise
  └── 6. 返回最终结果
```

### 2.4 CatBase 入口

```python
class CatBase:
    def use_middleware(self, mw: SignalMiddleware) -> None:
        """注册一个 signal 中间件。按注册顺序执行。"""
        if self._nervous is None:
            raise RuntimeError("middleware unavailable — enable_wiring=False")
        self._nervous._middleware.append(mw)
```

---

## 3. 内置中间件

| 中间件            | 说明                                                 | 位置                    |
| ----------------- | ---------------------------------------------------- | ----------------------- |
| `ContextInjector` | 自动将 SignalContext 注入每次 signal（Gateway 依赖） | `meowcat/middleware.py` |
| `SignalLogger`    | 记录每次 signal(from, to, method, duration)          | `meowcat/middleware.py` |
| `RateLimiter`     | 限制特定 organ 方法的调用频率                        | `meowcat/middleware.py` |
| `TimeoutGuard`    | 超时自动 abort                                       | `meowcat/middleware.py` |

---

## 4. 设计原则

- **零开销关闭** — 无中间件时 signal() 路径不增加任何判断（空列表 for 循环零迭代）
- **不改变 signal() 签名** — Middleware 是装饰器模式，不入侵现有接口
- **Middleware stack 在 Nervous 内** — 不污染 OrganHost 或 EventBus
- **on_error 不吞异常** — 仅通知，异常继续向上传播

---

## 5. 改动范围

| 文件                    | 改动                                         | 行数 |
| ----------------------- | -------------------------------------------- | ---- |
| `meowcat/nervous.py`    | SignalCall + SignalMiddleware + \_middleware | +30  |
| `meowcat/middleware.py` | 新建: 4 个内置中间件                         | +50  |
| `meowcat/assembly.py`   | CatBase.use_middleware()                     | +6   |
| `meowcat/__init__.py`   | 导出新类型                                   | +3   |
| **合计**                |                                              | ~89  |

---

## 6. 测试策略 (~12 个)

| 测试                                       | 覆盖         |
| ------------------------------------------ | ------------ |
| 无中间件时 signal 正常                     | 零开销验证   |
| before 返回 None 短路                      | 短路机制     |
| before → after 正常链式调用                | 正常拦截流程 |
| 多个中间件按注册顺序执行                   | 执行顺序     |
| on_error 被调用且异常仍传播                | 错误通知     |
| after 可修改返回值                         | 返回值包装   |
| SignalCall 属性正确                        | 上下文完整性 |
| ContextInjector 注入 SignalContext         | 内置中间件   |
| SignalLogger 记录日志                      | 内置中间件   |
| RateLimiter 限流                           | 内置中间件   |
| TimeoutGuard 超时 abort                    | 内置中间件   |
| enable_wiring=False 时 use_middleware 报错 | 边界条件     |
