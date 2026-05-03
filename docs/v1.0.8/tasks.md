# v1.0.8 任务拆解 + 进度跟踪

> 来源: `.qoder/plans/meowcat深版分析_版本拆分计划.md` v1.0.8 章节

## 任务清单

### ✅ Protocol 修正: protocols_brain.py

- [x] AmygdalaProtocol 移除 `tag_emotion`
- [x] HypothalamusProtocol 移除 `wake_by_name` / `wake_by_keywords`
- [x] ThalamusProtocol.locate() 移除 `chroma` / `weights` 参数
- [x] 新增 4 个具名 Growth 协议：AnomalyGrowthProtocol / CorrectionGrowthProtocol / CrystallizerProtocol / RoleEmergenceProtocol
- [x] GrowthProtocol 标记 deprecated
- [x] 更新 `__all__`

### ✅ Protocol 修正: protocols_sense.py

- [x] EarsProtocol 新增 `tag_emotion`
- [x] EyesProtocol 移除 `scan_screen` / `describe`
- [x] PawsProtocol 新增 `execute`，旧方法 deprecated，移除 `get_execution_log`

### ✅ Re-export: protocols.py + **init**.py

- [x] protocols.py re-export 新 Growth 协议
- [x] **init**.py 导出新 Growth 协议

### ✅ Wiring 修正: biology.py

- [x] Whiskers out_edges 加 AMYGDALA + ANOMALY_GROWTH
- [x] Amygdala out_edges 加 ANOMALY_GROWTH + CORRECTION_GROWTH
- [x] EARS out_edges 加 AMYGDALA
- [x] EYES out_edges 加 AMYGDALA
- [x] Growth 四个 protocol 改为各自新协议
- [x] FORBIDDEN_PATHS 加 (CEREBRUM, ANOMALY_GROWTH) + (CEREBRUM, CORRECTION_GROWTH)
- [x] Import 补全新 Growth 协议

### ✅ Noop 同步修正: defaults/organs.py

- [x] NoopAmygdala 移除 `tag_emotion`
- [x] NoopEars 新增 `tag_emotion`（返回 episode 原样）
- [x] NoopEyes 移除 `scan_screen` / `describe`
- [x] NoopPaws 移除 `get_execution_log`，旧方法 delegate 到 `execute`
- [x] NoopHypothalamus 移除 `wake_by_name` / `wake_by_keywords`

### ✅ 测试修正

- [x] test_v051_protocol_checked.py: Ears Dummy 加 tag_emotion
- [x] test_v051_protocol_checked.py: Eyes Dummy 移除 scan_screen/describe
- [x] test_v051_protocol_checked.py: Paws Dummy 加 execute，移除 get_execution_log
- [x] test_v510_builtin_equivalence.py: 更新 golden 边集合（47→53）
- [x] test_v510_builtin_equivalence.py: 更新 golden 协议名称
- [x] test_v510_builtin_equivalence.py: 更新 forbidden 边（2→4）
- [x] test_v510_organ_spec.py: 放宽 sensor out_edges 断言

### ✅ 版本号

- [x] meowcat/pyproject.toml: 1.0.6 → 1.0.8

### ✅ 文档

- [x] docs/meowcat/v1.0.8/README.md
- [x] docs/meowcat/v1.0.8/design.md
- [x] docs/meowcat/v1.0.8/tasks.md（本文件）
- [ ] docs/meowcat/v1.0.8/review.md

## 验收清单

- [x] 610 tests passed (0 failures)
- [x] `__version__` 动态读取 pyproject.toml 正确返回 "1.0.8"
- [x] 新 Growth 协议可从 meowcat import
- [x] wiring 边集合精确 = 53 条（6 条新增）
- [x] forbidden 边 4 条（2 条新增）
- [x] Noop 类 instanceof 对应新 Protocol 全部通过
