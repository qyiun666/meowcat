# meowcat 框架层路线图 v1.0.16 → v1.0.18

> 创建日期: 2026-05-03 | 当前版本: v1.0.15
> 原则: 一版一事；框架层只放"每只猫都需要的东西"

---

## 当前已完成 (v1.0.15)

| 组件 | 位置 | 版本 |
|------|------|------|
| Gateway (协议 + 5 适配器) | `gateway/` | v1.0.10 |
| synthesize Path + workflow Paths/Chains | `path.py` + `chain.py` | v1.0.11 |
| Signal Middleware + 4 内置中间件 | `nervous.py` + `middleware.py` | v1.0.13 |
| Lifecycle Hooks (on_start/on_shutdown) | `assembly.py` | v1.0.14 |
| Colony Federation (TCP + Redis) | `colony_transports.py` | v1.0.12 |
| WorkflowShape + _resume/_checkpoint | `models.py` + `assembly.py` | v1.0.15 |
| 14/20 Noop* 器官桩 | `defaults/organs.py` | v1.0.9 |

---

## 实际缺口（3 版）

### v1.0.16 — 补齐 6 个缺失 Noop* 器官桩

**现状**: 20 个器官坐标，14 个有 Noop* 桩。6 个缺失导致 meowagent 无法继承。

| 缺失的 Noop* | 坐标 | Protocol | HOOKS | 模式 |
|-------------|------|----------|-------|------|
| NoopCerebrum | (brain, cerebrum) | LLMBrainProtocol | generate, stream_generate | C |
| NoopCerebellum | (brain, cerebellum) | LLMBrainProtocol | generate, stream_generate | C |
| NoopAnomalyGrowth | (growth, anomaly_growth) | AnomalyGrowthProtocol | record | B |
| NoopCorrectionGrowth | (growth, correction_growth) | CorrectionGrowthProtocol | record | B |
| NoopCrystallizer | (growth, crystallizer) | CrystallizerProtocol | crystallize, hotspots | C |
| NoopRoleEmergence | (growth, role_emergence) | RoleEmergenceProtocol | record | B |

**改动**: `defaults/organs.py` +150 行 + `__init__.py` 导出

**测试**: ~10 个

---

### v1.0.17 — Pipeline Stage 基类 + 默认序列

**现状**: `pipeline.py` 54 行空壳，零内置 Stage。meowagent 自建 11 个无基类可继承。

**改动**:

`pipeline.py` 新增 `BaseStage(Pluggable)` — 声明 HOOKS，默认 `run()` 空实现。

新建 `defaults/stages.py`:
```
NoopIngestStage(BaseStage)     — 输入预处理桩
NoopLocateStage(BaseStage)     — 记忆检索桩
NoopRouteStage(BaseStage)      — 路由决策桩
NoopExecuteStage(BaseStage)    — LLM 执行桩
NoopPostStage(BaseStage)       — 记忆写入桩
NoopCompressStage(BaseStage)   — 上下文压缩桩
build_default_pipeline()       — 返回默认序列
```

**框架改动**: ~120 行

**测试**: ~8 个

---

### v1.0.18 — 小件收束

两个小改动合版：

**1. BUILTIN_REFLEX_PATHS** (`reflex.py`)

```python
BUILTIN_REFLEX_PATHS = {
    "text_dialogue": (EARS, THALAMUS, BRAINSTEM, CEREBRUM, CEREBELLUM, MOUTH),
    "danger":        (EARS, THALAMUS, AMYGDALA, MOUTH),
}
```

只提供路径结构，trigger 由应用层传入。

**2. SecurityPolicyProtocol** (`protocols.py`)

```python
class SecurityPolicyProtocol(Protocol):
    def is_danger(self, input: str) -> bool: ...
    def assess_tool_risk(self, name: str, params: dict) -> dict: ...
```

框架不提供默认 patterns。空猫默认 is_danger → False。

**框架改动**: ~35 行

**测试**: ~6 个

---

## 版本总览

```
v1.0.15  当前                                         14/20 Noop*
v1.0.16  补齐 6 个 Noop* 器官桩                        ~150行
v1.0.17  Pipeline Stage 基类 + 默认序列                ~120行
v1.0.18  Reflex 常量 + Security Protocol                ~35行
───────
合计                                                     ~305行
```

---

## 不提的（框架不该做的）

| 项目 | 原因 |
|------|------|
| Reflection Path/Chain/Loop | 需要 B-model LLM |
| 幻觉检测基类 | 强依赖 LLM 行为特征 |
| 具体 danger patterns | 每应用不同 |
| 飞书/微信平台逻辑 | OAuth/卡片/解密 → 应用层 |

---

## meowagent 适配节点

| meowcat 版本 | meowagent 需做的事 |
|-------------|-------------------|
| v1.0.16 | Cerebrum/Cerebellum + 4 Growth 器官改为继承 Noop* |
| v1.0.17 | 11 个 Stage 改为继承 BaseStage；用 Noop* 替换无逻辑 Stage |
| v1.0.18 | Reflex 路径使用框架常量；安全逻辑挂 SecurityPolicyProtocol |

---

## 设计约束

| 规则 | 说明 |
|------|------|
| 零依赖 meowagent | 框架层不 import meowagent |
| Protocol 优先 | 新接口先定义 Protocol |
| 一版一事 | 设计→开发→审查三会话 |
| 函数 ≤50 行 / 文件 ≤500 行 | |
| Pluggable 优先 | 新 Noop* 继承 Pluggable + HOOKS |
