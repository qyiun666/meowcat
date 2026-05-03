# v1.0.10 任务拆解 + 进度跟踪

> 来源: `.qoder/plans/meowcat-v1.0.10-roadmap.md` v1.0.10 章节

## 任务清单

### 1. Gateway 协议定义: `gateway/protocol.py`

- [x] `SignalContext` dataclass（frozen, session_id/platform/user_id/timestamp）
- [x] `GatewayProtocol` Protocol（start/stop/mount_adapter/unmount_adapter）
- [x] `AdapterProtocol` Protocol（name/serve/send/stream_chunk/stream_end/stop）

### 2. Gateway 实现: `gateway/__init__.py`

- [x] `Gateway` 类 — 持有 cat + \_adapters dict
- [x] `mount_adapter(adapter)` — 挂载，同名覆盖
- [x] `unmount_adapter(name)` — 卸载
- [x] `start()` — 并行启动所有 Adapter.serve()
- [x] `stop()` — 停止所有 Adapter
- [x] `_on_message(text, ctx)` — 注入 cat.perceive()，返回回复
- [x] `_on_stream(text, ctx)` — 流式版本

### 3. HttpAdapter: `gateway/http_adapter.py`

- [x] `HttpAdapter` 类（host/port）
- [x] `serve(on_message, on_stream)` — asyncio HTTP server
- [x] `send(output, session_id)` — 存 buffer / HTTP response
- [x] `stream_chunk` / `stream_end` — SSE 推送
- [x] `stop()` — 关闭 server

### 4. WsAdapter: `gateway/ws_adapter.py`

- [x] `WsAdapter` 类（host/port）
- [x] `serve(on_message, on_stream)` — asyncio WebSocket server
- [x] 双向帧收发
- [x] `stream_chunk` / `stream_end`
- [x] `stop()`

### 5. WebhookAdapter: `gateway/webhook_adapter.py`

- [x] `WebhookAdapter` 类（host/port/path）
- [x] `verify_signature(headers, body)` — 可被子类重写
- [x] `parse_message(body)` — 可被子类重写
- [x] `serve(on_message, on_stream)` — HTTP POST 接收
- [x] `stop()`

### 6. CliAdapter: `gateway/cli_adapter.py`

- [x] `CliAdapter` 类
- [x] `serve(on_message, on_stream)` — stdin.readline 循环
- [x] `send` — print()
- [x] `stream_chunk` / `stream_end` — print(flush=True)
- [x] `stop()`

### 7. IpcAdapter: `gateway/ipc_adapter.py`

- [x] `IpcAdapter` 类（socket_path）
- [x] `serve(on_message, on_stream)` — Unix socket server
- [x] `send` / `stream_chunk` / `stream_end`
- [x] `stop()`

### 8. 公开 API 导出: `meowcat/__init__.py`

- [x] 导出 `Gateway`, `GatewayProtocol`, `AdapterProtocol`, `SignalContext`
- [x] 导出各 Adapter 类: `HttpAdapter`, `WsAdapter`, `WebhookAdapter`, `CliAdapter`, `IpcAdapter`

### 9. 测试: `tests/test_v1010_gateway.py` (~30 tests)

- [x] TestSignalContext (3): 构造 / 不可变 / 字段类型
- [x] TestProtocols (5): GatewayProtocol isinstance / AdapterProtocol isinstance / name 属性
- [x] TestGateway (4): mount / unmount / 不存在noop / 同名覆盖
- [x] TestHttpAdapter (4): POST 收发 / JSON 解析 / 错误响应 / SSE
- [x] TestWsAdapter (2): 连接 / 消息帧 / 流式帧 / 断开
- [x] TestCliAdapter (4): stdin 输入 / stdout 输出 / stream 输出 / stream_end
- [x] TestWebhookAdapter (5): 签名验证 / 消息解析 / 缺失字段 / 回调 / 签名拒绝
- [x] TestIpcAdapter (2): 连接 / 收发 / 多轮消息
- [x] TestMultiAdapter (3): 两 Adapter 共存 / 独立 session_id / 独立 platform
- [x] TestSignalContextInjection (3): perceive extras 透传 / Gateway集成 / 字段类型
- [x] TestWsFrameEncoding (3): 编码 / 解码 / accept 计算

### 10. 版本号

- [x] `meowcat/pyproject.toml`: 1.0.9 → 1.0.10

---

## 验收清单

- [x] 所有新增测试通过（38 个）
- [x] 已有 635 tests 零回归 (624 通过 + 16 预存失败与本次无关)
- [x] Gateway + HttpAdapter + CliAdapter 最小可用: 启动 HTTP server + CLI 同时工作
- [x] SignalContext 通过 perceive extras 正确注入
- [x] 框架层零 import meowagent
- [x] 零新增 pip 依赖（纯 asyncio + 标准库）
- [x] `from meowcat.gateway import Gateway, HttpAdapter, CliAdapter` 可用
- [x] `from meowcat import Gateway, SignalContext` 可用

---

## 开发顺序

```
1. protocol.py     → 先定协议（SignalContext + 两个 Protocol）
2. __init__.py     → Gateway 实现（依赖协议）
3. http_adapter.py → 最简单的 Adapter，验证 Gateway 集成
4. cli_adapter.py  → 第二简单
5. ws_adapter.py   → 流式支持
6. webhook_adapter.py → 骨架
7. ipc_adapter.py  → 最后
8. __init__.py     → 公开 API 导出
9. tests           → 测试覆盖
```
