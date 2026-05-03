# meowcat v1.0.8 — Protocol 修正 + Wiring 修正 + Growth 具名化

> 版本日期: 2026-05-02 | 改动量: ~120 行 | 测试: 610 passed

## 概述

对 20 个器官的 Protocol 层做审计修正，确保每个器官的职责边界清晰、协议签名正确、神经通路合理。是"meowcat 器官全量审计"三部曲的第二版。

## 主要改动

### Protocol 修正 (5 个)

| 器官             | 改动                                                                   |
| ---------------- | ---------------------------------------------------------------------- |
| **Amygdala**     | 移除 `tag_emotion` → 情绪标注归 Ears                                   |
| **Ears**         | 新增 `tag_emotion`（从 Amygdala 迁移）                                 |
| **Eyes**         | 移除 `scan_screen` / `describe`，只保留 `see`                          |
| **Paws**         | 新增 `execute()` 统一入口，旧方法 deprecated，移除 `get_execution_log` |
| **Hypothalamus** | 移除 `wake_by_name` / `wake_by_keywords` → 检索归 Hippocampus          |
| **Thalamus**     | `locate()` 移除 `chroma`/`weights` 参数 → 协议不暴露搜索后端           |

### Growth 协议具名化

| 旧                        | 新                                                                                                      |
| ------------------------- | ------------------------------------------------------------------------------------------------------- |
| `GrowthProtocol` (无签名) | `AnomalyGrowthProtocol` / `CorrectionGrowthProtocol` / `CrystallizerProtocol` / `RoleEmergenceProtocol` |
| 共用模糊协议              | 四个具名协议，各有明确方法签名                                                                          |

### Wiring 修正

新增 6 条允许边：

- `EARS → AMYGDALA` — 危险语音应激反射
- `EYES → AMYGDALA` — 危险图像应激反射
- `WHISKERS → AMYGDALA` — 注入检测立即告警
- `AMYGDALA → ANOMALY_GROWTH` — 安全事件记录
- `AMYGDALA → CORRECTION_GROWTH` — 纠正记录
- `WHISKERS → ANOMALY_GROWTH` — 异常检测记录

新增 2 条禁止边：

- `CEREBRUM → ANOMALY_GROWTH` — 大脑不直连生长
- `CEREBRUM → CORRECTION_GROWTH` — 同上

### Noop 同步修正

| 改动                                                      | 说明                  |
| --------------------------------------------------------- | --------------------- |
| NoopAmygdala 移除 `tag_emotion`                           | 匹配 Protocol         |
| NoopEars 新增 `tag_emotion`                               | 返回 episode 原样     |
| NoopEyes 移除 `scan_screen` / `describe`                  | 匹配精简后的 Protocol |
| NoopPaws 旧方法 delegate 到 `execute()`                   | 统一入口              |
| NoopPaws 移除 `get_execution_log`                         | 走 EventBus           |
| NoopHypothalamus 移除 `wake_by_name` / `wake_by_keywords` | 匹配 Protocol         |

## 测试

```
610 passed, 1 warning in 0.70s
```

## 下一步

→ v1.0.9: CLI 门面方法 + Colony 别名 + 全量回归
→ meowagent 适配（继承迁移）
