# meowcat v2.2.0 · Default Configuration & Execution Catalog

> **开箱即用的一切**：20 器官 + 23 路径 + 8 链条 + 7 循环 + 1 循环序列 + 预设目录 + 接线规则
>
> **v2.0 核心变更**：Noop/Renovated 合并为一套 Default · 对话链 6→3 步 · Colony namespace 6→3 · 适配器/工具移入应用层 · 新增 KnowledgeTree
>
> 从 v1.x 升级 → **[MIGRATION_v2.md](MIGRATION_v2.md)**

`create_cat()` 一行代码做了什么？出厂自带了哪些默认执行流？这里就是答案。

---

## I. Default Assembly — `create_cat()` 全流程

```
工厂函数 create_cat(container, cerebrum, ...)
  │
  ├─ 1. Colony 孵化容器
  │     container.create_cat(name) → CatBase 空壳
  │
  ├─ 2. 器官填充（一套 Default 实现）
  │     20 个器官全部预装 Default 实现
  │     开箱即用 → 用户只需提供 cerebrum (LLM)
  │
  ├─ 3. 预设注入（二语 行业 可挂载）
  │     keyword=KW_BILINGUAL → 注入 Ears/Thalamus/Amygdala/Frontal
  │     prompt=PROMPT_ZH     → 注入 Brainstem/Cerebrum
  │
  ├─ 4. 自动装配 mount_known_organs(cat)
  │     OrganHost 逐一 mount → Protocol 校验 → impl_style 兼容性检查
  │
  ├─ 5. 接线 wire_default_nervous_system()
  │     允许边 + 禁止边 → Wiring 有向神经图
  │
  ├─ 6. 反射弧注入 (调用方提供)
  │     reflexes=[...] → cat.register_reflex(ref) 逐一注册
  │
  ├─ 7. 装配钩子 on_before_freeze
  │     用户注入额外器官 / 接线 / 路径 (在冻结前)
  │
  ├─ 8. 冻结 freeze_nervous_system()
  │     Wiring 不可变 · CircuitBreaker 初始化 · Path/Chain/Loop 注册
  │
  ├─ 9. 装配钩子 on_assembled
  │     冻结后→运行时属性设置
  │
  └─ 返回 → CatBase (完整装配、接线、冻结、就绪)
```

> v2.0 变更: 不再有 renovated/bare_organs/renovate_organs 参数和 register_default_tools 参数。

### 装配开关一览

| 参数                      | 默认   | 作用                                                  |
| :------------------------ | :----- | :---------------------------------------------------- |
| `keyword`                 | `None` | `KeywordPreset` — 注入 Ears/Thalamus/Amygdala/Frontal |
| `prompt`                  | `None` | `PromptPreset` — 注入 Brainstem/Cerebrum              |
| `register_default_paths`  | `True` | 自动注册 23 条内置路径                                |
| `register_default_chains` | `True` | 自动注册 8 条内置链条                                 |
| `register_default_loops`  | `True` | 自动注册 7 条内置循环                                 |
| `on_before_freeze`        | `None` | 冻结前钩子 — 注入额外器官/接线                        |
| `on_assembled`            | `None` | 冻结后钩子 — 设置运行时属性                           |

---

## II. Built-in Execution Flows

### L1 — Path 路径 (23 built-in)

原子信号：`源器官 → 目标器官.方法`。

#### 记忆域 (Memory) — 3 条

| 路径             | 信号                                   | 模式  | 说明     |
| :--------------- | :------------------------------------- | :---- | :------- |
| `locate`         | THALAMUS → THALAMUS.locate             | read  | 记忆检索 |
| `remember`       | BRAINSTEM → HIPPOCAMPUS.remember       | write | 存储记忆 |
| `append_content` | BRAINSTEM → HIPPOCAMPUS.append_content | write | 追加内容 |

#### 推理域 (Reasoning) — 3 条

| 路径            | 信号                              | 模式 | 说明     |
| :-------------- | :-------------------------------- | :--- | :------- |
| `deep_reason`   | THALAMUS → CEREBRUM.generate      | read | 深度推理 |
| `decide_route`  | THALAMUS → THALAMUS.decide_route  | read | 路由决策 |
| `assess_safety` | AMYGDALA → AMYGDALA.assess_safety | read | 安全评估 |

#### 输出域 (Output) — 2 条

| 路径    | 信号                     | 模式  | 说明     |
| :------ | :----------------------- | :---- | :------- |
| `speak` | CEREBELLUM → MOUTH.speak | write | 输出回复 |
| `hear`  | EARS → THALAMUS.hear     | read  | 接收输入 |

#### 工具 + 维护 + 合成 — 4 条

| 路径               | 信号                                                  | 模式  | 说明       |
| :----------------- | :---------------------------------------------------- | :---- | :--------- |
| `execute_tool`     | CEREBELLUM → PAWS.execute                             | write | 执行工具   |
| `decay`            | HYPOTHALAMUS → HIPPOCAMPUS.decay                      | write | 记忆衰减   |
| `cleanup_orphans`  | HYPOTHALAMUS → HIPPOCAMPUS.cleanup_orphan_connections | write | 清理孤立   |
| `compress_context` | BRAINSTEM → BRAINSTEM.compress_context                | write | 上下文压缩 |

#### 生长域 (Growth) — 4 条

| 路径                | 信号                                 | 模式  | 说明     |
| :------------------ | :----------------------------------- | :---- | :------- |
| `record_anomaly`    | BRAINSTEM → ANOMALY_GROWTH.record    | write | 记录异常 |
| `record_correction` | BRAINSTEM → CORRECTION_GROWTH.record | write | 记录纠正 |
| `crystallize`       | BRAINSTEM → CRYSTALLIZER.crystallize | write | 技能结晶 |
| `record_pattern`    | BRAINSTEM → ROLE_EMERGENCE.record    | write | 角色模式 |

#### 工作流域 (Orchestration) — 3 条

| 路径                  | 信号                                   | 模式  | 说明       |
| :-------------------- | :------------------------------------- | :---- | :--------- |
| `workflow_create`     | BRAINSTEM → HIPPOCAMPUS.add_entity     | write | 创建工作流 |
| `workflow_checkpoint` | BRAINSTEM → HIPPOCAMPUS.append_content | write | 写入检查点 |
| `workflow_resume`     | BRAINSTEM → HIPPOCAMPUS.get_entity     | read  | 恢复工作流 |

#### 知识树域 (Tree) — 4 条 🆕 v2.0

| 路径            | 信号                                 | 模式  | 说明       |
| :-------------- | :----------------------------------- | :---- | :--------- |
| `get_tree`      | THALAMUS → HIPPOCAMPUS.get_tree      | read  | 读取知识树 |
| `search_tree`   | THALAMUS → HIPPOCAMPUS.search_tree   | read  | 搜索树节点 |
| `query_subtree` | THALAMUS → HIPPOCAMPUS.query_subtree | read  | 查询子树   |
| `build_tree`    | BRAINSTEM → HIPPOCAMPUS.build_tree   | write | 构建知识树 |

---

### L2 — Chain 链条 (8 built-in)

| #   | 链条               | 路径序列                                                   | 说明          |
| :-- | :----------------- | :--------------------------------------------------------- | :------------ |
| C1  | `memory_search`    | `locate`                                                   | 记忆搜索      |
| C2  | `full_reasoning`   | `deep_reason` → `speak`                                    | 推理+输出     |
| C3  | `tool_exec`        | `execute_tool`                                             | 工具执行      |
| C4  | `maintenance`      | `decay` → `cleanup_orphans`                                | 记忆维护      |
| C5  | `diagnostic`       | `crystallize`                                              | 技能结晶诊断  |
| C6  | `workflow_chain`   | `workflow_create` → `execute_tool` → `workflow_checkpoint` | 工作流单步    |
| C7  | `growth_chain`     | `record_anomaly` → `crystallize`                           | 异常学习→结晶 |
| C8  | `reflection_chain` | `crystallize`                                              | 执行后反思    |

---

### L3 — Loop 循环 (7 built-in)

| #   | 循环              | 链条 (内联)                               | 触发器              | 说明            |
| :-- | :---------------- | :---------------------------------------- | :------------------ | :-------------- |
| L1  | `conversation`    | hear → deep_reason → speak                | `perceive.start`    | 对话闭环        |
| L2  | `tool_execution`  | hear → execute_tool → speak               | `orchestrate.start` | 工具执行闭环    |
| L3  | `danger_response` | assess_safety                             | `amygdala.alert`    | 紧急安全闭环    |
| L4  | `maintenance`     | maintenance_chain (decay→cleanup_orphans) | `heartbeat.tick`    | 体内稳态闭环    |
| L5  | `diagnostic`      | diagnostic_chain (crystallize)            | (手动触发)          | 技能结晶 + 诊断 |
| L6  | `growth`          | growth_chain (record_anomaly→crystallize) | `post_action`       | 异常学习→结晶   |
| L7  | `reflection`      | reflection_chain (crystallize)            | `tool_executed`     | 执行后反思      |

> v2.0 变更: conversation loop 从 6 步简化为 3 步（hear → deep_reason → speak）。decide_route 吸收进 Thalamus.hear()，locate 由 deep_reason 内部触发，remember 改为 post_loop 异步事件。

---

### CatSelf 房间闭环 (ReflectionLoop)

v2.0 中 3 个独立 Loop 类合并为统一的 `ReflectionLoop`：

```python
from meowcat.biology.cat_self_loops import ReflectionLoop

# 对话后反思
loop = ReflectionLoop(mode="conversation", fusion_trigger="event")
# 任务驱动（草稿纸满 50 条触发）
loop = ReflectionLoop(mode="task", fusion_trigger="full:50")
# 学时驱动（立即蒸馏）
loop = ReflectionLoop(mode="learn", fusion_trigger="immediate")
```

> v2.0 变更: CatSelf 不再自动创建，由应用层 `cat.cat_self = CatSelf()` 自行管理。

---

### L4 — LoopSequence 循环序列 (1)

| #   | 名称                | 循环序列                 | 说明      |
| :-- | :------------------ | :----------------------- | :-------- |
| LS1 | `daily_maintenance` | maintenance → diagnostic | 维护→检查 |

---

### Reflex 反射 (2 built-in)

> v2.0: 反射 API 不变，框架层保留反射弧机制。

| #   | 名称            | 触发器               | 路径                                                        | 说明                     |
| :-- | :-------------- | :------------------- | :---------------------------------------------------------- | :----------------------- |
| R1  | `text_dialogue` | `modality == "text"` | EARS → THALAMUS → BRAINSTEM → CEREBRUM → CEREBELLUM → MOUTH | 标准文本对话全路径       |
| R2  | `danger`        | 内容匹配危险模式     | EARS → THALAMUS → AMYGDALA → MOUTH                          | 杏仁核紧急反射，绕过大脑 |

---

## III. Organ Quick Reference

### 9 大脑区域

| 器官             | 角色         | 核心特征               | 支持 Plug    |
| :--------------- | :----------- | :--------------------- | :----------- |
| **Thalamus**     | 感觉中继枢纽 | 所有输入必经此地       | ALGO / MODEL |
| **Cerebrum**     | 深度推理     | LLM 驱动，仅 MODEL     | MODEL        |
| **Cerebellum**   | 快速响应     | 所有效应器唯一入口     | MODEL / ALGO |
| **Hippocampus**  | 记忆图谱     | 实体-关联存储 + 知识树 | ALGO / MODEL |
| **Amygdala**     | 安全旁路     | 可无推理直接输出       | ALGO / MODEL |
| **Frontal**      | 专注与规划   | 话题跟踪、任务分解     | ALGO / MODEL |
| **Hypothalamus** | 体内稳态     | 记忆衰减、孤立清理     | ALGO         |
| **Cortex**       | 世界观蒸馏   | L0→L3 认知管线         | ALGO / MODEL |
| **Brainstem**    | 总调度       | 协调所有脑区           | ALGO / MODEL |

### 4 感觉 (SENSE) + 4 效应器

| 器官         | 类别           | 角色          |
| :----------- | :------------- | :------------ |
| **Ears**     | SENSE          | 文本输入      |
| **Eyes**     | SENSE          | 视觉输入      |
| **Whiskers** | SENSE          | 环境感知      |
| **Paws**     | SENSE + 效应器 | 工具执行      |
| **Mouth**    | VOICE          | 语音/文本输出 |
| **Purr**     | VOICE          | 流式输出      |
| **Tail**     | VOICE          | 状态显示      |

### 5 成长 (GROWTH)

| 器官                 | 角色                               |
| :------------------- | :--------------------------------- |
| **PinealGland**      | 顿悟融合枢纽 — 碎片→洞察，双向融合 |
| **AnomalyGrowth**    | 异常沉淀 — 用户标记→持久化         |
| **CorrectionGrowth** | 纠错固化 — 用户纠正→永久修复       |
| **Crystallizer**     | 技能晶化 — 高频操作→可复用技能     |
| **RoleEmergence**    | 角色涌现 — 行为模式→隐式角色       |

---

## IV. Wiring Reference

### 禁止边 (Forbidden Edges)

| 禁止边                       | 原因                   |
| :--------------------------- | :--------------------- |
| CEREBRUM → PAWS              | 大脑不直接控制肢体     |
| CEREBRUM → MOUTH             | 大脑不直接驱动语言     |
| CEREBRUM → ANOMALY_GROWTH    | 大脑不直接触发成长     |
| CEREBRUM → CORRECTION_GROWTH | 大脑不直接触发纠错     |
| CEREBRUM → CRYSTALLIZER      | 大脑不直接结晶技能     |
| CEREBRUM → ROLE_EMERGENCE    | 大脑不直接触发角色涌现 |
| CEREBELLUM → CEREBRUM        | 小脑不反馈至大脑       |
| AMYGDALA → HIPPOCAMPUS       | 杏仁核不直接访问记忆   |
| THALAMUS → CEREBELLUM        | 丘脑不绕行大脑         |

### 写入约束

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
                │     └─→ MOUTH (危险直接输出)
                ├─→ HIPPOCAMPUS (记忆读写)
                ├─→ FRONTAL (专注/规划)
                └─→ BRAINSTEM (总调度)
                      └─→ 所有器官 (生命周期事件)
```

---

## V. Presets Catalog

### Keyword Presets

> 注入 Ears / Thalamus / Amygdala / Frontal。每个器官选取自己需要的子集。

| 预设           | 停用词    | 命令 | 危险规则 | 说明             |
| :------------- | :-------- | :--- | :------- | :--------------- |
| `KW_EN`        | 70 英文词 | 28   | 8 regex  | 英文基础         |
| `KW_ZH`        | 70 中文词 | 36   | 9 regex  | 中文基础         |
| `KW_BILINGUAL` | 中英合并  | 64   | 17 regex | 双语合并（推荐） |

### Prompt Presets

> 注入 Brainstem / Cerebrum。7 条路由模板。

| 预设             | 模板数      | 说明     |
| :--------------- | :---------- | :------- |
| `PROMPT_DEFAULT` | 7 路由 (EN) | 英文默认 |
| `PROMPT_ZH`      | 7 路由 (CN) | 中文默认 |

---

## VI. KnowledgeTree 🆕 v2.0

```python
from meowcat.tree import TreeNode

# 构建知识树
root = TreeNode(
    id="root", entity_id="proj-1", parent_id=None,
    path="/", node_type="project", name="my-project",
)

node = TreeNode(
    id="n1", entity_id="proj-1", parent_id="root",
    path="/src", node_type="directory", name="src",
)
root.children.append(node)

cat.hippocampus.build_tree("proj-1", root)

# 查询
tree = cat.hippocampus.get_tree("proj-1")
nodes = cat.hippocampus.search_tree("proj-1", "keyword", limit=5)
sub = cat.hippocampus.query_subtree("proj-1", "n1", max_depth=2)
stale = cat.hippocampus.check_tree_stale("proj-1")

# 删除
cat.hippocampus.delete_tree("proj-1")
```

---

## VII. RuleSet 统一规则引擎 🆕 v2.1.0

```python
from meowcat.ruleset import Rule, RuleSet

rs = RuleSet(
    always_on=[
        Rule("安全守则", "不要删除数据库", "critical"),
    ],
    per_route={
        "deep_reason": [Rule("SQL规范", "必须参数化查询", "high")],
        "tool_use": [Rule("工具约束", "只读优先", "medium")],
    },
    output_format_block="使用 Markdown 格式回复",
)

cat.rule_set = rs
# Brainstem.build_system_prompt() 自动注入 <rules> XML 块
# cerebrum.generate() 兜底注入（不走 Brainstem 也生效）
# cat.rule_set = None 时行为不变
```

---

## VIII. TaskPad + do_task + spawn_worker 🆕 v2.2.0

### 8.1 TaskPad — 任务清单

```python
from meowcat.biology.task_pad import TaskPad

pad = TaskPad(max_tasks=50)
item = pad.post("写一个登录函数")          # TaskItem(TODO)
pad.mark_doing(item.task_id)
result = await cat.do_task(item.content)   # 大脑-工具多轮循环
pad.mark_done(item.task_id, result.final_text)

# 或标记失败
pad.mark_failed(item.task_id, "超时未完成")

todos = pad.list_todo()           # 仅返回 TODO 状态
diag = pad.diagnose()             # {"count": 5, "by_status": {...}}
```

### 8.2 do_task() — 大脑-工具多轮循环

```python
from meowcat.tools.tool_call import TaskResult, XmlToolCallParser

result: TaskResult = await cat.do_task(
    "写一个登录函数",
    max_rounds=5,
    timeout=120.0,
    parser=XmlToolCallParser(),
)
print(result.final_text)   # 最终答案
print(result.rounds)       # 执行的轮次
print(result.tool_calls)   # [ToolCall(name="read_file", params={...}), ...]
```

### 8.3 spawn_worker() — 召唤分身猫

```python
worker = cat.spawn_worker(
    "helper",               # 分身猫名字
    "检索用户表结构",        # 待办任务 (自动发布到分身 TaskPad)
    allowed_organs=frozenset({"cat_uid", "name", "container", "task_pad"}),
)
worker.parent_id == cat.cat_uid         # True
worker.task_pad.list_todo()             # 分身独立的待办清单
```

---

## IX. Assembly Recipes

```python
from meowcat.defaults import create_cat, KW_BILINGUAL, PROMPT_ZH
from meowcat.colony import Colony
from meowcat.biology.cat_self import CatSelf

colony = Colony()

# 1. 最简装配 — 只需提供 cerebrum
cat = create_cat(container=colony, cerebrum=MyLLM())

# 2. 双语 + 中文提示词
cat = create_cat(container=colony, cerebrum=MyLLM(),
                 keyword=KW_BILINGUAL, prompt=PROMPT_ZH)

# 3. CatSelf 由应用层自行创建 (v2.0)
cat.cat_self = CatSelf()

# 4. 延迟注册 — 先冻结，手动注册路径/链条/循环
cat = create_cat(container=colony, cerebrum=MyLLM(),
                 register_default_paths=False,
                 register_default_chains=False,
                 register_default_loops=False)

# 5. 装配钩子
def my_before_freeze(cat):
    cat.wire("thalamus", "my_organ", "my_method")
cat = create_cat(container=colony, cerebrum=MyLLM(),
                 on_before_freeze=my_before_freeze)

# 6. 替换单个器官
cat = create_cat(container=colony, cerebrum=MyLLM(),
                 hippocampus=MyCustomHippocampus())

# 7. 知识树 (v2.0)
from meowcat.tree import TreeNode
root = TreeNode(id="r", entity_id="e1", parent_id=None,
                path="/", node_type="project", name="p")
cat.hippocampus.build_tree("e1", root)

# --- 运行时调用 ---
# 路径
result = await cat.path_registry.run("deep_reason", prompt="t?")
# 链条
result = await cat.chain_registry.run("full_reasoning", prompt="t?")
# 循环
async for event in cat.perceive("今天天气怎么样？"):
    pass
# 循环序列
await cat.loopseq_registry.run("daily_maintenance")
```

---

## X. File Index

| 内容                          | 文件路径                                 |
| :---------------------------- | :--------------------------------------- |
| 公共 API (延迟加载)           | `meowcat/__init__.py`                    |
| 器官坐标 / 类别 / PlugStyle   | `meowcat/anatomy.py`                     |
| 器官规格定义                  | `meowcat/biology/organ_spec.py`          |
| CatBase 装配逻辑              | `meowcat/assembly.py`                    |
| OrganHost 挂载/校验           | `meowcat/host.py`                        |
| Wiring 神经接线图             | `meowcat/wiring.py`                      |
| Nervous 信号调度 + 断路器     | `meowcat/nervous.py`                     |
| 事件总线                      | `meowcat/events.py`                      |
| 遥测                          | `meowcat/telemetry.py`                   |
| Path / BUILTIN_PATHS (23)     | `meowcat/path.py`                        |
| Chain / BUILTIN_CHAINS (8)    | `meowcat/chain.py`                       |
| Loop / BUILTIN_LOOPS (7)      | `meowcat/loops.py`                       |
| Reflex / 反射弧 (2)           | `meowcat/reflex.py`                      |
| CatSelf + ReflectionLoop      | `meowcat/biology/cat_self.py`            |
| PinealGland 顿悟融合          | `meowcat/biology/pineal_gland.py`        |
| Cortex L0-L3 世界观           | `meowcat/biology/cortex.py`              |
| ScribblePad 草稿纸            | `meowcat/biology/scribble_pad.py`        |
| 知识树 (TreeNode) 🆕          | `meowcat/tree.py`                        |
| 规则引擎 (RuleSet) 🆕 v2.1    | `meowcat/ruleset/`                       |
| TaskPad 任务清单 🆕 v2.2      | `meowcat/biology/task_pad.py`            |
| ToolCall 工具调用 🆕 v2.2     | `meowcat/tools/tool_call.py`             |
| Default 器官实现              | `meowcat/defaults/organs/`               |
| 关键词 + 提示词预设           | `meowcat/defaults/presets/`              |
| 存储参考实现                  | `meowcat/defaults/stores.py`             |
| create_cat 工厂               | `meowcat/defaults/factory.py`            |
| Hippocampus 默认实现          | `meowcat/defaults/organs/hippocampus.py` |
| 工具/技能/Paws 核心           | `meowcat/tools/`                         |
| 可选扩展 (chroma_store 等)    | `meowcat/plus/`                          |
| Colony 多猫容器               | `meowcat/colony/`                        |
| Gateway 皮肤 + FrontDesk 前台 | `meowcat/gateway/`                       |
| 器官适配器                    | `meowcat/adapters/`                      |
| 管理器模块 (11 个)            | `meowcat/*.py`                           |

> v2.0 移除: `meowcat/cli/`, `meowcat/plus/gateway/`, `meowcat/plus/tools/`, `meowcat/plus/browser.py`, `meowcat/plus/mcp_client.py`, `meowcat/defaults/renovated/`, `meowcat/colony/delegation.py`, `meowcat/colony/federation.py`, `meowcat/colony/transports.py`, `meowcat/colony/registry.py`, `meowcat/colony/llm_shelf.py`, `meowcat/biology/fusion_cycle.py`, `meowcat/biology/metacognition.py`, `meowcat/biology/roles.py`, `meowcat/biology/cat_self_loops.py` (重写)

---

> **README** = 门面：亮点 + 生态 + 快速开始
> **CATALOG** = 配置手册：默认装配 + 执行流 + 预设 + 接线
> **AGENTS** = 应用开发者心智模型
