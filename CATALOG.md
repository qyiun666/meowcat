# MeowCat v1.1.0 框架层全器官·全链路·全闭环 目录

> 当前版本: 20 器官 / 26 链路 / 6 链路串 / 5 闭环 / 2 反射弧 / 1 闭环编排

---

## 核心概念

```
器官 = 插槽(slot)           ← 入口出口 Protocol + 引脚(in/out edges)
实现 = 插头(plug)           ← 内部实现风格: 算法/规则/正则/模型/任意代码

每个插槽声明了"支持哪些插头类型(supported_styles)"
每个插头声明了"我是哪种实现风格(impl_style)"
开发者任选插头, 可多个按序匹配(fallback), 可扩展新插头
简装 = 默认插头 + 对应代码 (create_cat默认给出)
```

### 插头风格 ImplementationStyle

| 风格 | 值 | 含义 | 典型例子 |
|------|-----|------|----------|
| `ALGORITHM` | `algorithm` | 纯代码 | 正则、字典、字符串、subprocess |
| `RULE` | `rule` | 声明式规则 | 黑白名单、阈值触发、匹配条件 |
| `MODEL` | `model` | ML 模型 | LLM、分类器、嵌入向量 |
| `HYBRID` | `hybrid` | 混合 | 规则优先→模型兜底、多模型投票 |

---

## 一、器官目录 (20个)

### 大脑 Brain (9个)

#### 1. THALAMUS — 丘脑 ★路由分叉点★

```
插槽 (slot):  (brain, thalamus)
协议:          ThalamusProtocol
角色:          Route decision — all input passes through me first
入口(in):      EARS, EYES, WHISKERS (all SENSORS)
出口(out):     CEREBRUM, BRAINSTEM, AMYGDALA, HIPPOCAMPUS
读方法:        locate, decide_route
支持插头:      [algorithm, rule, model, hybrid]
简装插头:      ALGORITHM (关键词匹配 + /命令检测)
毛坯插头:      ALGORITHM (永远返回 route=chat)
```

#### 2. HIPPOCAMPUS — 海马体记忆

```
插槽:          (brain, hippocampus)
协议:          HippocampusProtocol
角色:          Memory — the single entry for store, find, forget
入口(in):      CEREBRUM, FRONTAL, HYPOTHALAMUS, BRAINSTEM
出口(out):     CEREBRUM, CORTEX
读方法:        entities, episodes, locate, get_entity, get_all, get_by_name,
               get_related, stats, fts_search, to_dict
写方法:        remember, add_entity, add_episode, connect, decay,
               weaken_connections, cleanup_orphan_connections, from_dict,
               record_access, set_dormant, append_content,
               update_importance, set_last_seen
写权限:        BRAINSTEM, HYPOTHALAMUS (只有这两个可以写)
支持插头:      [algorithm, model, hybrid]
简装插头:      ALGORITHM (InMemoryGraphStore + 关键词索引)
毛坯插头:      ALGORITHM (空 dict/list)
```

#### 3. CEREBRUM — 大脑皮层 A脑

```
插槽:          (brain, cerebrum)
协议:          LLMBrainProtocol
角色:          Deep reasoning — invokes LLM for complex thinking
入口(in):      THALAMUS, HIPPOCAMPUS, FRONTAL, BRAINSTEM
出口(out):     HIPPOCAMPUS, CEREBELLUM, FRONTAL
方法:          generate(), stream_generate(), reload_config(), diagnose()
支持插头:      [model, hybrid]
简装插头:      MODEL (callable LLM 适配器)
毛坯插头:      ALGORITHM (返回空字符串)
```

#### 4. CEREBELLUM — 小脑 B脑

```
插槽:          (brain, cerebellum)
协议:          LLMBrainProtocol
角色:          Fast response — sole upstream for all effectors
入口(in):      CEREBRUM, AMYGDALA, BRAINSTEM
出口(out):     PAWS, MOUTH, PURR, TAIL (all EFFECTORS)
方法:          generate(), stream_generate(), reload_config(), diagnose()
支持插头:      [model, algorithm, hybrid]
简装插头:      MODEL (callable LLM 适配器)
毛坯插头:      ALGORITHM (返回空字符串)
```

#### 5. AMYGDALA — 杏仁核 安全

```
插槽:          (brain, amygdala)
协议:          AmygdalaProtocol
角色:          Safety review — danger detection + risk assessment
入口(in):      THALAMUS, BRAINSTEM
出口(out):     CEREBELLUM, MOUTH, CEREBRUM, ANOMALY_GROWTH, CORRECTION_GROWTH
方法:          is_rejection, classify_rejection, parse_correction,
               handle_rejection, handle_correction, assess_safety, assess_tool_risk
支持插头:      [algorithm, rule, model, hybrid]
简装插头:      ALGORITHM (中英文正则安全扫描)
毛坯插头:      ALGORITHM (永远返回 safe=True)
```

#### 6. FRONTAL — 额叶 注意力

```
插槽:          (brain, frontal)
协议:          FrontalCortexProtocol
角色:          Focus/Planning — topic management + task decomposition
入口(in):      CEREBRUM, BRAINSTEM
出口(out):     CEREBRUM, HIPPOCAMPUS, BRAINSTEM
方法:          detect_shift, is_continue, archive_focus, update_focus, save, load
支持插头:      [algorithm, model, hybrid]
简装插头:      ALGORITHM (关键词重叠话题检测)
毛坯插头:      ALGORITHM (永远返回 False)
```

#### 7. HYPOTHALAMUS — 下丘脑 稳态

```
插槽:          (brain, hypothalamus)
协议:          HypothalamusProtocol
角色:          Self-maintenance — memory decay + orphan cleanup
入口(in):      BRAINSTEM
出口(out):     HYPOTHALAMUS(自环), HIPPOCAMPUS, CORTEX
方法:          run_maintenance, decay_memories, compress_long_history
支持插头:      [algorithm, rule]
简装插头:      ALGORITHM (TTL 可配置衰减)
毛坯插头:      ALGORITHM (返回空计数)
```

#### 8. CORTEX — 皮层 世界观

```
插槽:          (brain, cortex)
协议:          CortexProtocol
角色:          Worldview — distill cognition from experience
入口(in):      HIPPOCAMPUS, HYPOTHALAMUS, BRAINSTEM
出口(out):     (无 — 终端器官，只被读)
方法:          ingest, record_weakness, weaknesses, synthesize
支持插头:      [algorithm, model, hybrid]
简装插头:      ALGORITHM (4层世界观 dict)
毛坯插头:      ALGORITHM (返回空)
```

#### 9. BRAINSTEM — 脑干 总调度

```
插槽:          (brain, brainstem)
协议:          BrainStemProtocol
角色:          Coordination hub — lifecycle + flow orchestration
入口(in):      THALAMUS
出口(out):     THALAMUS, HIPPOCAMPUS, CEREBRUM, CEREBELLUM, AMYGDALA,
               FRONTAL, HYPOTHALAMUS, CORTEX, ANOMALY_GROWTH,
               CORRECTION_GROWTH, CRYSTALLIZER, ROLE_EMERGENCE,
               EARS, EYES, WHISKERS, MOUTH, PURR, TAIL
方法:          build_system_prompt, cancel_current, diagnose
支持插头:      [algorithm, rule, model, hybrid]
简装插头:      ALGORITHM (PromptPreset 模板构建)
毛坯插头:      ALGORITHM (返回空)
```

---

### 感知 Senses (4个)

#### 10. EARS — 耳朵 文本输入

```
插槽:          (sense, ears)
协议:          EarsProtocol
角色:          Text input — CLI/API/Discord/Telegram
入口(in):      (无 — 纯输入端)
出口(out):     THALAMUS, AMYGDALA
方法:          hear, extract_keywords, detect_language, tag_emotion
支持插头:      [algorithm]
简装插头:      ALGORITHM (文本标准化 + 关键词 + zh/en检测)
毛坯插头:      ALGORITHM (原样返回)
```

#### 11. EYES — 眼睛 视觉

```
插槽:          (sense, eyes)
协议:          EyesProtocol
角色:          Visual input — images/video
入口(in):      (无 — 纯输入端)
出口(out):     THALAMUS, AMYGDALA
方法:          see
支持插头:      [algorithm, model, hybrid]
简装插头:      ALGORITHM (magic bytes 格式检测)
毛坯插头:      ALGORITHM (返回空 dict)
```

#### 12. WHISKERS — 胡须 环境感知

```
插槽:          (sense, whiskers)
协议:          WhiskersProtocol
角色:          Environment sensing — I/O anomaly detection
入口(in):      (无 — 纯输入端)
出口(out):     THALAMUS, AMYGDALA, ANOMALY_GROWTH
方法:          feel_input, feel_output, detect_drift, check_hallucination
支持插头:      [algorithm, model, hybrid]
简装插头:      ALGORITHM (输入/输出感知 + 漂移检测)
毛坯插头:      ALGORITHM (返回空)
```

#### 13. PAWS — 爪子 工具执行

```
插槽:          (sense, paws)
协议:          PawsProtocol
角色:          Tool execution — Skill/MCP/commands
入口(in):      CEREBELLUM (唯一入口! 大脑不直连四肢)
出口(out):     (无 — 终端执行器)
方法:          execute, touch_file, run_command, interact_with_tool
支持插头:      [algorithm, rule, hybrid]
简装插头:      ALGORITHM (tool_registry 集成 + 安全前置)
毛坯插头:      ALGORITHM (返回 ok=False)
```

---

### 输出 Voice (3个)

#### 14. MOUTH — 嘴巴 文本输出

```
插槽:          (voice, mouth)
协议:          MouthProtocol
角色:          Voice output — TTS + text reply
入口(in):      CEREBELLUM, AMYGDALA, BRAINSTEM
出口(out):     (无 — 终端输出器官)
方法:          speak, diagnose
支持插头:      [algorithm]
简装插头:      ALGORITHM (stdout 打印 + 日志)
毛坯插头:      ALGORITHM (返回空字符串)
```

#### 15. PURR — 呼噜 流式

```
插槽:          (voice, purr)
协议:          PurrProtocol
角色:          Streaming status — progress indication
入口(in):      CEREBELLUM, BRAINSTEM
出口(out):     (无 — 终端输出器官)
方法:          stream, diagnose
支持插头:      [algorithm]
简装插头:      ALGORITHM (流式状态跟踪)
毛坯插头:      ALGORITHM (返回 None)
```

#### 16. TAIL — 尾巴 状态栏

```
插槽:          (voice, tail)
协议:          TailProtocol
角色:          Status bar — CLI/TUI health signal
入口(in):      CEREBELLUM, BRAINSTEM
出口(out):     (无 — 终端输出器官)
方法:          render, diagnose
支持插头:      [algorithm]
简装插头:      ALGORITHM (状态栏渲染)
毛坯插头:      ALGORITHM (无操作)
```

---

### 生长 Growth (4个) — Loop C 进化回路

#### 17. ANOMALY_GROWTH — 异常沉淀

```
插槽:          (growth, anomaly_growth)
协议:          AnomalyGrowthProtocol
角色:          Anomaly sedimentation — user-flagged anomalies → persistent
入口(in):      BRAINSTEM, AMYGDALA, WHISKERS
出口(out):     HIPPOCAMPUS, CORTEX
方法:          record, diagnose
支持插头:      [algorithm, model, hybrid]
简装插头:      ALGORITHM (内存异常日志)
毛坯插头:      ALGORITHM (无操作)
```

#### 18. CORRECTION_GROWTH — 校正固化

```
插槽:          (growth, correction_growth)
协议:          CorrectionGrowthProtocol
角色:          Correction solidification — user corrections → permanent fixes
入口(in):      BRAINSTEM, AMYGDALA
出口(out):     HIPPOCAMPUS, CORTEX
方法:          record, diagnose
支持插头:      [algorithm, model, hybrid]
简装插头:      ALGORITHM (内存校正日志)
毛坯插头:      ALGORITHM (无操作)
```

#### 19. CRYSTALLIZER — 技能结晶

```
插槽:          (growth, crystallizer)
协议:          CrystallizerProtocol
角色:          Experience crystallization — frequent ops → reusable skills
入口(in):      BRAINSTEM
出口(out):     (无 — 终端)
方法:          crystallize, hotspots, diagnose
支持插头:      [algorithm, model, hybrid]
简装插头:      ALGORITHM (命中计数器 + 热点检测)
毛坯插头:      ALGORITHM (返回 False/空)
```

#### 20. ROLE_EMERGENCE — 角色涌现

```
插槽:          (growth, role_emergence)
协议:          RoleEmergenceProtocol
角色:          Role emergence — behavior patterns → implicit roles
入口(in):      BRAINSTEM
出口(out):     (无 — 终端)
方法:          record, diagnose
支持插头:      [algorithm, model, hybrid]
简装插头:      ALGORITHM (行为模式日志)
毛坯插头:      ALGORITHM (无操作)
```

---

## 二、禁止边 (Forbidden Edges)

以下边被 `FORBIDDEN_PATHS` 阻止 (blocklist 优先级高于 allowlist):

| 禁止边 | 原因 |
|--------|------|
| CEREBRUM → PAWS | 大脑不直连四肢 (运动皮层→小脑原则) |
| CEREBRUM → MOUTH | 大脑不直接驱动发声 |
| CEREBELLUM → CEREBRUM | 小脑不回传大脑 (单向) |
| AMYGDALA → HIPPOCAMPUS | 杏仁核不直接操作记忆 |
| THALAMUS → CEREBELLUM | 丘脑不直连小脑 (需经大脑或脑干) |

---

## 三、链路目录 Path (26条)

每条 Path = `from_organ → to_organ.method` 原子信号配方。

### 自环路径 (Self-loop, 不走 wiring, 直接方法调用)

| # | 链路名 | 信号 | 模式 | 描述 |
|---|--------|------|------|------|
| P1 | `locate` | THALAMUS → THALAMUS.locate | read | 记忆检索 (丘脑自环) |
| P2 | `decide_route` | THALAMUS → THALAMUS.decide_route | read | **路由分叉** (丘脑自环) |
| P3 | `assess_safety` | AMYGDALA → AMYGDALA.assess_safety | read | 安全检查 (杏仁核自环) |

### 脑桥路径 (跨器官信号)

#### 输入域 (Sense → Brain)

| # | 链路名 | 信号 | 模式 | 描述 |
|---|--------|------|------|------|
| P4 | `hear` | EARS → THALAMUS.hear | read | 文本输入接收 |

#### 推理域 (Brain Internal)

| # | 链路名 | 信号 | 模式 | 描述 |
|---|--------|------|------|------|
| P5 | `deep_reason` | THALAMUS → CEREBRUM.generate | read | 深度推理 (LLM) |

#### 输出域 (Brain → Voice)

| # | 链路名 | 信号 | 模式 | 描述 |
|---|--------|------|------|------|
| P6 | `speak` | CEREBELLUM → MOUTH.speak | write | 文本输出 |

#### 工具域 (Brain → Paws)

| # | 链路名 | 信号 | 模式 | 描述 |
|---|--------|------|------|------|
| P7 | `execute_tool` | CEREBELLUM → PAWS.interact_with_tool | write | 工具执行 |

#### 记忆域 (Brain ↔ Hippocampus)

| # | 链路名 | 信号 | 模式 | 描述 |
|---|--------|------|------|------|
| P8 | `remember` | BRAINSTEM → HIPPOCAMPUS.remember | write | 存储记忆 |
| P9 | `get_entity` | THALAMUS → HIPPOCAMPUS.get_entity | read | 读取实体 |
| P10 | `get_all` | THALAMUS → HIPPOCAMPUS.get_all | read | 读取全部实体 |
| P11 | `fts_search` | THALAMUS → HIPPOCAMPUS.fts_search | read | 全文检索 |
| P12 | `add_entity` | BRAINSTEM → HIPPOCAMPUS.add_entity | write | 添加实体 |
| P13 | `add_episode` | BRAINSTEM → HIPPOCAMPUS.add_episode | write | 添加事件 |
| P14 | `connect` | BRAINSTEM → HIPPOCAMPUS.connect | write | 连接实体 |
| P15 | `record_access` | BRAINSTEM → HIPPOCAMPUS.record_access | write | 记录访问 |
| P16 | `set_dormant` | BRAINSTEM → HIPPOCAMPUS.set_dormant | write | 设置休眠 |
| P17 | `append_content` | BRAINSTEM → HIPPOCAMPUS.append_content | write | 追加内容 |
| P18 | `update_importance` | BRAINSTEM → HIPPOCAMPUS.update_importance | write | 更新重要性 |
| P19 | `set_last_seen` | BRAINSTEM → HIPPOCAMPUS.set_last_seen | write | 设置最后访问时间 |

#### 维护域 (Hypothalamus → Hippocampus)

| # | 链路名 | 信号 | 模式 | 描述 |
|---|--------|------|------|------|
| P20 | `decay` | HYPOTHALAMUS → HIPPOCAMPUS.decay | write | 记忆衰减 |
| P21 | `weaken_connections` | HYPOTHALAMUS → HIPPOCAMPUS.weaken_connections | write | 弱化连接 |
| P22 | `cleanup_orphans` | HYPOTHALAMUS → HIPPOCAMPUS.cleanup_orphan_connections | write | 清理孤立连接 |

#### 合成域 (Brain → Cortex)

| # | 链路名 | 信号 | 模式 | 描述 |
|---|--------|------|------|------|
| P23 | `synthesize` | BRAINSTEM → CORTEX.synthesize | read | 世界观合成 |

#### 工作流域 (Workflow)

| # | 链路名 | 信号 | 模式 | 描述 |
|---|--------|------|------|------|
| P24 | `workflow_create` | BRAINSTEM → HIPPOCAMPUS.add_entity | write | 创建工作流 |
| P25 | `workflow_checkpoint` | BRAINSTEM → HIPPOCAMPUS.append_content | write | 写入检查点 |
| P26 | `workflow_resume` | BRAINSTEM → HIPPOCAMPUS.get_entity | read | 恢复工作流 |

---

## 四、链路串目录 Chain (6条)

每条 Chain = 命名 Path 序列, 上一步结果作为下一步 kwargs。

| # | 链路串 | Path 序列 | 描述 |
|---|--------|-----------|------|
| C1 | `memory_search` | `locate` | 记忆检索 |
| C2 | `full_reasoning` | `deep_reason` → `speak` | 深度推理→输出 |
| C3 | `tool_exec` | `execute_tool` | 工具执行 |
| C4 | `maintenance` | `decay` → `cleanup_orphans` | 记忆维护 |
| C5 | `diagnostic` | (空 — Stethoscope 体检) | 诊断检查 |
| C6 | `workflow_chain` | `workflow_create` → `execute_tool` → `workflow_checkpoint` | 长工作流 |

---

## 五、闭环目录 Loop (5条)

每条 Loop = Chain + trigger 事件 + exit 事件。

### Loop A — 感知-推理-输出闭环

```
CONVERSATION_LOOP
├─ trigger:  perceive.start
├─ chain:    conversation_chain
│   ├─ hear               (EARS → THALAMUS)
│   ├─ decide_route       (THALAMUS 自环 ★分叉★)
│   ├─ locate             (THALAMUS 自环)
│   ├─ deep_reason        (THALAMUS → CEREBRUM)
│   ├─ speak              (CEREBELLUM → MOUTH)
│   └─ remember           (BRAINSTEM → HIPPOCAMPUS)
└─ exit:     (none)
```

| # | 闭环 | 链路串 | 触发事件 | 退出事件 | 描述 |
|---|------|--------|----------|----------|------|
| L1 | `conversation` | hear→decide_route→locate→deep_reason→speak→remember | `perceive.start` | — | **闭环A: 感知-推理-输出** |
| L2 | `tool_execution` | hear→decide_route→execute_tool→speak→remember | `orchestrate.start` | — | 工具执行闭环 |
| L3 | `danger_response` | assess_safety | `amygdala.alert` | — | 安全应急闭环 |
| L4 | `maintenance` | decay→cleanup_orphans | `heartbeat.tick` | — | **闭环B: 稳态维护** |
| L5 | `diagnostic` | (空) | (手动) | — | 健康检查闭环 |

---

## 六、反射弧目录 Reflex (2条)

反射弧 = trigger(匹配条件) + path(器官序列) + stages(可选)。

### R1 — text_dialogue (文本对话反射)

```
trigger:     modality == "text"
path:        EARS → THALAMUS → BRAINSTEM → CEREBRUM → CEREBELLUM → MOUTH
hops:        5
描述:        标准文本对话完整路径
```

### R2 — danger (危险反射)

```
trigger:     内容匹配 danger 模式
path:        EARS → THALAMUS → AMYGDALA → MOUTH (绕过大脑!)
hops:        3
描述:        杏仁核应急反射 — 检测到危险直接输出,不经过推理
```

---

## 七、闭环编排 LoopSequence (1条)

| # | 编排名 | Loop 序列 | 模式 | 描述 |
|---|--------|-----------|------|------|
| LS1 | `daily_maintenance` | maintenance → diagnostic | sequential | 每日维护→体检, 顺序执行 |

---

## 八、关键词 & 提示词预设目录

### 关键词预设 KeywordPreset (8组)

| 预设 | stop_words | 指令数 | 安全规则 | 行业话题 |
|------|-----------|--------|----------|----------|
| `KW_EN` | 70 英文停用词 | 28 | 8 regex | — |
| `KW_ZH` | 70 中文停用词 | 36 | 9 regex | — |
| `KW_BILINGUAL` | zh+en 合并 | 64 | 17 regex | — |
| `KW_TECH` | — | 18 | — | backend/frontend/devops/data |
| `KW_FINANCE` | — | 24 | — | equity/fixed_income/derivatives/risk |
| `KW_MEDICAL` | — | 30 | — | cardiology/neurology/oncology/pediatrics |
| `KW_LEGAL` | — | 24 | — | corporate/ip/employment/compliance |
| `KW_EDUCATION` | — | 22 | — | math/science/language/history |

### 提示词预设 PromptPreset (7组)

| 预设 | 模板数 | pre_prompt | post_prompt |
|------|--------|------------|-------------|
| `PROMPT_DEFAULT` | 7 route | — | 通用安全声明 |
| `PROMPT_ZH` | 7 route (中文) | — | 中文安全声明 |
| `PROMPT_TECH` | 3 route | 高级软件工程师 | 代码质量标准 |
| `PROMPT_FINANCE` | 2 route | 金融分析师 | 投资免责声明 |
| `PROMPT_MEDICAL` | 2 route | 医学知识助手 | 医疗免责声明 |
| `PROMPT_LEGAL` | 1 route | 法律信息助手 | 法律免责声明 |
| `PROMPT_EDUCATION` | 1 route | 耐心教师 | 理解检查建议 |

---

## 九、使用速查

```python
from meowcat import create_cat, ImplementationStyle
from meowcat.defaults import KW_BILINGUAL, PROMPT_ZH, KW_TECH

# 简装猫 (默认)
cat = create_cat("bot", cerebrum=MyCerebrum())

# 简装 + 双语关键词 + 中文提示词
cat = create_cat("bot", cerebrum=MyLLM(), keyword=KW_BILINGUAL, prompt=PROMPT_ZH)

# 毛坯猫 (全部 Noop)
cat = create_cat("bot", cerebrum=MyLLM(), renovated=False)

# 混合: 简装但杏仁核用毛坯
cat = create_cat("bot", cerebrum=MyLLM(), bare_organs={"amygdala"})

# 每器官查看插头
print(cat.organ("brain", "amygdala").impl_style)  # ImplementationStyle.ALGORITHM

# 链路
await cat.path_registry.run("locate", query="天气")
await cat.path_registry.run("deep_reason", prompt="为什么天是蓝的?")

# 链路串
await cat.chain_registry.run("full_reasoning", prompt="...")
await cat.chain_registry.run("maintenance")

# 闭环
await cat.run_loop("conversation", message="你好!")
await cat.run_loop("maintenance")
await cat.run_loopseq("daily_maintenance")
```

---

## 十、文件索引

| 概念 | 文件 |
|------|------|
| 器官坐标 | `meowcat/anatomy.py` |
| 器官规格 (插槽) | `meowcat/biology.py` |
| 器官角色描述 | `meowcat/organ_roles.py` |
| 毛坯实现 (插头) | `meowcat/defaults/organs.py` |
| 简装实现 (插头) | `meowcat/defaults/renovated.py` |
| 关键词 & 提示词预设 | `meowcat/defaults/presets.py` |
| 工厂函数 | `meowcat/defaults/factory.py` |
| 链路 (Path) | `meowcat/path.py` |
| 链路串 (Chain) | `meowcat/chain.py` |
| 闭环 (Loop) | `meowcat/loops.py` |
| 反射弧 (Reflex) | `meowcat/reflex.py` |
| 神经接线 (Wiring) | `meowcat/wiring.py` |
| 信号系统 (Nervous) | `meowcat/nervous.py` |
| 插头风格 (ImplStyle) | `meowcat/anatomy.py` (ImplementationStyle) |
