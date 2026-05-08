# meowcat v1.3.7 · Default Configuration & Execution Catalog

> **开箱即用的一切**：20 器官 + 31 路径 + 8 链条 + 7 循环 + 3 CatSelf 自循环 + 2 反射 + 1 循环序列 + 预设目录 + 接线规则
>
> v1.3.6 新增：OrganPrompt 插槽 · Hippocampus 持久化 · LLM 模型货架 · 管理器基类 5 件套 · 调度/存储/编排/容错
> v1.3.7 新增：Gateway 绑定 Colony + FrontDesk 前台接待员 (Protocol + Pluggable)

`create_cat()` 一行代码做了什么？出厂自带了哪些默认执行流？这里就是答案。

---

## I. Default Assembly — `create_cat()` 全流程

```
工厂函数 create_cat(container, cerebrum, ...)
  │
  ├─ 1. Colony 孵化容器
  │     container.create_cat(name) → CatBase 空壳
  │
  ├─ 2. 器官填充 (二选一模式)
  │     ┌─ 简装修 renovated=True (默认): 20 器官预装 Renovated* 实现
  │     │    • 安全正则 · 关键词路由 · 内存图存储 · 工具集成
  │     │    • 开箱即用 → 用户只需提供 cerebrum
  │     └─ 毛坯   renovated=False:        20 器官全为 Noop* 桩
  │          • 所有方法返回空/安全默认值
  │          • 用于完整控制或接线测试
  │
  ├─ 3. 混合模式 (bare_organs / renovate_organs)
  │     renovated=True  + bare_organs={"amygdala"}     → 简装修但杏仁核留毛坯
  │     renovated=False + renovate_organs={"thalamus"} → 毛坯但丘脑升级简装修
  │
  ├─ 4. 预设注入 (二语 行业 可挂载)
  │     keyword=KW_BILINGUAL → 注入 Ears/Thalamus/Amygdala/Frontal
  │     prompt=PROMPT_ZH     → 注入 Brainstem/Cerebrum
  │
  ├─ 5. 自动装配 mount_known_organs(cat)
  │     OrganHost 逐一 mount → Protocol 校验 → impl_style 兼容性检查
  │
  ├─ 6. 接线 wire_default_nervous_system()
  │     允许边 + 禁止边 → Wiring 有向神经图
  │
  ├─ 7. 内置工具注册 (可选)
  │     register_default_tools=True → BUILTIN_TOOLS → tool_registry
  │
  ├─ 8. 反射弧注入 (调用方提供)
  │     reflexes=[...] → cat.register_reflex(ref) 逐一注册
  │
  ├─ 9. 装配钩子 on_before_freeze
  │     用户注入额外器官 / 接线 / 路径 (在冻结前)
  │
  ├─ 10. 冻结 freeze_nervous_system()
  │      Wiring 不可变 · CircuitBreaker 初始化 · Path/Chain/Loop 注册
  │
  ├─ 11. 装配钩子 on_assembled
  │     冻结后→运行时属性设置 (路径/链条/循环注册已在冻结时完成)
  │
  └─ 返回 → CatBase (完整装配、接线、冻结、就绪)
```

### 装配开关一览

| 参数                      | 默认   | 作用                                                  |
| :------------------------ | :----- | :---------------------------------------------------- |
| `renovated`               | `True` | `True` = 简装修 / `False` = 毛坯                      |
| `bare_organs`             | `None` | 简装修模式下保留毛坯的器官名集合                      |
| `renovate_organs`         | `None` | 毛坯模式下升级简装修的器官名集合                      |
| `keyword`                 | `None` | `KeywordPreset` — 注入 Ears/Thalamus/Amygdala/Frontal |
| `prompt`                  | `None` | `PromptPreset` — 注入 Brainstem/Cerebrum              |
| `register_default_paths`  | `True` | 自动注册 31 条内置路径                                |
| `register_default_chains` | `True` | 自动注册 8 条内置链条                                 |
| `register_default_loops`  | `True` | 自动注册 7 条内置循环                                 |
| `register_default_tools`  | `True` | 自动注册内置工具集                                    |
| `on_before_freeze`        | `None` | 冻结前钩子 — 注入额外器官/接线                        |
| `on_assembled`            | `None` | 冻结后钩子 — 设置运行时属性                           |

---

## II. Built-in Execution Flows

### L1 — Path 路径 (31 built-in)

原子信号：`源器官 → 目标器官.方法`。无 rollback，无 trigger。

#### 记忆域 (Memory)

| 路径                | 信号                                      | 模式  | 说明                 |
| :------------------ | :---------------------------------------- | :---- | :------------------- |
| `locate`            | THALAMUS → THALAMUS.locate                | read  | 记忆搜索（丘脑自环） |
| `remember`          | BRAINSTEM → HIPPOCAMPUS.remember          | write | 存储记忆             |
| `get_entity`        | THALAMUS → HIPPOCAMPUS.get_entity         | read  | 读取单个实体         |
| `get_all`           | THALAMUS → HIPPOCAMPUS.get_all            | read  | 读取全部实体         |
| `fts_search`        | THALAMUS → HIPPOCAMPUS.fts_search         | read  | 全文搜索             |
| `add_entity`        | BRAINSTEM → HIPPOCAMPUS.add_entity        | write | 添加实体             |
| `add_episode`       | BRAINSTEM → HIPPOCAMPUS.add_episode       | write | 添加情节             |
| `connect`           | BRAINSTEM → HIPPOCAMPUS.connect           | write | 连接实体             |
| `record_access`     | BRAINSTEM → HIPPOCAMPUS.record_access     | write | 记录访问             |
| `set_dormant`       | BRAINSTEM → HIPPOCAMPUS.set_dormant       | write | 设为休眠             |
| `append_content`    | BRAINSTEM → HIPPOCAMPUS.append_content    | write | 追加内容             |
| `update_importance` | BRAINSTEM → HIPPOCAMPUS.update_importance | write | 更新重要性           |
| `set_last_seen`     | BRAINSTEM → HIPPOCAMPUS.set_last_seen     | write | 设置最后可见时间     |

#### 推理域 (Reasoning)

| 路径            | 信号                              | 模式 | 说明             |
| :-------------- | :-------------------------------- | :--- | :--------------- |
| `deep_reason`   | THALAMUS → CEREBRUM.generate      | read | 深度推理         |
| `decide_route`  | THALAMUS → THALAMUS.decide_route  | read | 路由决策（自环） |
| `assess_safety` | AMYGDALA → AMYGDALA.assess_safety | read | 安全评估（自环） |

#### 输出域 (Output)

| 路径    | 信号                     | 模式  | 说明     |
| :------ | :----------------------- | :---- | :------- |
| `speak` | CEREBELLUM → MOUTH.speak | write | 输出回复 |
| `hear`  | EARS → THALAMUS.hear     | read  | 接收输入 |

#### 工具域 (Tool)

| 路径           | 信号                      | 模式  | 说明     |
| :------------- | :------------------------ | :---- | :------- |
| `execute_tool` | CEREBELLUM → PAWS.execute | write | 执行工具 |

#### 维护域 (Maintenance)

| 路径                 | 信号                                                  | 模式  | 说明         |
| :------------------- | :---------------------------------------------------- | :---- | :----------- |
| `decay`              | HYPOTHALAMUS → HIPPOCAMPUS.decay                      | write | 记忆衰减     |
| `weaken_connections` | HYPOTHALAMUS → HIPPOCAMPUS.weaken_connections         | write | 弱化连接     |
| `cleanup_orphans`    | HYPOTHALAMUS → HIPPOCAMPUS.cleanup_orphan_connections | write | 清理孤立连接 |

#### 合成 + 生长 + 工作流域

| 路径                  | 信号                                   | 模式  | 说明         |
| :-------------------- | :------------------------------------- | :---- | :----------- |
| `synthesize`          | BRAINSTEM → CORTEX.synthesize          | read  | 世界观合成   |
| `compress_context`    | BRAINSTEM → BRAINSTEM.compress_context | read  | 上下文压缩   |
| `record_anomaly`      | BRAINSTEM → ANOMALY_GROWTH.record      | write | 记录异常模式 |
| `record_correction`   | BRAINSTEM → CORRECTION_GROWTH.record   | write | 记录纠正固化 |
| `crystallize`         | BRAINSTEM → CRYSTALLIZER.crystallize   | write | 技能结晶     |
| `record_pattern`      | BRAINSTEM → ROLE_EMERGENCE.record      | write | 记录角色模式 |
| `workflow_create`     | BRAINSTEM → HIPPOCAMPUS.add_entity     | write | 创建工作流   |
| `workflow_checkpoint` | BRAINSTEM → HIPPOCAMPUS.append_content | write | 写入检查点   |
| `workflow_resume`     | BRAINSTEM → HIPPOCAMPUS.get_entity     | read  | 恢复工作流   |

---

### L2 — Chain 链条 (8 built-in)

命名路径序列。上一步结果作为 `**kwargs` 传入下一步。支持 rollback。

| #   | 链条                  | 路径序列                                                                  | 说明          |
| :-- | :-------------------- | :------------------------------------------------------------------------ | :------------ |
| C1  | `memory_search_chain` | `locate`                                                                  | 记忆搜索      |
| C2  | `conversation_chain`  | `hear` → `decide_route` → `locate` → `deep_reason` → `speak` → `remember` | 完整对话流    |
| C3  | `tool_loop_chain`     | `hear` → `decide_route` → `execute_tool` → `speak` → `remember`           | 工具执行流    |
| C4  | `danger_chain`        | `assess_safety`                                                           | 安全评估      |
| C5  | `maintenance_chain`   | `decay` → `cleanup_orphans`                                               | 记忆维护      |
| C6  | `diagnostic_chain`    | `crystallize`                                                             | 技能结晶诊断  |
| C7  | `growth_chain`        | `record_anomaly` → `crystallize`                                          | 异常学习→结晶 |
| C8  | `reflection_chain`    | `record_correction` → `record_pattern`                                    | 纠错→角色涌现 |

---

### L3 — Loop 循环 (7 built-in + 3 CatSelf)

> 链条 + 触发事件 + 退出事件 = 自主闭环执行

#### LoopRegistry 循环 (7) — 器官间信号编排

```
★ conversation (Loop A: 感知→推理→输出)
  trigger: perceive.start
  chain:   hear → decide_route → locate → deep_reason → speak → remember
  path:    EARS → THALAMUS → CEREBRUM → CEREBELLUM → MOUTH → HIPPOCAMPUS
```

| #   | 循环              | 链条               | 触发器              | 说明            |
| :-- | :---------------- | :----------------- | :------------------ | :-------------- |
| L1  | `conversation`    | conversation_chain | `perceive.start`    | 对话闭环        |
| L2  | `tool_execution`  | tool_loop_chain    | `orchestrate.start` | 工具执行闭环    |
| L3  | `danger_response` | danger_chain       | `amygdala.alert`    | 紧急安全闭环    |
| L4  | `maintenance`     | maintenance_chain  | `heartbeat.tick`    | 体内稳态闭环    |
| L5  | `diagnostic`      | diagnostic_chain   | (手动触发)          | 技能结晶 + 诊断 |
| L6  | `growth`          | growth_chain       | `post_action`       | 异常学习→结晶   |
| L7  | `reflection`      | reflection_chain   | `tool_executed`     | 纠错→角色涌现   |

#### CatSelf 默认循环 (3) — 自意识成长

```
★ 内环：单猫自进化
  before_act(冻结快照) → action → after_act(scribble) → PinealGland.trigger_if() → fuse_to_self → Cortex/Metacognition

★ 外环：集体智能融合
  ScribblePad → PinealGland.trigger_if(on_full/on_timer) → fuse_to_colony → SharedStorage → 其他猫
```

| 循环           | 流程                           | 融合触发                       | 说明                 |
| :------------- | :----------------------------- | :----------------------------- | :------------------- |
| `conversation` | 读自我→聊天→回复→scribble→反思 | `on_event("conversation_end")` | 对话中进化（最常用） |
| `task`         | 读自我→分析→执行→观察→scribble | `on_full(50)`                  | 任务驱动进化         |
| `learn`        | 读自我→盲点→探索→验证→scribble | `trigger()` 即时               | 好奇心驱动学习       |

---

### L4 — LoopSequence 循环序列 (1 built-in)

| #   | 名称                | 循环序列                 | 模式       | 说明          |
| :-- | :------------------ | :----------------------- | :--------- | :------------ |
| LS1 | `daily_maintenance` | maintenance → diagnostic | sequential | 日常维护→检查 |

---

### Reflex 反射 (2 built-in)

> 刺激→响应，零 LLM 依赖。触发时跳过推理直接执行。

| #   | 名称            | 触发器               | 路径                                                        | 跳数 | 说明                              |
| :-- | :-------------- | :------------------- | :---------------------------------------------------------- | :--- | :-------------------------------- |
| R1  | `text_dialogue` | `modality == "text"` | EARS → THALAMUS → BRAINSTEM → CEREBRUM → CEREBELLUM → MOUTH | 5    | 标准文本对话全路径                |
| R2  | `danger`        | 内容匹配危险模式     | EARS → THALAMUS → AMYGDALA → MOUTH                          | 3    | 杏仁核紧急反射 — 绕过大脑直接输出 |

---

## III. Organ Quick Reference

### 9 大脑区域

| 器官             | 角色         | 核心特征                  | 支持 Plug                    | 简装修类型          |
| :--------------- | :----------- | :------------------------ | :--------------------------- | :------------------ |
| **Thalamus**     | 感觉中继枢纽 | 所有输入必经此地          | ALGO / RULE / MODEL / HYBRID | ALGORITHM           |
| **Cerebrum**     | 深度推理     | LLM 驱动，仅 MODEL/HYBRID | MODEL / HYBRID               | — (用户提供)        |
| **Cerebellum**   | 快速响应     | 所有效应器唯一入口        | MODEL / ALGO / HYBRID        | — (默认同 Cerebrum) |
| **Hippocampus**  | 记忆图谱     | 实体-关联存储             | ALGO / MODEL / HYBRID        | ALGORITHM           |
| **Amygdala**     | 安全旁路     | 可无推理直接输出          | ALGO / RULE / MODEL / HYBRID | ALGORITHM           |
| **Frontal**      | 专注与规划   | 话题跟踪、任务分解        | ALGO / MODEL / HYBRID        | ALGORITHM           |
| **Hypothalamus** | 体内稳态     | 记忆衰减、孤立清理        | ALGO / RULE                  | ALGORITHM           |
| **Cortex**       | 世界观蒸馏   | L0→L3 认知管线            | ALGO / MODEL / HYBRID        | ALGORITHM           |
| **Brainstem**    | 总调度       | 协调所有脑区              | ALGO / RULE / MODEL / HYBRID | ALGORITHM           |

### 4 感觉 (SENSE) + 4 效应器

| 器官         | 类别           | 角色                                | 简装修类型 |
| :----------- | :------------- | :---------------------------------- | :--------- |
| **Ears**     | SENSE          | 文本输入 (CLI/API/Discord/Telegram) | ALGORITHM  |
| **Eyes**     | SENSE          | 视觉输入 (图片/视频)                | ALGORITHM  |
| **Whiskers** | SENSE          | 环境感知 (I/O 异常检测)             | ALGORITHM  |
| **Paws**     | SENSE + 效应器 | 工具执行 (Skill/MCP/命令)           | ALGORITHM  |
| **Mouth**    | VOICE          | 语音/文本输出                       | ALGORITHM  |
| **Purr**     | VOICE          | 流式状态指示                        | ALGORITHM  |
| **Tail**     | VOICE          | 状态栏 (CLI/TUI 健康信号)           | ALGORITHM  |

### 5 成长 (GROWTH)

| 器官                 | 角色                               | 简装修类型                 |
| :------------------- | :--------------------------------- | :------------------------- |
| **PinealGland**      | 顿悟融合枢纽 — 碎片→洞察，双向融合 | Pluggable (不在 OrganHost) |
| **AnomalyGrowth**    | 异常沉淀 — 用户标记→持久化         | ALGORITHM                  |
| **CorrectionGrowth** | 纠错固化 — 用户纠正→永久修复       | ALGORITHM                  |
| **Crystallizer**     | 技能晶化 — 高频操作→可复用技能     | ALGORITHM                  |
| **RoleEmergence**    | 角色涌现 — 行为模式→隐式角色       | ALGORITHM                  |

---

## IV. Wiring Reference

### 禁止边 (Forbidden Edges)

> 生物学合理接线约束 — 允许边开放，禁止边硬阻断。禁止优先于允许。

| 禁止边                       | 原因                             |
| :--------------------------- | :------------------------------- |
| CEREBRUM → PAWS              | 大脑不直接控制肢体               |
| CEREBRUM → MOUTH             | 大脑不直接驱动语言               |
| CEREBRUM → ANOMALY_GROWTH    | 大脑不直接触发成长               |
| CEREBRUM → CORRECTION_GROWTH | 大脑不直接触发纠错               |
| CEREBRUM → CRYSTALLIZER      | 大脑不直接结晶技能 (v1.2.17)     |
| CEREBRUM → ROLE_EMERGENCE    | 大脑不直接触发角色涌现 (v1.2.17) |
| CEREBELLUM → CEREBRUM        | 小脑不反馈至大脑                 |
| AMYGDALA → HIPPOCAMPUS       | 杏仁核不直接访问记忆             |
| THALAMUS → CEREBELLUM        | 丘脑不绕行大脑                   |

### 写权限约束

| 目标器官    | 允许写入方                             |
| :---------- | :------------------------------------- |
| HIPPOCAMPUS | BRAINSTEM, HYPOTHALAMUS (仅此二者可写) |

### 默认接线架构

```
SENSE 输入 → THALAMUS (唯一中继)
                ├─→ CEREBRUM (深度推理)
                │     └─→ CEREBELLUM (快速响应) ← AMYGDALA (安全输入)
                │           └─→ MOUTH / PAWS / PURR / TAIL (效应器)
                ├─→ AMYGDALA (安全旁路)
                │     └─→ MOUTH (危险直接输出，零推理)
                ├─→ HIPPOCAMPUS (记忆读写)
                ├─→ FRONTAL (专注/规划)
                └─→ BRAINSTEM (总调度)
                      └─→ 所有器官 (生命周期事件)
```

---

## V. Presets Catalog

### Keyword Presets — 关键词预设

> 注入 Ears / Thalamus / Amygdala / Frontal。每个器官选取自己需要的子集。

| 预设           | 停用词    | 命令 | 危险规则 | 话题词 | 说明             |
| :------------- | :-------- | :--- | :------- | :----- | :--------------- |
| `KW_EN`        | 70 英文词 | 28   | 8 regex  | —      | 英文基础         |
| `KW_ZH`        | 70 中文词 | 36   | 9 regex  | —      | 中文基础         |
| `KW_BILINGUAL` | 中英合并  | 64   | 17 regex | —      | 双语合并（推荐） |

```python
from meowcat.defaults import KW_BILINGUAL, KW_EN, KW_ZH

# 标准双语
cat = create_cat(container=colony, cerebrum=MyLLM(), keyword=KW_BILINGUAL)

# 自定义合并
custom = KW_ZH.merge(KW_EN)
```

### Prompt Presets — 提示词预设

> 注入 Brainstem / Cerebrum。7 条路由模板。

| 预设             | 模板数      | 说明     |
| :--------------- | :---------- | :------- |
| `PROMPT_DEFAULT` | 7 路由 (EN) | 英文默认 |
| `PROMPT_ZH`      | 7 路由 (CN) | 中文默认 |

```python
from meowcat.defaults import PROMPT_DEFAULT, PROMPT_ZH

cat = create_cat(container=colony, cerebrum=MyLLM(), prompt=PROMPT_ZH)
```

---

## VI. Plus Built-in Tools (8)

> 注册到 `cat.tool_registry`，LLM 可直接调用。

| #   | 工具           | 风险 | 类别   | 说明                           |
| :-- | :------------- | :--- | :----- | :----------------------------- |
| T1  | `read_file`    | LOW  | file   | 读取文件内容                   |
| T2  | `write_file`   | HIGH | file   | 写入文件                       |
| T3  | `run_command`  | HIGH | system | 执行 Shell 命令                |
| T4  | `http_get`     | LOW  | web    | HTTP GET 请求                  |
| T5  | `list_dir`     | LOW  | file   | 列出目录（限 200 条）          |
| T6  | `grep_files`   | LOW  | file   | 正则搜索文件（限 300 文件）    |
| T7  | `current_time` | LOW  | util   | 获取当前 UTC/本地时间          |
| T8  | `code_runner`  | HIGH | system | 沙箱执行 Python/JS（10s 超时） |

- **T5-T8** 为 v1.3.0 新增
- `code_runner` 沙箱安全设计：子进程隔离 + `-I` 模式 + 环境变量剥离 + 超时 + 非阻塞 asyncio

---

## VII. Assembly Recipes

```python
from meowcat import create_cat, ImplementationStyle
from meowcat.defaults import KW_BILINGUAL, PROMPT_ZH

# 1. 最简装配 — 只需提供 cerebrum，其余全部简装修
cat = create_cat(container=colony, cerebrum=MyLLM())

# 2. 简装修 + 双语 + 中文提示词
cat = create_cat(container=colony, cerebrum=MyLLM(),
                 keyword=KW_BILINGUAL, prompt=PROMPT_ZH)

# 3. 毛坯 — 全部 Noop 桩，完全自控
cat = create_cat(container=colony, cerebrum=MyLLM(), renovated=False)

# 4. 混合 — 简装修但杏仁核留毛坯（无安全检查）
cat = create_cat(container=colony, cerebrum=MyLLM(),
                 bare_organs={"amygdala"})

# 5. 混合 — 毛坯但丘脑升级简装修
cat = create_cat(container=colony, cerebrum=MyLLM(),
                 renovated=False, renovate_organs={"thalamus"})

# 6. 延迟注册 — 先冻结，手动注册路径/链条/循环
cat = create_cat(container=colony, cerebrum=MyLLM(),
                 register_default_paths=False,
                 register_default_chains=False,
                 register_default_loops=False)
cat.register_default_paths()
cat.register_default_chains()
cat.register_default_loops()

# 7. 装配钩子 — 冻结前注入额外器官/接线
def my_before_freeze(cat):
    cat.wire("thalamus", "my_organ", "my_method")

cat = create_cat(container=colony, cerebrum=MyLLM(),
                 on_before_freeze=my_before_freeze)

# 8. 反射弧注入
from meowcat.reflex import Reflex
my_reflex = Reflex(name="custom_alert", trigger={"type": "urgent"},
                   path=["ears", "thalamus", "amygdala", "mouth"])
cat = create_cat(container=colony, cerebrum=MyLLM(),
                 reflexes=[my_reflex])

# 9. 自选存储后端
cat = create_cat(container=colony, cerebrum=MyLLM(),
                 graph_store=MyGraphStore(),
                 vector_store=MyVectorStore())

# --- 运行时调用 ---

# 路径 (原子信号)
result = await cat.path_registry.run("locate", query="天气")
result = await cat.path_registry.run("deep_reason", prompt="天为什么是蓝的？")

# 链条 (路径序列)
result = await cat.chain_registry.run("conversation_chain", prompt="你好")
result = await cat.chain_registry.run("maintenance_chain")

# 循环 (闭环)
await cat.run_loop("conversation", message="你好！")
await cat.run_loop("maintenance")

# 循环序列
await cat.run_loopseq("daily_maintenance")

# 统一感知入口 — 输入进，回复出
reply = await cat.perceive("今天天气怎么样？")

# 检查装配状态
print(cat.organ("brain", "amygdala").impl_style)  # ImplementationStyle.ALGORITHM
print(cat.list_organs())                            # 所有已挂载器官
print(cat.wiring.describe())                        # 接线图描述
```

---

## VIII. File Index

| 内容                                        | 文件路径                                      |
| :------------------------------------------ | :-------------------------------------------- |
| 公共 API (延迟加载)                         | `meowcat/__init__.py` + `meowcat/_exports.py` |
| 器官坐标 / 类别 / PlugStyle                 | `meowcat/anatomy.py`                          |
| 器官规约 (Slot SSOT)                        | `meowcat/biology.py`                          |
| 器官角色描述                                | `meowcat/organ_roles.py`                      |
| CatBase 装配逻辑                            | `meowcat/assembly.py`                         |
| OrganHost 挂载/校验                         | `meowcat/host.py`                             |
| Wiring 神经接线图                           | `meowcat/wiring.py`                           |
| Nervous 信号调度 + 断路器                   | `meowcat/nervous.py`                          |
| 中间件                                      | `meowcat/middleware.py`                       |
| 事件总线                                    | `meowcat/events.py`                           |
| 事件载荷类型 (v1.2.18)                      | `meowcat/events_payloads.py`                  |
| 遥测 (Tracer+Metrics, v1.2.21)              | `meowcat/telemetry.py`                        |
| Path / BUILTIN_PATHS (31)                   | `meowcat/path.py`                             |
| Chain / BUILTIN_CHAINS (8)                  | `meowcat/chain.py`                            |
| Loop / BUILTIN_LOOPS (7) + LoopSequence (1) | `meowcat/loops.py`                            |
| Reflex / 反射弧 (2)                         | `meowcat/reflex.py`                           |
| CatSelf 统一自我 + 3 默认循环               | `meowcat/biology/cat_self.py`                 |
| PinealGland 顿悟融合                        | `meowcat/biology/pineal_gland.py`             |
| Cortex L0-L3 世界观                         | `meowcat/biology/cortex.py`                   |
| ScribblePad 草稿纸                          | `meowcat/biology/scribble_pad.py`             |
| Fusion + ActiveGrowth                       | `meowcat/biology/`                            |
| 简装修实现 (Renovated\*)                    | `meowcat/defaults/renovated.py`               |
| 毛坯桩 (Noop\*)                             | `meowcat/defaults/organs.py`                  |
| 关键词 + 提示词预设                         | `meowcat/defaults/presets.py`                 |
| 存储参考实现                                | `meowcat/defaults/stores.py`                  |
| create_cat 工厂                             | `meowcat/defaults/factory.py`                 |
| 工具/技能/Paws 核心                         | `meowcat/tools/`                              |
| 可选 I/O: 浏览器/ChromaDB/MCP/网关          | `meowcat/plus/`                               |
| Plus 内置工具 (8)                           | `meowcat/plus/tools/`                         |
| Colony 多猫容器 + 联邦                      | `meowcat/colony/`                             |
| Worker / Scheduler (v1.2.22)                | `meowcat/worker/`                             |
| Gateway 协议（皮肤 + FrontDesk 前台）       | `meowcat/gateway/`                            |
| 测试 (60+ 用例)                             | `tests/`                                      |

### v1.3.6 新增模块

| 内容                           | 文件路径                       |
| :----------------------------- | :----------------------------- |
| OrganPrompt per-organ 提示插槽 | `meowcat/organ_prompt.py`      |
| Hippocampus episodes 持久化    | `meowcat/defaults/episode.py`  |
| LLM 模型货架 (12 供应商)       | `meowcat/model_shelf.py`       |
| CompressionManager 上下文压缩  | `meowcat/compression.py`       |
| RememberPolicy 记忆策略        | `meowcat/remember_policy.py`   |
| ClarifyManager 歧义反问        | `meowcat/clarify.py`           |
| BudgetTracker 压缩预算         | `meowcat/budget.py`            |
| NoiseFilter 噪音过滤           | `meowcat/noise_filter.py`      |
| PeriodicScheduler 周期调度     | `meowcat/scheduler.py`         |
| FocusStore 专注持久化          | `meowcat/focus.py`             |
| TopicClosureDetector 话题闭包  | `meowcat/topic_closure.py`     |
| CheckpointStore 检查点存储     | `meowcat/checkpoint.py`        |
| PlanReviser 策略链框架         | `meowcat/plan_reviser.py`      |
| TaskOrchestrator DAG 编排      | `meowcat/task_orchestrator.py` |

---

> **README** = 门面：亮点 + 生态 + 快速开始
> **CATALOG** = 配置手册：默认装配 + 执行流 + 预设 + 接线
