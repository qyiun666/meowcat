# meowcat 框架层路线图 v1.0.10 → v1.0.14

> 创建日期: 2026-05-03 | 基版本: v1.0.9
> 原则: 一版一事；框架层只放"每只猫都需要的东西"；不污染器官体系

---

## 判定标准

| ✅ 框架层 | 纯骨架 — 协议、管道、事件、生命周期                 |
| --------- | --------------------------------------------------- |
| ❌ 应用层 | 特定平台逻辑（OAuth/消息格式）、需要具体 LLM 的行为 |

---

## 版本路线

```
v1.0.9  当前                             2026-05-02  22路径 5链路 5闭环 1loopseq
v1.0.10 Gateway 体系 (皮肤)               ~250行      新子系统
v1.0.11 synthesize Path (世界观综合)      ~3行       一行路径 ✅
v1.0.12 Colony 联邦 (跨主机)             ~150行      增强
v1.0.13 Signal Middleware (信号中间件)    ~60行       新机制
v1.0.14 Cat Lifecycle Hooks (生命周期钩)  ~40行       新机制
v1.0.15 长流程 (Long-Running Workflow)    ~90行       编排持久化
───────
合计                                      ~600行      6个版本
```

---

## v1.0.10 — Gateway 体系（猫的皮肤）

> 每只猫必然有一个"外面"。Gateway 是猫与外部世界之间的唯一 I/O 抽象层，所有协议适配器插在同一个 Gateway 上。

### 架构

```
                              ┌─ HttpAdapter ────────┐
  HTTP POST /chat ──────────→ ├─ WsAdapter ──────────┤
  WebSocket ws://... ───────→ ├─ WebhookAdapter ─────┤──→ Gateway ──→ Eyes.see()
  飞书回调 ──────────────────→ ├─ CliAdapter ────────┤       │           │
  stdin/stdout ─────────────→ ├─ IpcAdapter ─────────┘       │           ▼
  桌面 App ─────────────────→                               │      猫的神经系统
                                                             │           │
                                                             │           ▼
                                                      Mouth.speak() / Purr.stream()
                                                             │
                                                      Gateway.respond() → 对应 Adapter → 外部
```

**1 只猫 : 1 个 Gateway : N 个 Adapter。** Colony 下每只猫独立进程，各自 Gateway。

### 模块结构

```
meowcat/gateway/
├── __init__.py           # Gateway + AdapterProtocol 导出
├── protocol.py           # GatewayProtocol / AdapterProtocol / SignalContext
├── http_adapter.py       # HttpAdapter (POST /chat)
├── ws_adapter.py         # WsAdapter (WebSocket 双向流)
├── webhook_adapter.py    # WebhookAdapter (飞书/微信回调)
├── cli_adapter.py        # CliAdapter (stdin/stdout 显式化)
└── ipc_adapter.py        # IpcAdapter (Unix socket, 桌面 App 入口)
```

### GatewayProtocol

```python
class GatewayProtocol(Protocol):
    """网关协议 — 唯一外部 I/O 入口。1:1 绑定一只猫。"""

    async def start(self, cat: CatBase) -> None: ...
    async def stop(self) -> None: ...
    def mount_adapter(self, adapter: AdapterProtocol) -> None: ...
    def unmount_adapter(self, name: str) -> None: ...
```

### AdapterProtocol

```python
class AdapterProtocol(Protocol):
    """适配器协议 — Gateway 的插件，负责一种协议/管道的收发"""

    name: str
    async def serve(self, on_message: Callable, on_stream: Callable) -> None: ...
    async def send(self, output: str, session_id: str, **meta) -> None: ...
    async def stream_chunk(self, chunk: str, session_id: str, **meta) -> None: ...
    async def stream_end(self, session_id: str, **meta) -> None: ...
```

### SignalContext — 会话 = session_id 隐式多平台索引

```python
@dataclass(frozen=True)
class SignalContext:
    """随每次外部消息注入猫的上下文。所有 signal 隐式携带。"""
    session_id: str      # "cli-20260503" | "feishu-group-abc" | "desktop-zt"
    platform: str        # "cli" | "feishu" | "wechat" | "desktop"
    user_id: str
    timestamp: str
```

**核心设计**：同一只猫，同一个 Hippocampus，不同 session_id 对应不同平台。

```
  CLI 用户   → session_id="cli-20260503"    ┐
  飞书群聊   → session_id="feishu-grp-abc"  ├── 同一只猫 → 同一个 Hippocampus
  桌面 App   → session_id="desktop-zt"       ┘
```

Hippocampus 的 `locate()` / `remember()` 已经接受 session_id 参数。Gateway 做的事只是：收到消息 → 构造 SignalContext → 注入到 cat → 后续所有 signal 自然携带 context。**不需要单独的 Session 模块。**

### 流式输出

Gateway 原生支持流式：Mouth 逐句 → `adapter.send()`；Purr 实时进度 → `adapter.stream_chunk()`。WsAdapter 通过 WebSocket 逐帧推送，HttpAdapter 可选 SSE。

### 各 Adapter 职责

| Adapter        | 用途          | 框架层实现                    | 应用层扩展                                    |
| -------------- | ------------- | ----------------------------- | --------------------------------------------- |
| HttpAdapter    | REST 对话     | POST /chat JSON 请求/响应     | —                                             |
| WsAdapter      | 流式对话      | WebSocket 双向帧              | —                                             |
| WebhookAdapter | 飞书/微信回调 | HTTP POST 接收 + 验证骨架     | `FeishuAdapter(WebhookAdapter)` 加 OAuth/卡片 |
| CliAdapter     | 终端对话      | stdin readline / stdout print | TUI 富文本（meowagent）                       |
| IpcAdapter     | 桌面 App      | Unix socket / named pipe      | macOS 沙盒、Windows named pipe（桌面层）      |

> 框架层只提供协议管道。飞书的 token 管理、微信的消息解密、桌面的窗口绑定 — 全部在应用层子类里。

### 测试

~30 个（协议校验 + 5 个适配器收发 + 流式 + SignalContext 注入 + 多适配器共存）

---

## v1.0.11 — synthesize Path（世界观综合）

> CORTEX 已有 `synthesize()` 方法（CortexProtocol §260），BrainStem 已有到 CORTEX 的边（biology.py §178）。唯一缺的是一行 Path。

### 改动

`path.py` BUILTIN_PATHS 新增一行：

```python
Path("synthesize", BRAINSTEM, CORTEX,
     "synthesize", "read", "世界观综合"),
```

### 说明

框架不关心 `synthesize()` 的内部实现 — 可以是 LLM 摘要、规则聚类、纯统计。框架只管"脑干下令 → 皮层执行"这条神经通路。

`brainstem→cortex` 边已有（biology.py:178），`CortexProtocol.synthesize()` 已定义（protocols_brain.py:260）。**零协议改动，零器官改动。**

### 测试

~5 个

---

## v1.0.12 — Colony 联邦（跨主机通信）

> Colony 已是多进程（每只主猫独立进程）。联邦让不同主机的 Colony 之间互相感知、通信。

### 架构

```
  主机 A                          主机 B
  ┌────────────────┐             ┌────────────────┐
  │  Colony-A      │             │  Colony-B      │
  │  Cat "alpha"   │             │  Cat "beta"    │
  │  Cat "gamma"   │             │  Cat "delta"   │
  └───────┬────────┘             └───────┬────────┘
          │                              │
          └──── FederationTransport ─────┘
               (TCP / Redis pub/sub)
```

### 改动

`colony.py` 新增联邦能力：

```python
class FederationTransport(Protocol):
    """跨 Colony 通信传输层"""
    async def publish(self, topic: str, payload: dict) -> None: ...
    async def subscribe(self, topic: str) -> AsyncIterator[dict]: ...

class Colony:
    def federate(self, transport: FederationTransport) -> None: ...
    async def signal_remote(self, target_colony: str, cat_id: str,
                            to_organ: Organ, method: str, **kw) -> Any: ...
```

### 内置传输

| Transport            | 说明          | 场景                 |
| -------------------- | ------------- | -------------------- |
| TCPSocketTransport   | 标准库 socket | 同网络内两台主机     |
| RedisPubSubTransport | Redis pub/sub | 生产部署（可选依赖） |

### 安全

| 规则                         | 说明                            |
| ---------------------------- | ------------------------------- |
| Colony 间默认隔离            | 不发 federation 调用则不可见    |
| signal_remote 走 wiring 校验 | 远端 Cat 自己的 wiring 仍然生效 |
| Transport 可加密             | TCP 走 TLS、Redis 走 ACL        |

### 测试

~15 个

---

## v1.0.13 — Signal Middleware（信号中间件） ⭐ 专家意见

> `signal()` 是框架最核心的原语 — 所有器官间通信的必经之路。当前无拦截点，日志/追踪/限流全部需要侵入器官代码。Middleware 是框架级的生产力基础设施。

### 设计

```python
class CatBase:
    nervous: Nervous

    def use_middleware(self, mw: SignalMiddleware) -> None:
        """注册一个 signal 中间件。按注册顺序执行。"""
        self.nervous._middleware.append(mw)
```

```python
class SignalMiddleware(Protocol):
    """信号中间件 — 每次 signal() 调用前后执行。"""

    async def before(self, ctx: SignalCall) -> SignalCall | None:
        """signal 执行前。返回 None 则短路（阻止执行）。"""
        ...

    async def after(self, ctx: SignalCall, result: Any) -> Any:
        """signal 执行后。可修改/包装返回值。"""
        ...

    async def on_error(self, ctx: SignalCall, error: Exception) -> None:
        """signal 抛出异常时调用。"""
        ...
```

### 内置中间件

| 中间件            | 说明                                                 |
| ----------------- | ---------------------------------------------------- |
| `ContextInjector` | 自动将 SignalContext 注入每次 signal（Gateway 依赖） |
| `SignalLogger`    | 记录每次 signal(from, to, method, duration)          |
| `RateLimiter`     | 限制特定 organ 方法的调用频率                        |
| `TimeoutGuard`    | 超时自动 abort                                       |

### 设计原则

- **零开销关闭** — 无中间件时 signal() 路径不增加任何判断
- **不改变 signal() 签名** — Middleware 是装饰器模式，不入侵现有接口
- **Middleware stack 在 Nervous 内** — 不污染 OrganHost 或 EventBus

### 测试

~12 个

---

## v1.0.14 — Cat Lifecycle Hooks（生命周期钩子） ⭐ 专家意见

> Organ 的 Protocol 定义了 `build_system_prompt()` / `cancel_current()` 等生命周期方法，但都在器官内部。Cat 级别缺少 "启动时做什么" "关闭时做什么" 的统一入口。

### 设计

```python
class CatBase:
    """在现有基础上新增生命周期钩子"""

    async def start(self) -> None:
        """装配完成 → 发射 lifecycle.start → 依次调用 on_start hooks"""
        await self.emit(Lifecycle.START, cat_id=self.cat_id)
        for hook in self._start_hooks:
            await hook(self)

    async def shutdown(self) -> None:
        """依次调用 on_shutdown hooks → 发射 lifecycle.shutdown"""
        for hook in reversed(self._shutdown_hooks):
            await hook(self)
        await self.emit(Lifecycle.SHUTDOWN, cat_id=self.cat_id)

    def on_start(self, hook: CatHook) -> None:
        self._start_hooks.append(hook)

    def on_shutdown(self, hook: CatHook) -> None:
        self._shutdown_hooks.append(hook)
```

### 与 Loop 的关系

| 概念            | 触发时机          | 用途                                      |
| --------------- | ----------------- | ----------------------------------------- |
| Loop.trigger    | 某个 event 发生时 | 自动化执行回路（已有）                    |
| Cat.on_start    | 猫启动时          | 初始化 Gateway、连接 DB、预热 Kitten Pool |
| Cat.on_shutdown | 猫关闭时          | 关闭 Gateway、保存状态、dismiss kittens   |

Loop 是"运行中的闭环"，Lifecycle Hook 是"出生/死亡时的一次性动作"。两者互补不冲突。

### 测试

~8 个

---

## v1.0.15 — 长流程（Long-Running Orchestration）

> 三个"长"是一个东西：猫接到任务 → 编排分身接力干活 → 跑 3 天不断 → 重启恢复状态 → 等用户授权后继续。这是框架必须保证的能力。

### 一次完整的长流程

```
用户: "帮我重构整个 auth 模块"
  │
  ▼
主猫: 拆解为 8 个步骤，创建 Workflow 实体
  │
  ├── Step 1: 分析现状              → spawn Kitten-A → 完成 ✓ → checkpoint
  ├── Step 2: 设计新接口             → spawn Kitten-B → 完成 ✓ → checkpoint
  ├── Step 3: 用户确认设计方案       → 💬 等待用户回复（暂停）
  │                                      │ 3 天后用户回复 "方案 OK"
  ├── Step 4: 迁移 User 模型        → spawn Kitten-C → 完成 ✓ → checkpoint
  ├── ...                                │ 猫进程重启
  │                                      │ cat.start() → 扫描未完成 Workflow
  ├── Step 5: 迁移 Session 逻辑     → spawn Kitten-D → 继续 ✓
  ├── ...
  └── Step 8: 全量测试              → spawn Kitten-H → 完成 ✓ → Workflow complete
```

### 核心设计：三件事合一

| 能力                          | 如何实现                                                                                              |
| ----------------------------- | ----------------------------------------------------------------------------------------------------- |
| **长会话** — 重启后记得上下文 | Workflow 实体存 Hippocampus。cat.start() 扫出未完成 workflow → 自动加载 plan + 历史 checkpoint        |
| **长续航** — 3 天不爆内存     | 每个 Step 完成后压缩上一 Step 的 episode（decay 加强）。locate 时只拉当前 workflow 相关记忆，自动截断 |
| **长流程** — 跨会话任务不丢   | 每步自动写 checkpoint 到 Hippocampus 实体。断电/重启 → 读 checkpoint 继续                             |

### 框架新增

**1. Workflow 实体模型** (`models.py`)

```python
@dataclass
class WorkflowShape:
    entity_id: str
    cat_id: str
    session_id: str
    status: str          # "active" | "awaiting_user" | "completed" | "failed"
    plan: list[str]      # 步骤描述列表
    current_step: int    # 当前在第几步
    checkpoint: dict     # 当前步骤的断点数据
    kittens_spawned: list[str]  # 已 spawn 的 kitten 列表
    created_at: str
    updated_at: str
```

**2. Framework-guaranteed checkpoint** — 以下时机框架自动存：

| 时机                     | 触发                      |
| ------------------------ | ------------------------- |
| Kitten complete → absorb | 自动存档当前步骤结果      |
| Kitten stuck → dismiss   | 自动存档错误信息          |
| Cat.shutdown()           | 自动存档所有活跃 workflow |
| 用户回复触发 resume      | 自动读档上一步 checkpoint |

**3. 新增 Path + Chain**

```python
# 编排域新路径
Path("workflow_create",    BRAINSTEM, HIPPOCAMPUS, "add_entity",    "write", "创建工作流"),
Path("workflow_checkpoint",BRAINSTEM, HIPPOCAMPUS, "append_content","write", "写检查点"),
Path("workflow_resume",    BRAINSTEM, HIPPOCAMPUS, "get_entity",    "read",  "恢复工作流"),

# 编排链
Chain("workflow_chain", ("workflow_create", "execute_tool", "workflow_checkpoint"),
      "工作流单步 — 创建→执行→存档"),
```

全部复用已有 Hippocampus 方法，零新器官。

**4. Cat 生命周期自动衔接** (`assembly.py`)

```python
class CatBase:
    async def start(self) -> None:
        # 1. 扫描 Hippocampus 中未完成的 Workflow
        # 2. 若存在 → 自动加载，触发 resume
        # 3. 发射 lifecycle.start
        ...

    async def shutdown(self) -> None:
        # 1. 遍历所有 active workflow → 写 checkpoint
        # 2. 关闭 Gateway
        # 3. 发射 lifecycle.shutdown
        ...
```

### 框架不做什么

- 不决定如何拆解步骤（LLM 做的事，应用层）
- 不实现 kitten 的具体执行逻辑（应用层）
- 不提供 workflow 的触发策略（heartbeat 已够）

框架只保证：**状态不丢，重启可续，内存不炸。**

### 改动

| 模块                 | 改动                                               |
| -------------------- | -------------------------------------------------- |
| `models.py`          | WorkflowShape 数据形状                             |
| `path.py`            | 3 条新 Path（编排域）                              |
| `chain.py`           | 1 条新 Chain                                       |
| `assembly.py`        | CatBase.start() 自动扫描 + shutdown() 自动存档     |
| `protocols_brain.py` | HippocampusProtocol 新增 `list_active_workflows()` |

**改动**：~90 行

**测试**：~20 个（workflow 创建/checkpoint/resume/重启恢复/多步骤/用户等待）

---

## 为什么不提的

| 功能                   | 原因                                                                                      |
| ---------------------- | ----------------------------------------------------------------------------------------- |
| **反省 (Reflection)**  | 需要 LLM（B-model），框架不绑 LLM                                                         |
| **飞书/微信平台逻辑**  | OAuth、卡片、解密 → 应用层 FeishuAdapter 子类                                             |
| **定时任务/Scheduler** | `heartbeat.tick` + maintenance loop 已够。定时 spawn kitten 是应用层监听 heartbeat 的行为 |
| **权限/多租户**        | 部署策略，每只猫的权限模型完全不同                                                        |
| **Web Dashboard**      | UI 层，不属于框架骨架                                                                     |
| **可观测性重做**       | Stethoscope + EventBus 已覆盖诊断。Signal Middleware (v1.0.13) 补充追踪                   |

---

## meowagent 适配节点

| meowcat 版本 | meowagent 需做的事                                                                                                                                                 |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| v1.0.10      | 删除 CLI 内嵌的 stdin/stdout 循环，改用 `CliAdapter`；MeowAgent 的 HTTP server 改为 Gateway + HttpAdapter；新增 `gateway/feishu_adapter.py`（WebhookAdapter 子类） |
| v1.0.11      | 无需改动 — Path 自动可用                                                                                                                                           |
| v1.0.12      | 可选 — 需要跨主机时启用联邦                                                                                                                                        |
| v1.0.13      | `maintenance.py` 的日志改为 `SignalLogger` 中间件                                                                                                                  |
| v1.0.14      | CLI 启动流程改为 `cat.on_start(lambda c: c.gateway.start(c))`                                                                                                      |
| v1.0.15      | 长任务改用 `WorkflowShape` + `workflow_chain`；删除应用层 checkpoint/resume 逻辑                                                                                   |

---

## 设计约束（不变）

| 规则                       | 说明                                                    |
| -------------------------- | ------------------------------------------------------- |
| 零依赖 meowagent           | 框架层绝不 import meowagent                             |
| Protocol 优先              | 新接口先定义 Protocol                                   |
| 一版一事                   | 设计→开发→审查三会话                                    |
| 函数 ≤50 行 / 文件 ≤500 行 | 保持可拆分                                              |
| 优先四层 API               | 新能力通过 Path→Chain→Loop 暴露                         |
| 测试先行                   | 每版 ≥5 个测试                                          |
| 不污染器官体系             | Gateway/Middleware/Hooks 是独立子系统，不挤占 OrganSpec |

---

## 附录：Gateway 启动示例（最终体验）

```python
from meowcat import create_cat, Gateway
from meowcat.gateway import HttpAdapter, WsAdapter, CliAdapter

cat = create_cat("my-cat", cerebrum=MyBrain())
gw = Gateway(cat)

# 挂插多个适配器 — 同一只猫同时服务多个入口
gw.mount_adapter(HttpAdapter(host="0.0.0.0", port=8000))
gw.mount_adapter(WsAdapter(host="0.0.0.0", port=8001))
gw.mount_adapter(CliAdapter())  # stdin/stdout

cat.on_start(lambda c: c.gateway.start(c))
cat.on_shutdown(lambda c: c.gateway.stop())

await cat.start()  # 启动 Gateway + 所有 Adapter
# CLI 用户: 终端直接对话
# HTTP: curl -X POST localhost:8000/chat -d '{"message":"hi"}'
# WS:   ws://localhost:8001/chat → {"message":"hi"}
# 三个入口，同一只猫，同一份记忆，不同 session_id 索引
```
