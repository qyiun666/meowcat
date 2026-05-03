# v1.0.10 设计文档 — Gateway 体系

> 来源: `.qoder/plans/meowcat-v1.0.10-roadmap.md` v1.0.10 章节
> 架构参考: `docs/架构/00-meowcat-框架架构.md`

---

## 1. 设计目标

为 meowcat 框架添加 **Gateway 子系统** — 猫与外部世界的唯一 I/O 抽象层。所有外部输入/输出经 Gateway 收拢，内部神经系统无感知外部协议差异。

核心价值：

- **解耦**：猫的内部器官不知道外面是 HTTP 还是 WebSocket
- **多平台**：同一只猫同时服务 CLI / 飞书 / 桌面 App，不同 `session_id` 索引
- **流式**：原生支持流式推送（WebSocket / SSE），不依赖应用层
- **可扩展**：应用层可以 `WebhookAdapter` 为基类，子类化飞书/微信适配器

---

## 2. 架构概览

### 2.1 子系统位置

Gateway 是 Cat 的第五子系统，与 OrganHost / EventBus / Nervous / ReflexArc 平级：

```
                    CatBase
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
OrganHost          EventBus           Nervous
(器官容器)          (事件总线)          (信号分发)
[Pluggable]            │              ├── Wiring
    │                  │              └── probe
    │    ┌─────────────┼──────────────┘
    │    │             │
    │ ReflexArc    Gateway (v1.0.10 新增)
    │ (反射弧)     ├── HttpAdapter
    │              ├── WsAdapter
    │              ├── WebhookAdapter
    │              ├── CliAdapter
    │              └── IpcAdapter
```

### 2.2 拓扑关系

```
                              ┌─ HttpAdapter ────────┐
  HTTP POST /chat ──────────→ ├─ WsAdapter ──────────┤
  WebSocket ws://... ───────→ ├─ WebhookAdapter ─────┤──→ Gateway ──→ Eyes.see()
  飞书回调 ──────────────────→ ├─ CliAdapter ────────┤       │        / Ears.hear()
  stdin/stdout ─────────────→ ├─ IpcAdapter ─────────┘       │           │
  桌面 App ─────────────────→                                │      猫的神经系统
                                                             │           │
                                                             │           ▼
                                                      Mouth.speak() / Purr.stream()
                                                             │
                                                      Gateway.respond() → 对应 Adapter → 外部
```

**1 只猫 : 1 个 Gateway : N 个 Adapter。** Colony 下每只猫独立进程，各自 Gateway。

---

## 3. 模块结构

```
meowcat/gateway/                   (新增包)
├── __init__.py           # Gateway + AdapterProtocol + SignalContext 导出
│                         #   子模块 re-export
├── protocol.py           # GatewayProtocol / AdapterProtocol / SignalContext
├── http_adapter.py       # HttpAdapter (POST /chat)
├── ws_adapter.py         # WsAdapter (WebSocket 双向流)
├── webhook_adapter.py    # WebhookAdapter (飞书/微信回调骨架)
├── cli_adapter.py        # CliAdapter (stdin/stdout)
└── ipc_adapter.py        # IpcAdapter (Unix socket)
```

**文件行数约束**：每个文件 ≤150 行，包总计 ~250 行。

---

## 4. 核心协议

### 4.1 SignalContext — 会话上下文

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SignalContext:
    """随每次外部消息注入猫的上下文。所有 signal 隐式携带。"""
    session_id: str      # "cli-20260503" | "feishu-group-abc" | "desktop-zt"
    platform: str        # "cli" | "http" | "ws" | "feishu" | "wechat" | "desktop"
    user_id: str         # 外部用户标识
    timestamp: str       # ISO 8601 时间戳
```

**核心设计**：同一只猫，同一个 Hippocampus，不同 `session_id` 对应不同平台。

```
  CLI 用户   → session_id="cli-20260503"    ┐
  飞书群聊   → session_id="feishu-grp-abc"  ├── 同一只猫 → 同一个 Hippocampus
  桌面 App   → session_id="desktop-zt"       ┘
```

Hippocampus 的 `locate(msg, session_id)` 和 `remember(...)` 已经接受 `session_id` 参数。Gateway 做的事只是：收到消息 → 构造 SignalContext → 注入到 cat。**不需要单独的 Session 模块。**

### 4.2 GatewayProtocol — 网关协议

```python
class GatewayProtocol(Protocol):
    """网关协议 — 唯一外部 I/O 入口。1:1 绑定一只猫。"""

    async def start(self, cat: CatBase) -> None:
        """启动网关，开始接收所有 Adapter 的消息。"""
        ...

    async def stop(self) -> None:
        """关闭网关，停止所有 Adapter。"""
        ...

    def mount_adapter(self, adapter: AdapterProtocol) -> None:
        """挂载一个协议适配器。同名覆盖。"""
        ...

    def unmount_adapter(self, name: str) -> None:
        """卸载一个协议适配器。不存在则 no-op。"""
        ...
```

### 4.3 AdapterProtocol — 适配器协议

```python
class AdapterProtocol(Protocol):
    """适配器协议 — Gateway 的插件，负责一种协议/管道的收发。

    每个 Adapter 实例独立管理自己的连接/监听。Gateway 不关心
    Adapter 内部如何收发，只要求它通过回调桥接到猫的神经系统。
    """

    name: str

    async def serve(
        self,
        on_message: Callable[[str, SignalContext], Awaitable[str | None]],
        on_stream: Callable[[str, SignalContext], Awaitable[AsyncIterator[str] | None]],
    ) -> None:
        """启动监听循环。收到外部消息时回调 on_message，阻塞直到 stop()。

        Args:
            on_message: 收到完整消息时回调，返回猫的回复文本
            on_stream:  收到流式消息时回调，返回异步迭代器
        """
        ...

    async def send(self, output: str, session_id: str, **meta: Any) -> None:
        """发送完整回复。"""
        ...

    async def stream_chunk(self, chunk: str, session_id: str, **meta: Any) -> None:
        """发送流式块。"""
        ...

    async def stream_end(self, session_id: str, **meta: Any) -> None:
        """流式结束标记。"""
        ...

    async def stop(self) -> None:
        """停止监听。"""
        ...
```

### 4.4 协议间的信号流

```
  Adapter.serve()                    Gateway                     Cat 神经系统
  ────────────────                  ─────────                  ─────────────
  on_message(text, ctx) ──────────→ Gateway._on_input()
                                      │
                                      ├─ 构造 SignalContext
                                      ├─ cat.perceive(text, context=ctx)
                                      │     │
                                      │     ├─ Eyes.see() / Ears.hear()
                                      │     └─ ... → Mouth.speak()
                                      │              │
                                      │         output_text
                                      │              │
                                      ├─ Gateway._on_output(text, ctx)
                                      │     │
                                      └─────├─ adapter.send(text, ctx.session_id)
                                            └─ (或 stream_chunk 逐块)
```

---

## 5. Gateway 实现

### 5.1 Gateway 类（`gateway/__init__.py`）

```python
class Gateway:
    """猫的皮肤 — 外部 I/O 的唯一入/出口。"""

    def __init__(self, cat: CatBase) -> None:
        self.cat = cat
        self._adapters: dict[str, AdapterProtocol] = {}

    def mount_adapter(self, adapter: AdapterProtocol) -> None:
        self._adapters[adapter.name] = adapter

    def unmount_adapter(self, name: str) -> None:
        self._adapters.pop(name, None)

    async def start(self) -> None:
        """启动所有 Adapter 的 serve() 循环。"""
        tasks = []
        for adapter in self._adapters.values():
            tasks.append(asyncio.create_task(
                adapter.serve(self._on_message, self._on_stream)
            ))
        # await asyncio.gather(*tasks) — 所有 Adapter 并行运行

    async def stop(self) -> None:
        for adapter in self._adapters.values():
            await adapter.stop()

    async def _on_message(self, text: str, ctx: SignalContext) -> str | None:
        """收到外部消息 → 注入猫 → 返回回复。"""
        async for event in self.cat.perceive(text, context=ctx):
            if isinstance(event, dict) and "output" in event:
                return event["output"]
        return None

    async def _on_stream(self, text: str, ctx: SignalContext) -> AsyncIterator[str] | None:
        """流式版本 — 逐 token 迭代。"""
        # 具体实现取决于 Purr.stream() 的返回
        ...
```

### 5.2 设计约束

| 约束                       | 说明                                                                  |
| -------------------------- | --------------------------------------------------------------------- |
| **非器官**                 | Gateway 不挂载到 OrganHost。它是独立子系统，与 CatBase 组合而非继承   |
| **不入侵信号系统**         | Gateway 使用 `cat.perceive()` 入口，不直接调 `signal()`               |
| **不管理连接**             | Adapter 各自管理自己的 `asyncio.Server` / `WebSocket` 生命周期        |
| **零依赖 meowagent**       | 全部标准库 + asyncio，不加额外 pip 依赖                               |
| **SignalContext 隐式传递** | 不是全局状态，而是每次 `perceive()` 的参数，自然下沉到所有下游 signal |

---

## 6. 各 Adapter 设计

### 6.1 HttpAdapter（`http_adapter.py`）

**职责**: 接受 HTTP POST `/chat` 请求，JSON body 返回 JSON response。

```python
class HttpAdapter:
    name = "http"

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port

    async def serve(self, on_message, on_stream):
        # asyncio.start_server → 每个连接读 JSON body
        # 构造 SignalContext(platform="http", ...)
        # reply = await on_message(text, ctx)
        # 写 JSON response {"reply": reply}
        ...

    async def send(self, output, session_id, **meta):
        # HTTP 无状态的 send 操作: 存到内部 buffer 等下次请求返回
        # 或直接通过 SSE 推送（可选）
        ...
```

**非流式请求/响应模式**。JSON body: `{"message": "..."}`, response: `{"reply": "..."}`。
可选 SSE 支持流式（`Accept: text/event-stream` → `stream_chunk` 逐块推送）。

### 6.2 WsAdapter（`ws_adapter.py`）

**职责**: WebSocket 双向流式对话。

```python
class WsAdapter:
    name = "ws"

    def __init__(self, host: str = "0.0.0.0", port: int = 8001):
        ...

    async def serve(self, on_message, on_stream):
        # asyncio.start_server + websocket handshake
        # 每收到一帧 → on_stream(text, ctx) → 迭代 chunks
        # 每个 chunk → ws.send(chunk)
        # stream_end → ws.send("[DONE]")
        ...

    async def stream_chunk(self, chunk, session_id, **meta):
        # 直接通过已建立的 ws 连接推送
        ...
```

**流式双向**: 客户端 send JSON → 猫处理 → 逐 token 推送回客户端。

### 6.3 WebhookAdapter（`webhook_adapter.py`）

**职责**: 回调骨架。接收 HTTP POST 回调，支持签名验证接口（子类实现）。

```python
class WebhookAdapter:
    name = "webhook"

    def __init__(self, host: str = "0.0.0.0", port: int = 8002, path: str = "/webhook"):
        self.host = host
        self.port = port
        self.path = path

    def verify_signature(self, headers: dict, body: bytes) -> bool:
        """子类重写以添加平台特定验证（飞书/微信）。默认放行。"""
        return True

    def parse_message(self, body: dict) -> tuple[str, str]:
        """从回调 body 提取 (消息文本, 用户ID)。子类重写。"""
        return body.get("message", ""), body.get("user_id", "unknown")

    async def serve(self, on_message, on_stream):
        # HTTP server 监听 POST /webhook
        # verify_signature → parse_message → on_message
        ...
```

**框架层只提供协议管道**。飞书的 token 管理、微信的消息解密 — 全部在应用层子类里：

```python
# meowagent 应用层
class FeishuAdapter(WebhookAdapter):
    name = "feishu"
    platform = "feishu"
    # 加 OAuth token 刷新、卡片消息、消息解密
```

### 6.4 CliAdapter（`cli_adapter.py`）

**职责**: stdin/stdout 对话。替代应用层内嵌的 CLI 循环。

```python
class CliAdapter:
    name = "cli"

    async def serve(self, on_message, on_stream):
        # 循环: stdin.readline() → on_message(text, ctx) → print(reply)
        # SignalContext(platform="cli", session_id="cli-{timestamp}", user_id="cli-user")
        ...

    async def send(self, output, session_id, **meta):
        print(output)

    async def stream_chunk(self, chunk, session_id, **meta):
        print(chunk, end="", flush=True)

    async def stream_end(self, session_id, **meta):
        print()  # 换行
```

### 6.5 IpcAdapter（`ipc_adapter.py`）

**职责**: Unix socket / named pipe，供桌面 App 进程间通信。

```python
class IpcAdapter:
    name = "ipc"

    def __init__(self, socket_path: str = "/tmp/meowcat.sock"):
        self.socket_path = socket_path

    async def serve(self, on_message, on_stream):
        # asyncio.start_unix_server → 读 JSON 行 → on_message
        ...
```

**框架层只提供 Unix socket 管道**。macOS 沙盒、Windows named pipe — 桌面层实现。

---

## 7. 流式输出设计

Gateway 原生支持流式：Mouth 逐句 → `adapter.send()`；Purr 实时进度 → `adapter.stream_chunk()`。

```
  Purr.stream(chunk) ────────→ Gateway._on_stream_chunk(chunk, ctx)
                                         │
                           adapter.stream_chunk(chunk, session_id)
                              │
                   ┌──────────┼──────────┐
                   ▼          ▼          ▼
              WsAdapter   HttpAdapter  CliAdapter
              ws.send()   SSE push     print(chunk, end="")
```

### Adapter 对流式的支持

| Adapter        | send()              | stream_chunk()   | stream_end()   |
| -------------- | ------------------- | ---------------- | -------------- |
| HttpAdapter    | JSON response       | SSE data: chunk  | SSE [DONE]     |
| WsAdapter      | ws.send(json)       | ws.send(chunk)   | ws.send(end)   |
| WebhookAdapter | HTTP 200 + 异步推送 | N/A（回调模式）  | N/A            |
| CliAdapter     | print(text)         | print(chunk,end) | print()        |
| IpcAdapter     | sock.send(json)     | sock.send(chunk) | sock.send(end) |

---

## 8. Gateway 与 CatBase 的集成

### 8.1 当前版本 (v1.0.10)

Gateway 由调用方手动管理生命周期：

```python
from meowcat import create_cat, Gateway
from meowcat.gateway import HttpAdapter, CliAdapter

cat = create_cat("my-cat", cerebrum=MyBrain())
gw = Gateway(cat)
gw.mount_adapter(HttpAdapter(port=8000))
gw.mount_adapter(CliAdapter())

await gw.start()   # 阻塞，所有 Adapter 并行运行
```

### 8.2 未来 (v1.0.14 Lifecycle Hooks)

```python
cat.mount_gateway(gw)
cat.on_start(lambda c: c.gateway.start())
cat.on_shutdown(lambda c: c.gateway.stop())
await cat.start()
```

v1.0.10 不引入 `cat.mount_gateway()`，保持 Gateway 与 CatBase 解耦。v1.0.14 再添加生命周期自动衔接。

### 8.3 perceive() 的 SignalContext 传递

当前 `cat.perceive(input, **extras)` 的 `extras` 会被透传给 ReflexArc。SignalContext 通过 `extras["context"]` 注入：

```python
# Gateway._on_message() 内部
async for event in self.cat.perceive(text, context=ctx):
    ...
```

ReflexArc 将 `context` 传递到 Pipeline stages，每个 Stage 的 `ctx.context` 可取出 `SignalContext`。这是自然下沉 — 不需要改 signal() 签名。

---

## 9. 框架层 vs 应用层边界

| 功能           | 框架层 (meowcat)                | 应用层 (meowagent)            |
| -------------- | ------------------------------- | ----------------------------- |
| HTTP 管道      | HttpAdapter（POST /chat JSON）  | —                             |
| WebSocket 管道 | WsAdapter（双向帧）             | —                             |
| 回调骨架       | WebhookAdapter（验证+解析接口） | FeishuAdapter / WechatAdapter |
| CLI 管道       | CliAdapter（stdin/stdout）      | TUI 富文本、历史补全          |
| IPC 管道       | IpcAdapter（Unix socket）       | macOS 沙盒、Windows pipe      |
| OAuth / token  | —                               | 应用层子类实现                |
| 消息格式/解密  | —                               | 应用层子类实现                |
| 卡片/富文本    | —                               | 应用层子类实现                |

---

## 10. 改动范围

| 文件                                 | 改动                                              | 行数        |
| ------------------------------------ | ------------------------------------------------- | ----------- |
| `meowcat/gateway/__init__.py`        | Gateway 类 + 导出                                 | ~50         |
| `meowcat/gateway/protocol.py`        | GatewayProtocol + AdapterProtocol + SignalContext | ~40         |
| `meowcat/gateway/http_adapter.py`    | HttpAdapter                                       | ~50         |
| `meowcat/gateway/ws_adapter.py`      | WsAdapter                                         | ~40         |
| `meowcat/gateway/webhook_adapter.py` | WebhookAdapter                                    | ~30         |
| `meowcat/gateway/cli_adapter.py`     | CliAdapter                                        | ~25         |
| `meowcat/gateway/ipc_adapter.py`     | IpcAdapter                                        | ~20         |
| `meowcat/__init__.py`                | 导出 Gateway + 协议                               | +5          |
| **合计**                             |                                                   | **~260 行** |

**零修改**（纯新增子系统，不改任何现有文件）:

- `assembly.py` — 不改
- `nervous.py` — 不改
- `biology.py` — 不改
- `anatomy.py` — 不改
- `host.py` — 不改

---

## 11. 测试策略 (~30 个)

| 测试组                | 数量 | 覆盖                                |
| --------------------- | ---- | ----------------------------------- |
| SignalContext         | 3    | 构造 / 不可变 / 默认值              |
| GatewayProtocol 校验  | 2    | isinstance 检查 / 缺失方法          |
| AdapterProtocol 校验  | 3    | name / serve / send / stream        |
| Gateway mount/unmount | 3    | 挂载 / 卸载 / 同名覆盖              |
| HttpAdapter 收发      | 4    | POST / JSON / 错误 / SSE            |
| WsAdapter 收发        | 4    | 连接 / 消息 / 流式 / 断开           |
| CliAdapter 收发       | 3    | stdin/stdout / context / stream     |
| WebhookAdapter        | 3    | 验证 / 解析 / 回调                  |
| Multi-adapter         | 3    | 两个 Adapter 共存 / 独立 session_id |
| SignalContext 注入    | 2    | perceive extras / Pipeline 可访问   |

---

## 12. 关键决策

| 决策                                    | 理由                                                     |
| --------------------------------------- | -------------------------------------------------------- |
| Gateway 不是 Organ                      | 它是 I/O 管道，不是神经器官。不污染器官体系              |
| 不创建 Session 模块                     | Hippocampus 已有 session_id 参数，复用即可               |
| 框架不实现飞书/微信                     | OAuth/解密/卡片 → 全部应用层子类。框架只管管道           |
| CliAdapter 不依赖 readline              | readline 是可选依赖，CLI 默认用 stdin.readline()         |
| WsAdapter 用纯 asyncio                  | 不加 websockets 依赖。框架层只提供协议管道               |
| Gateway 不管理 Adapter 生命周期         | 每个 Adapter 自己 `serve()` + `stop()`，Gateway 只做聚合 |
| SignalContext 通过 perceive extras 注入 | 不修改 signal() 签名，不污染热路径                       |
