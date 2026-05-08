# Changelog

All notable changes to MeowCat will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.7] — 2026-05-08

### Changed

- **Gateway 绑定 Colony**：`Gateway(colony)` 取代旧 `Gateway(cat)`，1 Colony : 1 Gateway : N Adapters
- **FrontDesk 新物种**：`DefaultFrontDesk` (Protocol + Pluggable) — 所有外部消息统一由 FrontDesk 路由，支持 `on_route` 插件链（安全门、审计、限流）
- Gateway 不再是器官（不挂在 OrganHost），而是 Colony 的独立子系统
- 具体协议适配器（HTTP/WS/CLI/IPC/Webhook）仍在 `meowcat.plus.gateway`

---

## [1.3.6] — 2026-05-07

### Added

- **ModelShelf**: LLM 模型货架，12 供应商入口探测 + `FallbackChain` 降级链
- **OrganPrompt**: per-organ 提示插槽（cerebrum/cerebellum/amygdala/frontal 独立提示词）
- **Hippocampus episodes 持久化**: `add_episode` 返回 episode_id，支持批量查询和持久化恢复
- **CompressionManager**: 分层上下文压缩策略，阈值可配置
- **RememberPolicy**: 三级退避记忆过滤 + 写入前置过滤
- **ClarifyManager**: 歧义反问检测，模糊阈值可配置
- **BudgetTracker**: 压缩预算追踪 + LRU 驱逐
- **NoiseFilter**: 噪音正则过滤，`worth_remembering` 前置判断
- **PeriodicScheduler**: interval/cron 周期调度基类
- **FocusStore**: Frontal 专注持久化，`JsonFocusStore` 默认实现 + lifecycle 钩子
- **TopicClosureDetector**: 话题闭包检测 — detect/summarize/decay/inject 四阶段管线 + 中英双语信号词
- **CheckpointStore**: 检查点存储基类 + `JsonCheckpointStore` 默认实现
- **PlanReviser**: 策略链框架，`RevisionStrategy` + `RevisionContext` + `RevisionResult`
- **TaskOrchestrator**: DAG 拓扑调度，`TaskNode` + `TaskStatus` + `TaskExecutor`
- CatBase 新增公开 API: `enable_telemetry()`, `disable_telemetry()`, `enable_circuit_breaker()`, `disable_circuit_breaker()`
- Async 生命周期钩子 `on_start` / `on_shutdown` 统一支持同步和异步回调

### Changed

- CATALOG/AGENTS/README_CN 全面同步 v1.3.6 新模块

---

## [1.3.5] — 2026-05-06

### Added

- 全量添加 SPDX 版权头 `(c) 2026 Axonant/qyiun666`
- `create_cat()` 支持预构造 `CatBase` 子类实例
- `create_cat()` 新增 `on_before_mount` 钩子
- `create_cat()` 自动注册默认 `text_dialogue` reflex（`perceive()` 开箱即用）

---

## [1.3.2] — 2026-05-06

### Fixed

- `__version__` 通过 `importlib.metadata` 读取，支持 pip 安装后无 `pyproject.toml` 的场景
- README 代码示例修正：API 调用方式、路径参数、`signal_between` 类型

### Changed

- README 示例去硬编码 model name，改用 provider-bound lazy resolution

---

## [1.3.1] — 2026-05-06

### Added

- Colony UID 自动生成（带版权水印）
- README 双语切换入口

---

## [1.3.0] — 2026-05-06

### Added

- Task Delegation: `delegate_async`（fire-and-forget）+ `await_task`（poll + kitten 健康检查）+ `check_cat`（alive/stuck/dead）
- `signal_between` 超时控制
- CatBase 强制归属容器（Colony），不再允许独立 Cat

### Changed

- 项目文档架构重构
- README/README_CN/CATALOG 重写 — 突出框架定位，meowagent 缩为一句话

---

## [1.2.36] — 2026-05-05

### Changed

- 全框架 `cat_id` → `cat_uid` 命名统一（23 files）

---

## [1.2.35] — 2026-05-05

### Fixed

- 框架级修复 7 项 — wiring 边界条件、reflex 路径校验、空闲 cat 状态

---

## [1.2.0 ~ 1.2.34] — 2026-05-05

### Added

- **CatSelf**: 统一自我 — `before_act` / `after_act` + 3 默认闭环（conversation/task/learn）
- **PinealGland**: 顿悟融合 — 草稿纸蒸馏 → Insight → fuse_to_self / fuse_to_colony
- **ScribblePad**: 草稿纸 — 碎片缓冲 + 过滤 + 日志 + 持久化
- **Cortex L0-L3**: 世界观蒸馏管线 — RuleExtractor + beliefs + Metacognition
- **ActiveGrowth**: 盲点检测 + 工具失败学习 + 热路径观察
- **Colony Federation**: TCP/Redis 跨容器通信
- **Organ Adapters**: 16 个 `AgentOrgan` / `SkillOrgan` 委托包装
- **Event Payloads**: 30+ 结构化事件载荷类型
- **Telemetry**: `Tracer` + `Metrics` + `SignalSpan` 可观测性
- **CircuitBreaker**: 信号级断路器 — 连续失败检测 + 半开探测
- **Middleware**: `SignalLogger` / `RateLimiter` / `TimeoutGuard` / `ContextInjector`
- **Gateway**: `HttpAdapter` / `WsAdapter` / `WebhookAdapter` / `CliAdapter` / `IpcAdapter`
- **CLI**: `CommandRouter` + system commands + colony commands + I18n + `MeowTui`
- **Storage**: `SqliteGraphStore` / `JsonlL6Store` / `JsonlEpisodeStore` / `VectorStore` / `SharedMemoryPool`
- **MCP Client**: `MCPServerConfig` + `MCPTool` 集成
- **Skill Loader**: SKILL.md 文件加载
- **GlobalColonyRegistry**: 跨 Colony 注册
- **Renovated Organs**: 20 器官简装修实现，`ImplementationStyle` 四风格
- **Presets**: `KeywordPreset` (KW_EN/ZH/BILINGUAL) + `PromptPreset` (PROMPT_DEFAULT/ZH)
- **Pluggable**: 通用插件系统基类
- **Pipeline Stages**: `BaseStage` + 6 Noop 桩 + `build_default_pipeline`

### Changed

- CatBase 子系统解耦: `OrganHost` + `Nervous` + `ReflexArc` + `EventBus` 独立可测
- Protocol 校验接入 `signal()` 热路径
- 写权限约束: 仅 Brainstem/Hypothalamus 可写 Hippocampus

---

## [1.1.12] — 2026-05-04

### Added

- 猫舍命令 `/cats` `/adopt` `/release` `/switch` + 诊断 `/health` `/brain`

---

## [1.1.11] — 2026-05-04

### Added

- System commands: `/version` `/wiring` `/inject` `/debug` `/help`

---

## [1.1.3] — 2026-05-04

### Changed

- CatBase 强制归属容器 — 不再允许不归属 Colony 的独立 Cat

---

## [1.1.1] — 2026-05-03

### Changed

- 第三方应用适配框架级改造

---

## [1.1.0] — 2026-05-03

### Changed

- 框架重构 — 架构升级

---

## [1.0.18] — 2026-05-03

### Added

- `BUILTIN_REFLEX_PATHS` 内置反射路径
- `SecurityPolicyProtocol` 安全策略接口

---

## [1.0.17] — 2026-05-03

### Added

- Pipeline Stage 基类 + 6 Noop 桩

---

## [1.0.16] — 2026-05-03

### Added

- 6 缺失的 Noop 生长器官桩 (AnomalyGrowth/CorrectionGrowth/Crystallizer/RoleEmergence 等)

---

## [1.0.15] — 2026-05-03

### Changed

- 英文注释/文档全面翻译
- README 重写
- 版权声明 + CI 修复

---

## [1.0.9] — 2026-05-03

### Added

- Pluggable 插件系统
- Protocol/Wiring 修正
- CLI 门面

---

## [1.0.6] — 2026-05-02

### Fixed

- `__version__` 读取 `pyproject.toml` 路径错误
- 器官数量文档更新 17→20

---

## [1.0.5] — 2026-05-02

### Added

- 独立仓库初始化 — 从 meowagent 中抽取 meowcat 为独立 pip 包
- Sources 移入 `meowcat/` 子目录，支持标准 PyPI 打包
- CI 测试 + PyPI release workflow

---

## [0.2.0] — 2026-05-01

### Added

- 框架独立仓库初始化 — 源码 + 内置 defaults + 128 独立测试
- CatBase 骨架 + OrganHost + Wiring + Nervous + ReflexArc 五子系统
