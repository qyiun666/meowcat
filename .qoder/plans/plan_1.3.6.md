# v1.3.6 框架层升级 — 应用层需求响应

> 需求来源：`../docs/requests/deman_meowagent-v0.7.3_框架层需求.md`（17 项）
> 架构设计：CatSelf → BrainStem 桥接缺口修复
> 策略：可 break 向后兼容（收益足够大），只做框架层

---

## 需求分流总表

| 编号 | 项                       | 决策      | 说明                                                                           |
| ---- | ------------------------ | --------- | ------------------------------------------------------------------------------ |
| D13  | Telemetry/CB 公开 API    | ✅ 接     | 框架缺陷，补公开方法                                                           |
| D14  | Async lifecycle hooks    | ✅ 接     | 框架缺陷，统一 async 支持                                                      |
| D17  | PromptPreset per-organ   | 🔄 重设计 | 不用嵌套模板，用 OrganPrompt 插槽                                              |
| —    | CatSelf → BrainStem 桥接 | 🔄 重设计 | 与 D17 合并设计                                                                |
| D6   | L6 存储默认实现          | 🔄 重设计 | 不叫 L6，并入 Hippocampus episodes 持久化                                      |
| D7   | 存储自动持久化           | 🔄 重设计 | 并入 Hippocampus lifecycle                                                     |
| D1   | LLM 模型货架             | 🔄 重设计 | 供应商目录按认证方式平铺 12 入口 → 配 key → 带出默认 URL → 探测模型 → 选型入架 |
| D2   | CompressionManager       | ✅ 接     | 基类 + 默认阈值                                                                |
| D3   | RememberPolicy           | ✅ 接     | 基类 + 默认退避规则                                                            |
| D4   | ClarifyManager           | ✅ 接     | 基类 + 歧义阈值                                                                |
| D5   | BudgetTracker            | ✅ 接     | 基类 + 预算参数                                                                |
| D8   | 周期调度                 | ✅ 接     | PeriodicScheduler 基类                                                         |
| D9   | Focus 持久化             | ✅ 接     | FocusStore 协议 + 默认 JSON                                                    |
| D10  | PlanReviser              | 🔄 重设计 | 给策略链框架，不给具体 5 策略                                                  |
| D11  | TaskOrchestrator         | 🔄 重设计 | 给 DAG + 依赖 + 派发核心，不给 Kitten                                          |
| D12  | 噪音过滤                 | ✅ 接     | NoiseFilter 基类 + 默认正则                                                    |
| D15  | 话题闭包检测             | ✅ 接     | 生命周期钩子，信号词注册留应用层                                               |
| D16  | CheckpointStore          | ✅ 接     | 协议 + 默认 JSON                                                               |

### 驳回项

| 编号            | 驳回内容      | 理由                                           |
| --------------- | ------------- | ---------------------------------------------- |
| D1 `bind_model` | 器官-模型绑定 | 应用层决策，框架只给货架，不替应用层决定谁用谁 |
| D11 Kitten      | 分身概念      | 应用层特有抽象，框架不引入                     |

---

## 子任务拆解

### Phase 1: 框架缺陷修复（阻塞性）

| 子任务 | 能力域   | 依赖 | 并发 | 内容                                                                                                                                  |
| ------ | -------- | ---- | ---- | ------------------------------------------------------------------------------------------------------------------------------------- |
| T-01   | 代码生成 | 无   | —    | [x] D13: CatBase/Nervous 新增 `enable_telemetry()` / `enable_circuit_breaker()` / `disable_*()` 公开方法，标记 `_nervous` 为 internal |
| T-02   | 代码生成 | 无   | [∥]  | [x] D14: CatBase `on_start`/`on_shutdown` 统一支持 async hook，自动检测 `iscoroutinefunction`，兼容 sync 旧签名                       |

### Phase 2: 提示词系统重构（核心）

| 子任务 | 能力域   | 依赖 | 并发 | 内容                                                                                                                                                        |
| ------ | -------- | ---- | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-03   | 架构设计 | T-01 | —    | [x] 产出 v1.3.6 design.md：OrganPrompt 定义、BrainStem 拼装链路、CatSelf 注入变量、与 PromptPreset 的关系                                                   |
| T-04   | 代码生成 | T-03 | —    | [x] 新增 `OrganPrompt` dataclass（identity/perspective/output_format/route_templates），挂载到 cerebrum/cerebellum 默认空插槽                               |
| T-05   | 代码生成 | T-04 | —    | [x] 重写 `RenovatedBrainstem.build_system_prompt(organ, route, cat_self_snapshot)`：OrganPrompt + CatSelf 性格/三观/自知自动注入 + PromptPreset.post_prompt |
| T-06   | 代码生成 | T-05 | —    | [x] `BrainStemProtocol` 接口签名更新（向后不兼容），同步所有 NoopBrainstem/RenovatedBrainstem 实现                                                          |
| T-07   | 测试编写 | T-06 | —    | [x] OrganPrompt 拼装 + CatSelf 注入 + 路由 fallback 全覆盖测试                                                                                              |

### Phase 3: Hippocampus 持久化

| 子任务 | 能力域   | 依赖 | 并发 | 内容                                                                                                                                |
| ------ | -------- | ---- | ---- | ----------------------------------------------------------------------------------------------------------------------------------- |
| T-08   | 代码生成 | T-02 | [∥]  | [x] `HippocampusProtocol` 新增 `get_episode(id)` / `get_episodes([ids])` 方法，`add_episode` 返回 `episode_id: str`                 |
| T-09   | 代码生成 | T-08 | —    | [x] 新增 `JsonlEpisodeStore` 默认实现（JSONL 追加 + 行号索引），集成到 RenovatedHippocampus                                         |
| T-10   | 代码生成 | T-09 | —    | [x] Hippocampus lifecycle：`on_start` 加载存储，`on_shutdown` 自动 flush（复用 T-02 async hook），移除独立的 L6StorageProtocol 概念 |
| T-11   | 测试编写 | T-10 | —    | episode CRUD + 批量查询 + 持久化恢复全覆盖测试                                                                                      |

### Phase 4: LLM 模型货架（供应商目录 → 探测 → 入架 → 降级）

| 子任务 | 能力域   | 依赖 | 并发 | 内容                                                                                                                                                                                                                                                                                            |
| ------ | -------- | ---- | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-12   | 代码生成 | 无   | —    | 内置供应商目录 12 入口：openai / deepseek / anthropic / minimax-api / minimax-token / aliyun-api / aliyun-token / moonshot / zhipu / baidu / ollama / custom-openai。每条含 display_name + auth_type（api-key / token / none）+ default_base_url。ollama 无 key 走本地，custom 需用户填 key+url |
| T-13   | 代码生成 | T-12 | —    | `ModelShelf.discover(entry, api_key, base_url?)` → 按入口类型调对应模型列表接口（OpenAI 兼容走 `/models`，ollama 走本地 `/api/tags`），返回模型名列表；`ModelConfig` 封装 api_key（`__repr__` 脱敏为 `sk-***`，不序列化）                                                                       |
| T-14   | 代码生成 | T-13 | —    | `ModelShelf.register(name, config)` 入架 + `list()` 列出 + `FallbackChain` 降级链执行器（应用层配置顺序）                                                                                                                                                                                       |
| T-15   | 测试编写 | T-14 | —    | [x] 供应商目录查询 + 探测 mock + 入架/查找/降级链 + key 脱敏全覆盖测试                                                                                                                                                                                                                          |

### Phase 5: 通用 Manager 基类（5 个，可并发）

| 子任务 | 能力域   | 依赖 | 并发 | 内容                                                        |
| ------ | -------- | ---- | ---- | ----------------------------------------------------------- |
| T-16   | 代码生成 | 无   | [∥]  | [x] D2 `CompressionManager` 基类 — 分层压缩策略，阈值可配置 |
| T-17   | 代码生成 | 无   | [∥]  | D3 `RememberPolicy` 基类 — 三级退避，写入前置过滤           |
| T-18   | 代码生成 | 无   | [∥]  | D4 `ClarifyManager` 基类 — 歧义反问，模糊阈值               |
| T-19   | 代码生成 | 无   | [∥]  | D5 `BudgetTracker` 基类 — 压缩预算 + LRU                    |
| T-20   | 代码生成 | 无   | [∥]  | D12 `NoiseFilter` 基类 — worth_remembering 正则过滤         |

### Phase 6: 调度与持久化（4 个，可并发）

| 子任务 | 能力域   | 依赖 | 并发 | 内容                                                                             |
| ------ | -------- | ---- | ---- | -------------------------------------------------------------------------------- |
| T-21   | 代码生成 | T-02 | [∥]  | D8 `PeriodicScheduler` 基类 — interval/cron 注册                                 |
| T-22   | 代码生成 | T-02 | [∥]  | [x] D9 `FocusStore` 协议 + 默认 JSON 实现，挂 lifecycle                              |
| T-23   | 代码生成 | 无   | [∥]  | [x] D15 `TopicClosureDetector` 基类 — detect/summarize/decay/inject 钩子，信号词注册 |
| T-24   | 代码生成 | T-10 | —    | [x] D16 `CheckpointStore` 协议 + 默认 JSON 实现                                      |

### Phase 7: 编排与容错（2 个）

| 子任务 | 能力域   | 依赖 | 并发 | 内容                                                                             |
| ------ | -------- | ---- | ---- | -------------------------------------------------------------------------------- |
| T-25   | 代码生成 | T-14 | [∥]  | D10 `PlanReviser` — 策略链框架，可插拔策略注册，不给具体 5 策略                  |
| T-26   | 代码生成 | T-25 | —    | D11 `TaskOrchestrator` 基类 — DAG + 拓扑排序 + 并行派发核心，不给 SubTask/Kitten |

### Phase 8: 收尾

| 子任务 | 能力域   | 依赖                | 并发 | 内容                                                                                             |
| ------ | -------- | ------------------- | ---- | ------------------------------------------------------------------------------------------------ |
| T-27   | 测试编写 | T-07,T-11,T-15~T-26 | —    | 全量回归 `pytest tests/ -v`，确保无遗漏                                                          |
| T-28   | 文档更新 | T-27                | —    | 更新 AGENTS.md / CATALOG.md / README_CN.md；在 `../docs/CHANGES.md` 写变更公告；需求文档回写状态 |
| T-29   | 代码审查 | T-27                | —    | 全量 review，输出 `../docs/meowcat/v1.3.6/review.md`                                             |

---

## 并发执行建议

```
Phase 1: T-01 + T-02 可并发（无冲突文件）
Phase 2: T-03→T-04→T-05→T-06 串行（同文件），T-07 收尾
Phase 3: T-08→T-09→T-10→T-11 串行（同模块），可与 Phase 4 并发
Phase 4: T-12→T-13→T-14→T-15 串行（同模块），可与 Phase 3 并发
Phase 5: T-16~T-20 全部可并发（5 个独立新文件）
Phase 6: T-21~T-24 全部可并发（4 个独立新文件）
Phase 7: T-25→T-26 串行
Phase 8: T-27→T-28→T-29 串行（收尾）
```

## 版本号

`pyproject.toml` version: `1.3.5` → `1.3.6`
