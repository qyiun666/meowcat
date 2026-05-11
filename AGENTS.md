# MeowCat AGENTS.md — 应用开发者入口

> 🎯 **你的身份**：meowcat 应用开发者。你 `pip install meowcat`，然后 `from meowcat import CatBase` 构建自己的 AI Agent。
> 先读此文件建立心智模型（3 分钟），再看 [CATALOG.md](CATALOG.md) 查默认配置，看 [README_CN.md](README_CN.md) 了解项目亮点。
>
> **v2.0 破坏性变更**：从 v1.x 升级前先读 [MIGRATION_v2.md](MIGRATION_v2.md) (中文) · [MIGRATION_v2_EN.md](MIGRATION_v2_EN.md) (English)

---

## 1. 一句话定位

meowcat 是 **纯抽象的 AI Agent 骨架**。它只定义"猫有什么器官、器官间怎么连"，不写任何具体逻辑。你来实现每个器官的具体行为——LLM 推理、记忆存储、安全检查、工具执行。独立 pip 包，核心仅依赖 pydantic + anyio。

---

## 2. 画面：猫舍 + 单人宿舍

```
┌─ 🏠 猫舍（Colony）──────────────────────────────────────┐
│                                                          │
│   ┌── 猫舍大看板（Shared Board）──────────────────┐     │
│   │                                                │     │
│   │  [用户画像]  主人信息（名字、语言、联系方式）   │     │
│   │  [共享知识]  集体记忆（语义检索）               │     │
│   │  [猫列表]    每只猫的简要介绍                   │     │
│   │  [自定义...]  应用层可挂更多区域                │     │
│   └────────────────────────────────────────────────┘     │
│                                                          │
│   ┌─ 🐱 01号宿舍 ─┐  ┌─ 🐱 02号宿舍 ─┐                 │
│   │  看板 写字台   │  │  看板 写字台   │                 │
│   │  床 [自定义]   │  │  床 [自定义]   │                 │
│   └───────────────┘  └───────────────┘                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 3. 猫舍大看板（Colony Shared Board）— 公共区域

贴在猫舍墙上的公共看板，所有猫都能看到。通过 `colony.ns_get/set("区域名", "key", value)` 读写。

| 看板区域                  | 固定放什么                                                         | 代码                         |
| ------------------------- | ------------------------------------------------------------------ | ---------------------------- |
| **用户画像** `owner/`     | 主人信息：name, email, language, extra（slack_id、role 等随便加）  | `ColonyOwner` dataclass      |
| **共享知识** `knowledge/` | 大家都该知道的事，支持语义检索                                     | `SharedMemoryPool`           |
| **猫列表** `cats/`        | 每只猫的 `{uid, name, brief, capabilities}` — 住在这里的猫的花名册 | namespace 已注册，应用层填充 |
| **[自定义]**              | 应用层通过 `colony.ns_set("custom_ns", key, value)` 挂新区域       | —                            |

> v2.0 精简：namespace 从 6 个减到 3 个（owner/knowledge/cats），`rules/` 和 `growth/` 已移除。

### 3.1 Colony 配套模块

| 模块               | 做什么                               |
| ------------------ | ------------------------------------ |
| `memory.py`        | 共享记忆池（remember/recall/forget） |
| `communication.py` | 猫间信号（signal_between/broadcast） |
| `cat_ops.py`       | 创建/释放/查找猫                     |
| `namespace.py`     | 键值存储                             |
| `config.py`        | Colony 配置                          |

---

## 3.5 猫舍大门（Gateway + FrontDesk）— 唯一外部入口

猫舍通过大门（Gateway）与外部世界交互。**框架层只保留 Gateway 类 + FrontDesk 插件链模式 + 适配器抽象，具体适配器（HTTP/WS/CLI）由应用层实现。**

```
外部世界 (HTTP/WS/CLI/IPC/Webhook)
    │
    ▼
┌─ Gateway (大门) ────────────────┐
│  ┌─ FrontDesk (前台) ────────┐  │
│  │  on_route 插件链:           │  │
│  │  → 安全门 (security gate)  │  │
│  │  → 审计日志 (audit)        │  │
│  │  → 限流 (rate limit)       │  │
│  │  → 自定义路由 (custom)     │  │
│  └──────────┬────────────────┘  │
│             │                    │
│   mount_adapter(MyAdapter())    │  ← 应用层提供适配器实现
└─────────────┼───────────────────┘
              │
              ▼
     Colony.cat.perceive()
```

### 核心设计

- **Gateway 不是器官**：不挂在 OrganHost 上，是 Colony 的独立子系统（皮肤）
- **FrontDesk 是前台接待员**：Protocol + Pluggable，所有外部消息必经 `route()` 方法
- **插件链 first-hit**：`on_route` 插件按注册顺序执行，第一个返回非 None 的插件短路返回
- **适配器由应用层提供**：`HttpAdapter`/`WsAdapter`/`CliAdapter` 等已从框架移出，应用层自行实现适配器并 `mount_adapter()`

### 用法

```python
from meowcat import Colony, Gateway
from meowcat.gateway.front_desk import DefaultFrontDesk
# 适配器由应用层提供（框架不再内置 HttpAdapter/WsAdapter 等）
# from my_app.adapters import HttpAdapter

colony = Colony("my-colony")

fd = DefaultFrontDesk()
fd.plug("on_route", lambda text, ctx, colony:
    "⚠️ 危险操作已拦截" if "DROP TABLE" in text.upper() else None)
fd.plug("on_route", lambda text, ctx, colony: print(f"[audit] {ctx.user_id}: {text[:50]}"))

gw = Gateway(colony, front_desk=fd)
# gw.mount_adapter(HttpAdapter(port=8000))  # 应用层提供适配器
await gw.start()
```

### 自定义 FrontDesk

```python
class MyFrontDesk(DefaultFrontDesk):
    async def route(self, text, ctx, colony):
        if ctx.platform == "feishu":
            return await self._feishu_dispatch(text, ctx, colony)
        return await super().route(text, ctx, colony)

gw = Gateway(colony, front_desk=MyFrontDesk())
```

---

## 4. 单人宿舍（Cat Private Room）— 私有区域

每只猫有自己的小房间，里面固定有这些家具：

### 4.1 看板（CatSelf）— 贴在墙上的身份板

猫每次行动前都看这块板，了解自己是谁。行动后可能更新板上的内容。

```
┌── 看板（CatSelf）──────────────┐
│                                │
│  [性格卡片]  怎么说话            │
│   Personality: {tone, language} │
│                                │
│  [三观卡片]  相信什么            │
│   Cortex L2: beliefs[]         │
│   "参数化SQL 永远用参数"        │
│                                │
│  [自知卡片]  会什么 / 不会什么    │
│   擅长: ["SQL查询", "Python"]   │
│   不会: ["前端开发"]            │
│                                │
└────────────────────────────────┘
```

> v2.0 变更: **CatSelf 由应用层自行创建和管理**。`create_cat()` 不再自动创建 CatSelf。
>
> ```python
> from meowcat.biology.cat_self import CatSelf
> cat.cat_self = CatSelf()
> ```

- 行动前：`CatSelf.before_act(reason)` 冻结快照，注入器官上下文
- 行动后：松果体 `fuse_to_self` 更新三观卡片和自知卡片

### 4.2 写字台（ScribblePad）— 临时草稿纸

每次行动后的碎碎念写在这里。**临时缓冲区**，满了就清空。

```
┌── 写字台（ScribblePad）────────┐
│                                │
│  📝 "用户问了表结构"            │
│  📝 "回复了建表语句"            │
│  ...（最多 200 条）             │
│                                │
│  📒 日志本（episodes）          │
│  永久记录，每次对话追加一条      │
│  "5/10 14:30 | 问:xxx | 答:xxx" │
│                                │
└────────────────────────────────┘
```

- 写：`CatSelf.after_act(summary, impact)` → scribble 碎片
- 日志本：`Hippocampus.remember()` 写入永久记录
- 清空：`PinealGland.trigger()` → drain() 排空草稿纸去蒸馏

### 4.3 床（Hippocampus）— 记忆 + 知识树

```
┌── 海马体 ──────────────────────┐
│                                │
│  [实体图谱]  结构化知识         │
│  users ──id_type──▶ uuid       │
│  module_A ──depends_on──▶ B    │
│                                │
│  [知识树]  v2.0 新增            │
│  TreeNode 层级结构             │
│  build_tree / search_tree      │
│                                │
└────────────────────────────────┘
```

- 实体图谱：结构化知识，不随草稿纸清空而消失
- **知识树 (v2.0)**：`cat.hippocampus.build_tree(entity_id, root)` / `.get_tree()` / `.search_tree()` / `.query_subtree()` / `.delete_tree()` / `.check_stale()`

### 4.4 松果体（PinealGland）— 蒸馏器

从写字台取草稿 → 蒸馏成洞察 → 更新看板（内环）+ 投到猫舍看板（外环）。

```
写字台 drain() → 松果体 meditate() → Insight[]
                                      ├── fuse_to_self   → 看板
                                      └── fuse_to_colony → 猫舍大看板
```

### 4.5 待办清单（TaskPad）— 房间家具 #5 🆕 v2.2.0

每只猫床头挂的任务清单。大脑决定做什么，爪子干活，做完划掉。

```
┌── 待办清单（TaskPad）──────────┐
│                                │
│  ☐ 写一个登录函数              │
│  ☐ 重构数据库模型              │
│  ✓ 修复空指针异常               │
│  ✗ 优化查询性能（超时）         │
│                                │
└────────────────────────────────┘
```

- **post()**: 贴新任务（TODO → DOING → DONE/FAILED）
- **pick()**: 取下一个待办（FIFO，跳过已完成的）
- **diagnose()**: 看任务分布
- **独立实例**: 每只猫有自己的 TaskPad，分身猫互不干扰

### 4.6 身体（器官）— 干活用的

猫由 20 个器官组成，一套 Default 实现开箱即用：

| 类别 | 器官                   | 做什么                             |
| ---- | ---------------------- | ---------------------------------- |
| 输入 | Ears（耳朵）           | 听声音 / 看文字                    |
| 输入 | Eyes（眼睛）           | 看图像                             |
| 输入 | Whiskers（胡须）       | 感知环境上下文                     |
| 脑区 | Thalamus（丘脑）       | 感觉中继 + 路由决策                |
| 脑区 | Hippocampus（海马体）  | 记忆存储 + 实体图谱 + 知识树       |
| 脑区 | Cortex（皮层）         | 世界观蒸馏 L0→L3                   |
| 脑区 | Cerebrum（大脑）       | 深度思考 / LLM 推理                |
| 脑区 | Cerebellum（小脑）     | 快速响应 / 模式匹配                |
| 脑区 | Amygdala（杏仁核）     | 安全检查 / 风险评估                |
| 脑区 | BrainStem（脑干）      | 提示词构建 + 生命周期 + 上下文压缩 |
| 脑区 | Frontal（额叶）        | 专注 / 任务拆解                    |
| 脑区 | Hypothalamus（下丘脑） | 记忆衰减 / 自维护                  |
| 输出 | Mouth（嘴巴）          | 说话                               |
| 输出 | Purr（呼噜）           | 流式输出                           |
| 输出 | Tail（尾巴）           | 状态显示                           |
| 工具 | Paws（爪子）           | **唯一**工具执行入口               |
| 生长 | AnomalyGrowth          | 异常模式学习                       |
| 生长 | CorrectionGrowth       | 纠正固化                           |
| 生长 | Crystallizer           | 技能结晶                           |
| 生长 | RoleEmergence          | 角色涌现                           |

> **禁区**：大脑 → 爪子（`cerebrum → paws`）禁止直连。工具执行必须走 大脑 → 小脑 → 爪子。

> v2.0 变更: Noop/Renovated 两套器官合并为一套 Default。`create_cat(renovated=True/False)` 参数已删除。

### 4.7 插头（Adapter）— 器官可以换实现

每个器官是插座，可以插入外部实现：

```python
from meowcat.adapters import HippocampusAgent
cat.mount("brain", "hippocampus", HippocampusAgent(别人的记忆系统))
```

`AgentOrgan` 提供委托 + 错误包装。2 种实现风格：`MODEL`（LLM 驱动）和 `ALGORITHM`（确定性算法）。（v2.0 移除了 `RULE` 和 `HYBRID`。）

---

## 5. 两层架构 — 一张图看懂猫怎么工作

v2.4.0 起，应用开发者只需要理解两层抽象：**打工循环**（对外干活）+ **成长循环**（自我进化）。

### 5.1 打工循环：`perceive()` + `do_task()`

所有外部输入的统一入口，内置 hear → route → reason → speak：

```
perceive("你好") → Ears → Thalamus → Cerebrum → Cerebellum → Mouth → 回复

do_task("写代码", max_rounds=5) → 大脑 ↔ 爪子多轮循环（最多 5 轮）
```

- `cat.perceive(message)` — 接收用户输入，返回猫的回复
- `cat.do_task(task, max_rounds=N)` — 大脑 ↔ 工具多轮循环，完成任务
- `cat.run_loop("conversation")` / `cat.run_loop("tool_execution")` 是内部实现细节，**不要直接调用**

### 5.2 成长循环：`ReflectionLoop`

猫做完事后怎么进步。三种模式，应用层决定什么时候激活：

```python
from meowcat.biology.cat_self_loops import ReflectionLoop

ReflectionLoop(mode="conversation", fusion_trigger="event")   # 对话后反思
ReflectionLoop(mode="task", fusion_trigger="full:50")          # 草稿纸满 50 条触发
ReflectionLoop(mode="learn", fusion_trigger="immediate")       # 立即蒸馏
```

```
写字台(草稿) → 松果体(蒸馏) → Insight[]
                              ├── fuse_to_self   → 看板（更新自己）
                              └── fuse_to_colony → 猫舍大看板（分享出去）
```

### 5.3 旁路 Loop（需要时手动触发）

| Loop              | 触发器官      | 做什么          |
| ----------------- | ------------- | --------------- |
| `danger_response` | Amygdala      | 安全快速响应    |
| `maintenance`     | Hypothalamus  | 记忆衰减 + 清理 |
| `diagnostic`      | Crystallizer  | 技能结晶诊断    |
| `growth`          | AnomalyGrowth | 异常学习        |
| `reflection`      | Crystallizer  | 执行后反思      |

### 5.4 内部基础设施：Path / Chain

23 条 Path、8 条 Chain 是框架内部信号系统，应用开发者无需关心。
高级用法（直接操作 Path/Chain/Loop 注册器）见 **[CATALOG.md](CATALOG.md) §高级参考**。

---

## 6. 房间内闭环（CatSelf + ReflectionLoop）

这是猫在房间里自我进化的回路。v2.0 中 3 个独立的 Loop 类合并为统一的 `ReflectionLoop`：

```python
from meowcat.biology.cat_self_loops import ReflectionLoop

# 对话后反思
loop = ReflectionLoop(mode="conversation", fusion_trigger="event")
# 任务驱动进化（草稿纸满 50 条触发）
loop = ReflectionLoop(mode="task", fusion_trigger="full:50")
# 好奇心驱动学习（立即蒸馏）
loop = ReflectionLoop(mode="learn", fusion_trigger="immediate")
```

```
看板(before_act)                    松果体(trigger_if)
  │ 读性格/三观/自知                     ↑
  ▼                                    │
身体执行                                │ 排空草稿纸
  │ 对话/任务/学习                       │ meditate() 蒸馏
  ▼                                    │
写字台(after_act) ─────────────────────┘
  │ 写碎片                    fuse_to_self → 更新看板
  │                    fuse_to_colony → 投猫舍大看板
```

**关键**：`after_act()` 只写草稿纸，不自动触发松果体。什么时候蒸馏由应用层决定。

---

## 7. 两个环：内环 + 外环

```
内环（单猫自我进化）：
  写字台 → 松果体.meditate() → fuse_to_self → 看板

外环（集体智慧共享）：
  写字台 → 松果体.meditate() → fuse_to_colony → 猫舍大看板
                                                   → 其他猫读到
```

---

## 8. 关键概念

- **Slot-Plug 模式**：框架定义器官接口（Protocol），你提供具体实现。2 种风格：`ALGORITHM` | `MODEL`
- **Cat 是唯一装配点**：所有器官挂载在 CatBase 上，通过 `cat.mount()` 注册，通过 `cat.signal()` 通信
- **Paws 是工具唯一入口**：`cerebrum → cerebellum → paws` 是唯一合法工具执行路径
- **两层 API**：`perceive()` / `do_task()`（打工循环）+ `ReflectionLoop`（成长循环）。高级用法见 [CATALOG.md](CATALOG.md)
- **CatSelf 应用层管理**：v2.0 起 CatSelf 不自动创建，由应用层自行 `cat.cat_self = CatSelf()`
- **内环 + 外环**：内环更新自己的看板，外环投到 Colony 共享知识池
- **知识树**：`TreeNode` dataclass + Hippocampus 扩展（v2.0）

> 更多约束细节见 [CATALOG.md](CATALOG.md) 禁止边和写权限约束。

---

## 9. 常用 API 速查

```python
from meowcat import Colony
from meowcat.defaults import create_cat, KW_BILINGUAL, PROMPT_ZH

# 创建猫舍和一只猫 — 只需提供 cerebrum（LLM 实现）
colony = Colony("my-colony")
cat = create_cat(container=colony, name="Kitty", cerebrum=MyLLM(), keyword=KW_BILINGUAL, prompt=PROMPT_ZH)

# v2.0: CatSelf 由应用层自行创建
from meowcat.biology.cat_self import CatSelf
cat.cat_self = CatSelf()

# 打工循环 — 统一感知入口 (async generator)
async for ev in cat.perceive("你好！"):
    print(ev)

# 打工循环 — 大脑 ↔ 爪子多轮
from meowcat.tools.tool_call import XmlToolCallParser
result = await cat.do_task("写一个登录函数", max_rounds=5)
print(result.final_text, result.rounds, result.tool_calls)

# 挂载自定义器官
cat.mount("brain", "hippocampus", MyHippocampus())

# Colony 多猫容器
cat_a = create_cat(container=colony, name="analyst", cerebrum=AnalystBrain())
cat_b = create_cat(container=colony, name="executor", cerebrum=ExecutorBrain())
await colony.signal_between(cat_a.cat_uid, cat_b.cat_uid, "brain", "amygdala",
                              "assess_safety", input=data)

# Gateway 大门 + FrontDesk 前台（适配器由应用层提供）
from meowcat import Gateway
from meowcat.gateway.front_desk import DefaultFrontDesk

fd = DefaultFrontDesk()
fd.plug("on_route", lambda text, ctx, colony: print(f"[audit] {text[:50]}"))
gw = Gateway(colony, front_desk=fd)
# gw.mount_adapter(HttpAdapter(port=8000))  # 应用层实现
await gw.start()

# v2.0 知识树
from meowcat.tree import TreeNode

root = TreeNode(id="r", entity_id="e1", parent_id=None,
                path="/", node_type="project", name="my-project")
cat.hippocampus.build_tree("e1", root)
tree = cat.hippocampus.get_tree("e1")
nodes = cat.hippocampus.search_tree("e1", "keyword")

# 成长循环 — ReflectionLoop
from meowcat.biology.cat_self_loops import ReflectionLoop
loop = ReflectionLoop(mode="conversation", fusion_trigger="event")

# v2.1.0 规则引擎
from meowcat.ruleset import Rule, RuleSet
cat.rule_set = RuleSet(
    always_on=[Rule("安全守则", "不要删除数据库", "critical")],
    per_route={"deep_reason": [Rule("SQL规范", "参数化查询", "high")]},
)

# v2.2.0 召唤分身猫
worker = cat.spawn_worker("helper", "检索用户表结构")
worker.task_pad.list_todo()  # 分身有自己的待办清单
```

> 完整装配流程和所有默认配置 → **[CATALOG.md](CATALOG.md)**

---

## 10. 安装 & 测试

```bash
pip install meowcat          # 核心框架（零 I/O）
pip install -e ".[dev]"      # 开发模式
pytest tests/ -v              # 运行测试
```

Python 3.10+，核心依赖：`pydantic>=2.0` + `anyio>=4.0`。

> v2.0 变更: `pip install meowcat[plus]` 不再包含内置工具和网关适配器（已移入应用层）。框架 plus/ 保留 chroma_store、crystallizer、skill_loader。
