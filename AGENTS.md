# MeowCat AGENTS.md — 应用开发者入口

> 🎯 **你的身份**：meowcat 应用开发者。你 `pip install meowcat`，然后 `from meowcat import CatBase` 构建自己的 AI Agent。
> 先读此文件建立心智模型（3 分钟），再看 [CATALOG.md](CATALOG.md) 查默认配置，看 [README_CN.md](README_CN.md) 了解项目亮点。

---

## 1. 一句话定位

meowcat 是 **纯抽象的 AI Agent 骨架**。它只定义"猫有什么器官、器官间怎么连"，不写任何具体逻辑。你来实现每个器官的具体行为——LLM 推理、记忆存储、安全检查、工具执行。独立 pip 包，零外部依赖。

---

## 2. 画面：猫舍 + 单人宿舍

```
┌─ 🏠 猫舍（Colony）──────────────────────────────────────────┐
│                                                              │
│   ┌── 猫舍大看板（Shared Board）──────────────────────┐     │
│   │                                                    │     │
│   │  [用户画像]  主人信息（名字、语言、联系方式）       │     │
│   │  [规则]      所有猫必须遵守的法律                   │     │
│   │  [共享知识]  大家共同知道的事情（语义检索）         │     │
│   │  [猫列表]    每只猫的简要介绍                       │     │
│   │  [集体生长]  跨猫发现的异常和纠正                   │     │
│   │  [自定义...]  应用层可挂更多区域                    │     │
│   └────────────────────────────────────────────────────┘     │
│                                                              │
│   ┌─ 🐱 01号宿舍 ─┐  ┌─ 🐱 02号宿舍 ─┐  ┌─ 🐱 03号宿舍 ─┐  │
│   │  看板 写字台   │  │  看板 写字台   │  │  看板 写字台   │  │
│   │  床  [自定义]  │  │  床  [自定义]  │  │  床  [自定义]  │  │
│   └───────────────┘  └───────────────┘  └───────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. 猫舍大看板（Colony Shared Board）— 公共区域

贴在猫舍墙上的公共看板，所有猫都能看到。通过 `colony.ns_get/set("区域名", "key", value)` 读写。

| 看板区域                  | 固定放什么                                                         | 代码                                        |
| ------------------------- | ------------------------------------------------------------------ | ------------------------------------------- |
| **用户画像** `owner/`     | 主人信息：name, email, language, extra（slack_id、role 等随便加）  | `ColonyOwner` dataclass                     |
| **规则** `rules/`         | 所有猫必须遵守的法律：安全策略、审批要求、速率限制                 | `ColonyRules` (可挂 `on_check` hook)        |
| **共享知识** `knowledge/` | 大家都该知道的事，支持语义检索                                     | `SharedMemoryPool` (remember/recall/forget) |
| **猫列表** `cats/`        | 每只猫的 `{uid, name, brief, capabilities}` — 住在这里的猫的花名册 | namespace 已注册，应用层 populate           |
| **集体生长** `growth/`    | 跨猫发现的异常、纠正记录                                           | `CollectiveGrowth`                          |
| **[自定义]**              | 应用层通过 `colony.storage_plug("namespace", "xxx")` 挂新区域      | —                                           |

---

## 3.5 猫舍大门（Gateway + FrontDesk）— 唯一外部入口

猫舍（Colony）通过大门（Gateway）与外部世界交互。**1 猫舍 : 1 大门 : N 适配器。**

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
└─────────────┼───────────────────┘
              │
              ▼
     Colony.cat.perceive()
```

### 核心设计

- **Gateway 不是器官**：不挂在 OrganHost 上，是 Colony 的独立子系统（皮肤）
- **FrontDesk 是前台接待员**：Protocol + Pluggable，所有外部消息必经 `route()` 方法
- **插件链 first-hit**：`on_route` 插件按注册顺序执行，第一个返回非 None 的插件短路线
- **默认路由**：`ctx.target_cat` 指定 → 转发给那只猫 → `cat.perceive()`；未指定 → 返回占位回复

### 用法

```python
from meowcat import Colony, Gateway
from meowcat.gateway.front_desk import DefaultFrontDesk
from meowcat.plus.gateway import HttpAdapter

colony = Colony("my-colony")

# 默认前台
fd = DefaultFrontDesk()

# 挂安全门插件（first-hit — 拦截危险内容）
fd.plug("on_route", lambda text, ctx, colony:
    "⚠️ 危险操作已拦截" if "DROP TABLE" in text.upper() else None)

# 挂审计日志插件
fd.plug("on_route", lambda text, ctx, colony: print(f"[audit] {ctx.user_id}: {text[:50]}"))

# 创建大门，挂适配器
gw = Gateway(colony, front_desk=fd)
gw.mount_adapter(HttpAdapter(port=8000))
await gw.start()  # 阻塞，所有适配器并行运行
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
│   "用户表 id 类型是 uuid"       │
│                                │
│  [自知卡片]  会什么 / 不会什么    │
│   Metacognition L3:            │
│   擅长: ["SQL查询", "Python"]   │
│   不会: ["前端开发"]            │
│                                │
└────────────────────────────────┘
```

- 行动前：`CatSelf.before_act(reason)` 冻结快照，注入器官上下文
- 行动后：松果体 `fuse_to_self` 更新三观卡片和自知卡片

### 4.2 写字台（ScribblePad）— 临时草稿纸

每次行动后的碎碎念写在这里。**临时缓冲区**，满了就清空。

```
┌── 写字台（ScribblePad）────────┐
│                                │
│  📝 "用户问了表结构"            │
│  📝 "回复了建表语句"            │
│  📝 "用户喜欢 Python 3.12"     │
│  ...（最多 200 条）             │
│                                │
│  📒 日志本（episodes）          │
│  永久记录，每次对话追加一条      │
│  "5/6 14:30 | 问:xxx | 答:xxx" │
│                                │
└────────────────────────────────┘
```

- 写：`CatSelf.after_act(summary, impact)` → scribble 碎片
- 日志本：`Hippocampus.remember()` 写入永久记录
- 清空：`PinealGland.trigger()` → drain() 排空草稿纸去蒸馏

### 4.3 床（Hippocampus entities）— 可选，墙上还有一张实体网

```
┌── 实体网（Hippocampus entities）──┐
│                                    │
│  users ──id_type──▶ uuid           │
│  module_A ──depends_on──▶ module_B │
│  ...（结构化知识图谱）              │
│                                    │
└────────────────────────────────────┘
```

- 猫的长期知识，不随草稿纸清空而消失
- 通过 `Hippocampus.fts_search()` 检索

### 4.4 松果体（PinealGland）— 蒸馏器

从写字台取草稿 → 蒸馏成洞察 → 更新看板（内环）+ 投到猫舍看板（外环）。

```
写字台 drain() → 松果体 meditate() → Insight[]
                                      ├── fuse_to_self   → 看板（三观卡片 + 自知卡片）
                                      └── fuse_to_colony → 猫舍大看板（共享知识）
```

### 4.5 身体（器官）— 干活用的

猫的身体由器官组成，通过 Path/Chain/Loop 编排：

| 类别 | 器官                   | 做什么                                    |
| ---- | ---------------------- | ----------------------------------------- |
| 输入 | Ears（耳朵）           | 听声音 / 看文字                           |
| 输入 | Eyes（眼睛）           | 看图像                                    |
| 输入 | Whiskers（胡须）       | 感知环境上下文 + 注入/否定/纠正检测       |
| 脑区 | Thalamus（丘脑）       | 路由决策 — 消息来了分发给谁               |
| 脑区 | Hippocampus（海马体）  | 记忆存储 + 实体图谱                       |
| 脑区 | Cortex（皮层）         | 世界观蒸馏 L0→L3                          |
| 脑区 | Cerebrum（大脑）       | 深度思考 / LLM 推理                       |
| 脑区 | Cerebellum（小脑）     | 快速响应 / 模式匹配                       |
| 脑区 | Amygdala（杏仁核）     | 安全检查 / 拒绝 / 风险评估 / is_dangerous |
| 脑区 | BrainStem（脑干）      | 提示词构建 + 生命周期管理 + 上下文压缩    |
| 脑区 | Frontal（额叶）        | 专注 / 任务拆解                           |
| 脑区 | Hypothalamus（下丘脑） | 记忆衰减 / 压缩 / 自维护                  |
| 输出 | Mouth（嘴巴）          | 说话                                      |
| 输出 | Purr（呼噜）           | 流式输出                                  |
| 输出 | Tail（尾巴）           | 状态显示                                  |
| 工具 | Paws（爪子）           | **唯一**工具执行入口                      |
| 生长 | AnomalyGrowth          | 异常模式学习                              |
| 生长 | CorrectionGrowth       | 纠正固化                                  |
| 生长 | Crystallizer           | 技能结晶                                  |
| 生长 | RoleEmergence          | 角色涌现                                  |

> **禁区**：大脑 → 爪子（`cerebrum → paws`）禁止直连。工具执行必须走 大脑 → 小脑 → 爪子。

### 4.6 插头（Adapter）— 器官可以换实现

每个器官是插座，可以插入外部实现（别人写的 skill、小系统、任何对象）：

```python
from meowcat.adapters import HippocampusAgent
cat.mount("brain", "hippocampus", HippocampusAgent(别人的记忆系统))
```

16 个器官都有对应 Adapter，`AgentOrgan` / `SkillOrgan` 提供委托 + 错误包装。

### 4.7 [自定义]

宿舍里可以加新家具：挂新器官 `cat.mount("brain", "xxx", MyOrgan())`，给看板加新卡片 `cat.cat_self.plug("before_act", my_hook)`，写字台挂新插件 `pad.plug("on_scribble", my_logger)`。

---

## 5. 内置通路（Paths）— 单步：从哪 → 到哪.方法 → 做什么

一条 Path = 一次 `signal(from器官, to器官, "方法")`。代码 `path.py` `BUILTIN_PATHS` 共 31 条。

### 5.1 记忆域（Memory）— 13 条

| Path                | 从        | 到                              | 做什么               |
| ------------------- | --------- | ------------------------------- | -------------------- |
| `locate`            | Thalamus  | Thalamus.locate()               | 记忆检索（丘脑自环） |
| `remember`          | Brainstem | Hippocampus.remember()          | 存储记忆             |
| `get_entity`        | Thalamus  | Hippocampus.get_entity()        | 读取单个实体         |
| `get_all`           | Thalamus  | Hippocampus.get_all()           | 读取全部实体         |
| `fts_search`        | Thalamus  | Hippocampus.fts_search()        | 全文搜索实体         |
| `add_entity`        | Brainstem | Hippocampus.add_entity()        | 添加实体             |
| `add_episode`       | Brainstem | Hippocampus.add_episode()       | 添加情节             |
| `connect`           | Brainstem | Hippocampus.connect()           | 连接两个实体         |
| `record_access`     | Brainstem | Hippocampus.record_access()     | 记录实体访问         |
| `set_dormant`       | Brainstem | Hippocampus.set_dormant()       | 将实体设为休眠       |
| `append_content`    | Brainstem | Hippocampus.append_content()    | 追加实体内容         |
| `update_importance` | Brainstem | Hippocampus.update_importance() | 更新实体重要性       |
| `set_last_seen`     | Brainstem | Hippocampus.set_last_seen()     | 更新最后可见时间     |

### 5.2 推理域（Reasoning）— 3 条

| Path            | 从       | 到                       | 做什么                 |
| --------------- | -------- | ------------------------ | ---------------------- |
| `deep_reason`   | Thalamus | Cerebrum.generate()      | 深度推理               |
| `decide_route`  | Thalamus | Thalamus.decide_route()  | 路由决策（自环）       |
| `assess_safety` | Amygdala | Amygdala.assess_safety() | 安全评估（杏仁核自环） |

### 5.3 输出域（Output）— 2 条

| Path    | 从         | 到              | 做什么            |
| ------- | ---------- | --------------- | ----------------- |
| `hear`  | Ears       | Thalamus.hear() | 耳朵接收输入→丘脑 |
| `speak` | Cerebellum | Mouth.speak()   | 小脑→嘴巴输出回复 |

### 5.4 工具域（Tool）— 1 条

| Path           | 从         | 到             | 做什么            |
| -------------- | ---------- | -------------- | ----------------- |
| `execute_tool` | Cerebellum | Paws.execute() | 小脑→爪子执行工具 |

### 5.5 维护域（Maintenance）— 3 条

| Path                 | 从           | 到                                       | 做什么       |
| -------------------- | ------------ | ---------------------------------------- | ------------ |
| `decay`              | Hypothalamus | Hippocampus.decay()                      | 记忆衰减     |
| `weaken_connections` | Hypothalamus | Hippocampus.weaken_connections()         | 弱化连接     |
| `cleanup_orphans`    | Hypothalamus | Hippocampus.cleanup_orphan_connections() | 清理孤立连接 |

### 5.6 合成域（Synthesis）— 2 条

| Path               | 从        | 到                           | 做什么             |
| ------------------ | --------- | ---------------------------- | ------------------ |
| `synthesize`       | Brainstem | Cortex.synthesize()          | 世界观蒸馏合成     |
| `compress_context` | Brainstem | Brainstem.compress_context() | 上下文压缩（自环） |

### 5.7 生长域（Growth）— 4 条

| Path                | 从        | 到                         | 做什么       |
| ------------------- | --------- | -------------------------- | ------------ |
| `record_anomaly`    | Brainstem | AnomalyGrowth.record()     | 记录异常模式 |
| `record_correction` | Brainstem | CorrectionGrowth.record()  | 记录纠正固化 |
| `crystallize`       | Brainstem | Crystallizer.crystallize() | 技能结晶     |
| `record_pattern`    | Brainstem | RoleEmergence.record()     | 记录角色模式 |

### 5.8 工作流域（Orchestration）— 3 条

| Path                  | 从        | 到                           | 做什么         |
| --------------------- | --------- | ---------------------------- | -------------- |
| `workflow_create`     | Brainstem | Hippocampus.add_entity()     | 创建工作流实体 |
| `workflow_checkpoint` | Brainstem | Hippocampus.append_content() | 写入检查点     |
| `workflow_resume`     | Brainstem | Hippocampus.get_entity()     | 恢复工作流     |

用法：`cat.signal(EARS, THALAMUS, "hear", raw_input="你好")` 或声明式 `Path("hear", EARS, THALAMUS, "hear")`。

---

## 6. 内置链路（Chains）— 多步序列

一条 Chain = 一组命名 Path 按序执行。框架 `chain.py` 有 8 条 BUILTIN_CHAINS，另有 3 条在 `loops.py` 的 Loop 对象中内联定义。以下列出实际运行中存在的 8 条链（合并两处）：

| Chain                | 由哪些 Path 组成                                              | 定义位置      | 做什么            |
| -------------------- | ------------------------------------------------------------- | ------------- | ----------------- |
| `memory_search`      | locate                                                        | chain.py      | 单步记忆搜索      |
| `conversation_chain` | hear → decide_route → locate → deep_reason → speak → remember | loops.py 内联 | 完整对话流        |
| `tool_loop_chain`    | hear → decide_route → execute_tool → speak → remember         | loops.py 内联 | 工具执行流        |
| `danger_chain`       | assess_safety                                                 | loops.py 内联 | 安全评估          |
| `maintenance`        | decay → cleanup_orphans                                       | chain.py      | 记忆衰减+清理孤立 |
| `diagnostic`         | crystallize                                                   | chain.py      | 技能结晶 + 诊断   |
| `growth_chain`       | record_anomaly → crystallize                                  | chain.py      | 异常学习→结晶     |
| `reflection_chain`   | record_correction → record_pattern                            | chain.py      | 纠错固化→角色涌现 |

> `chain.py` 的 BUILTIN_CHAINS 还有 `full_reasoning`（deep_reason→speak）、`tool_exec`（execute_tool）、`workflow_chain`（workflow_create→execute_tool→workflow_checkpoint），它们是可复用的原子链，但不在 Loop 中使用。

用法：`await cat.chain_registry.run("conversation_chain", message="你好")`。

---

## 7. 内置闭环（Loops）— Chain + 触发条件 + 退出条件

一条 Loop = 指定一条 Chain，加上什么时候触发、什么时候算完成。框架内置 7 条。

| Loop              | 触发条件            | 走哪条 Chain       | 退出条件     | 做什么            |
| ----------------- | ------------------- | ------------------ | ------------ | ----------------- |
| `conversation`    | `perceive.start`    | conversation_chain | 回复完成     | 一次完整对话      |
| `tool_execution`  | `orchestrate.start` | tool_loop_chain    | 工具结果返回 | 一次工具执行      |
| `danger_response` | `amygdala.alert`    | danger_chain       | 安全确认     | 危险快速响应      |
| `maintenance`     | `heartbeat.tick`    | maintenance        | 维护完成     | 定期记忆清理      |
| `diagnostic`      | 手动触发            | diagnostic         | 诊断完成     | 结晶热点 + 诊断   |
| `growth`          | `post_action`       | growth_chain       | 生长完成     | 异常学习→技能结晶 |
| `reflection`      | `tool_executed`     | reflection_chain   | 反思完成     | 纠错固化→角色涌现 |

用法：`await cat.run_loop("conversation", message="你好")` — 一行代码走完整条器官链路。

---

## 8. 房间内闭环（CatSelf Loops）— 看板 → 行动 → 写字台 → 松果体 → 更新看板

这是猫在房间里自我进化的回路。身体在外面干活（§7 的 Loop），但每次行动后房间内还有一个内省过程：

```
看板(before_act)               松果体(trigger_if)
  │ 读性格/三观/自知                ↑
  ▼                               │
身体执行                           │ 排空草稿纸
  │ 对话/任务/学习                  │ meditate() 蒸馏
  ▼                               │
写字台(after_act) ────────────────→┘
  │ 写碎片                    fuse_to_self → 更新看板（三观/自知）
  │                    fuse_to_colony → 投猫舍大看板（共享知识）
```

三种内置房间闭环：

| 闭环           | 做什么                                                   | 融合触发                        |
| -------------- | -------------------------------------------------------- | ------------------------------- |
| `conversation` | 对话后反思：看板 → 对话 → 写字台 → 松果体 → 更新看板     | `on_event("conversation_end")`  |
| `task`         | 任务后反思：看板 → 执行任务 → 写字台 → 松果体 → 更新看板 | `on_full(50)`（草稿纸满 50 条） |
| `learn`        | 学习后反思：看板 → 学新东西 → 写字台 → 松果体 → 更新看板 | 立即 `trigger()`                |

**关键**：`after_act()` 只写草稿纸，不自动触发松果体。什么时候蒸馏由应用层决定（满了再蒸？每轮都蒸？定时蒸？）。

用法：`loop = cat.cat_self.loop("conversation"); await loop.run(cat, "你好")`。

---

## 9. 两个环：内环（自己的房间） + 外环（投到猫舍）

```
内环（单猫自我进化）：
  写字台 → 松果体.meditate() → fuse_to_self → 看板（三观卡片 + 自知卡片）

外环（集体智慧共享）：
  写字台 → 松果体.meditate() → fuse_to_colony → 猫舍大看板/共享知识
                                                   → 其他猫读到 → 更新各自的看板
```

枢纽是松果体：一次蒸馏，同时走内环和外环。

---

## 10. 关键概念（理解就能用好）

- **Slot-Plug 模式**：框架定义器官接口（Protocol），你提供具体实现。4 种实现风格：`ALGORITHM` | `RULE` | `MODEL` | `HYBRID`
- **Cat 是唯一装配点**：所有器官挂载在 CatBase 上，通过 `cat.mount()` 注册，通过 `cat.signal()` 通信
- **Paws 是工具唯一入口**：`cerebrum → cerebellum → paws` 是唯一合法工具执行路径，大脑禁止直连爪子
- **优先四层 API**：Path（原子信号）→ Chain（序列+回滚）→ Loop（闭环+事件）→ LoopSequence（编排）。从简单到复杂层层组合
- **CatSelf 自我进化**：猫每次行动后 `after_act()` 写草稿纸，松果体定期蒸馏 → 更新三观和自知
- **内环 + 外环**：内环更新自己的看板，外环投到 Colony 共享知识池

> 更多约束细节见 [CATALOG.md](CATALOG.md) 禁止边和写权限约束。

---

## 11. 常用 API 速查

```python
from meowcat.defaults import create_cat, create_colony, KW_BILINGUAL, PROMPT_ZH

# 创建一只猫 — 只需提供 cerebrum（LLM 实现）
cat = create_cat("Kitty", cerebrum=MyLLM(), keyword=KW_BILINGUAL, prompt=PROMPT_ZH)

# 统一感知入口
reply = await cat.perceive("你好！")

# Path — 原子信号
await cat.path_registry.run("deep_reason", prompt="...")
await cat.path_registry.run("locate", query="天气")

# Chain — 路径序列
await cat.chain_registry.run("conversation_chain", message="你好")
await cat.chain_registry.run("maintenance_chain")

# Loop — 闭环执行
await cat.run_loop("conversation", message="你好！")

# 挂载自定义器官
cat.mount("brain", "hippocampus", MyHippocampus())

# Colony 多猫容器
colony = create_colony("my-colony")
cat_a = colony.create_cat("analyst", cerebrum=AnalystBrain())
cat_b = colony.create_cat("executor", cerebrum=ExecutorBrain())
await colony.signal_between("analyst", "executor", "brain", "amygdala", "assess_safety", input=data)

# CatSelf 自我进化
snapshot = cat.cat_self.before_act("conversation")
cat.cat_self.after_act("回答了用户问题", {"topic": "天气"})

# Gateway 大门 + FrontDesk 前台
from meowcat import Gateway
from meowcat.gateway.front_desk import DefaultFrontDesk
from meowcat.plus.gateway import HttpAdapter

fd = DefaultFrontDesk()
fd.plug("on_route", lambda text, ctx, colony: print(f"[audit] {ctx.user_id}: {text[:50]}"))
gw = Gateway(colony, front_desk=fd)
gw.mount_adapter(HttpAdapter(port=8000))
await gw.start()
```

> 完整装配流程和所有默认配置 → **[CATALOG.md](CATALOG.md)**

---

## 11.1 v1.3.6 新能力速查

> 框架层新增 14 个模块，覆盖提示词/持久化/模型货架/管理器/调度/编排。

### OrganPrompt — per-organ 提示插槽

每个脑器官（cerebrum/cerebellum/amygdala/frontal）现在有独立的提示插槽：

```python
from meowcat.organ_prompt import OrganPrompt

# 挂载 per-organ 提示
organ_prompt = OrganPrompt(
    identity="你是一个 Python 开发专家",
    perspective="从代码质量和性能角度思考",
    output_format="用 Markdown 格式回复",
    route_templates={"deep_reason": "请回答: {prompt}"},
)
cat.mount_organ_prompt("cerebrum", organ_prompt)
```

### Hippocampus 持久化（episodes）

```python
# add_episode 返回 episode_id
episode_id = await cat.path_registry.run("add_episode",
    session_id="s1", question="你好", answer="你好！", metadata={})

# 查询 episodes
episodes = await cat.organ("brain", "hippocampus").get_episodes([episode_id])
```

### LLM 模型货架

```python
from meowcat.model_shelf import ModelShelf

shelf = ModelShelf()
# 按供应商入口探测模型列表
models = await shelf.discover("openai", api_key="sk-xxx")
# 注册入架
shelf.register("gpt-4o", ModelConfig(provider="openai", api_key="sk-xxx", model="gpt-4o"))
# FallbackChain 降级链
chain = FallbackChain(["gpt-4o", "deepseek-v3", "ollama"])
result = await chain.run(shelf, prompt="...")
```

### 管理器基类 5 件套

| 模块               | 导入                                      | 用途           |
| ------------------ | ----------------------------------------- | -------------- |
| CompressionManager | `from meowcat.compression import ...`     | 分层压缩策略   |
| RememberPolicy     | `from meowcat.remember_policy import ...` | 三级退避过滤   |
| ClarifyManager     | `from meowcat.clarify import ...`         | 歧义反问检测   |
| BudgetTracker      | `from meowcat.budget import ...`          | 压缩预算 + LRU |
| NoiseFilter        | `from meowcat.noise_filter import ...`    | 噪音正则过滤   |

### 调度/存储/编排

| 模块                 | 导入                                        | 用途               |
| -------------------- | ------------------------------------------- | ------------------ |
| PeriodicScheduler    | `from meowcat.scheduler import ...`         | interval/cron 调度 |
| FocusStore           | `from meowcat.focus import ...`             | Frontal 专注持久化 |
| TopicClosureDetector | `from meowcat.topic_closure import ...`     | 话题闭包检测       |
| CheckpointStore      | `from meowcat.checkpoint import ...`        | 检查点存储         |
| PlanReviser          | `from meowcat.plan_reviser import ...`      | 策略链框架         |
| TaskOrchestrator     | `from meowcat.task_orchestrator import ...` | DAG 拓扑调度       |

### Async 生命周期钩子

`on_start` / `on_shutdown` 钩子现在统一支持同步和异步回调：

```python
# 异步钩子（自动检测 iscoroutinefunction）
async def my_start(cat):
    await load_from_db()
cat.on_start(my_start)

# 同步钩子仍兼容
def my_start_sync(cat):
    print("started")
cat.on_start(my_start_sync)
```

### Telemetry / CircuitBreaker 公开 API

```python
cat.enable_telemetry()
cat.enable_circuit_breaker()
cat.disable_telemetry()
cat.disable_circuit_breaker()
```

---

## 12. 安装 & 测试

```bash
pip install meowcat          # 核心框架
pip install meowcat[plus]    # 含可选扩展（浏览器、ChromaDB、MCP）+ 8 内置工具
pip install -e ".[dev]"      # 开发模式
pytest tests/ -v              # 运行测试
```

Python 3.10+，核心仅依赖 `pydantic>=2.0` + `anyio>=4.0`。
