# v1.0.8 设计文档 — Protocol 修正 + Wiring 修正 + Growth 具名化

> 来源: `.qoder/plans/meowcat深版分析_版本拆分计划.md` v1.0.8 章节

## 设计目标

对 20 个器官做审计修正：移除放错位置的方法、补齐缺失的协议、具名化模糊接口、修正神经通路。

## Protocol 修正详情

### 1. AmygdalaProtocol — 移除 tag_emotion

**理由**: `tag_emotion` 是输入理解（情绪标注），不是安全检测。Amygdala = 危险检测 + 拒绝/纠正。

### 2. EarsProtocol — 新增 tag_emotion

**理由**: Ears 是输入处理第一站，情绪标注应在此时完成。

### 3. EyesProtocol — 精简为 see 单一方法

**理由**: `scan_screen` 是浏览器/桌面自动化特定功能，`describe` 耦合了文件 IO。只保留通用 `see(bytes, mime)` 方法。

### 4. PawsProtocol — 新增 execute 统一入口

**理由**: `touch_file`/`run_command`/`interact_with_tool` 三个方法本质都是"工具执行"，新增 `execute(tool_name, params)` 作为统一入口。旧方法保留 deprecated。`get_execution_log` 移除（走 EventBus）。

### 5. HypothalamusProtocol — 移除唤醒方法

**理由**: `wake_by_name`/`wake_by_keywords` 本质是调 Hippocampus 检索，不属于下丘脑（稳态维护）职责。

### 6. ThalamusProtocol — locate 签名精简

**理由**: `chroma`（向量搜索后端）和 `weights`（检索权重）是应用层实现细节，不应暴露在框架协议中。

## Growth 具名化设计

旧 `GrowthProtocol` 没有方法签名，等于 `Any`，框架无法验证实现方。四个生长器官各有不同职责：

| 协议                       | 核心方法                                                 | 职责         |
| -------------------------- | -------------------------------------------------------- | ------------ |
| `AnomalyGrowthProtocol`    | `record(reason, snippet, confidence, phase, session_id)` | 异常模式学习 |
| `CorrectionGrowthProtocol` | `record(wrong, correct, session_id, topic)`              | 纠正固化     |
| `CrystallizerProtocol`     | `crystallize(slug, hit_count)` + `hotspots(threshold)`   | 技能结晶     |
| `RoleEmergenceProtocol`    | `record(pattern, evidence)`                              | 角色涌现     |

旧 `GrowthProtocol` 保留为 deprecated 兼容别名。

## Wiring 修正设计

### 新增应激反射直连

```
EARS/EYES/WHISKERS → AMYGDALA
```

感官检测到危险可直接告警杏仁核，绕过丘脑中继——这是哺乳动物的应激反射机制。

### 安全事件直连生长

```
AMYGDALA → ANOMALY_GROWTH / CORRECTION_GROWTH
WHISKERS → ANOMALY_GROWTH
```

安全事件和异常检测可直接写入生长记录，不需要通过 BrainStem 中转。

### 新增禁止边

```
CEREBRUM → ANOMALY_GROWTH / CORRECTION_GROWTH
```

Cerebrum 负责推理，生长是副作用，应与 PAWS/MOUTH 同类约束——统一走 Cerebellum 或 BrainStem。

## 影响分析

### 框架层 (L2)

- Protocol 签名变更：向后不兼容（旧实现有额外方法仍可通过 isinstance，但新实现必须满足新方法）
- Wiring 边新增：packward compatible（只是新增边，旧边不变）
- Noop 实现：同步修正，行为不变

### 应用层 (meowagent) — 待适配

- Ears 需实现 `tag_emotion`
- Paws 需实现 `execute`
- Thalamus.locate 需移除 `chroma`/`weights` 参数
- Eyes 可保留 `scan_screen`/`describe` 作为自有方法（协议不再要求）
- Amygdala 可保留 `tag_emotion` 作为自有方法（协议不再要求）
