---
trigger: model_decision
description: MeowCat 框架可抽性纪律——从 v0.5.0 起按"本地框架 + 参考应用"双层结构开发，保证未来一抽即发 pypi 的能力。
---

# P-03: MeowCat 可抽性纪律（Extraction-Ready）

> **适用范围**: v0.5.0 及以后（v0.4.x 填坑期不受约束）。
> **核心思想**: meowcat = 猫的生物学蓝图（框架），定义猫有什么器官、怎么连接。meowagent = 用 meowcat 做的一只具体的猫。不引入运行时框架层，只保持代码可抽性。

---

## 一、目录结构（v0.5.0 落地后）

```
MeowAgent/
├── meowcat/              ← 猫框架：猫的生物学蓝图（≤2000 行）
│   ├── __init__.py
│   ├── protocols.py       ← 猫的解剖结构：脑区/感官/声音/存储 所有器官的 Protocol
│   ├── assembly.py        ← Cat 装配基类 + 生命周期
│   ├── pipeline.py        ← Stage + Pipeline 执行器
│   ├── events.py          ← 事件总线（神经系统）
│   ├── loop.py            ← 三大闭环（血液循环）事件常量
│   ├── models.py          ← 通用数据形状（Episode/Entity/SubTask）
│   └── errors.py          ← 框架级异常
│
└── meowagent/            ← 基于 meowcat 的具体项目
    ├── cat/               ← 器官的具体实现（LiteLLM 大脑、SQLite 海马...）
    ├── cli/               ← CLI/TUI（纯 meowagent，框架不管）
    └── ...
```

**单向依赖铁律**：`meowcat/` 永远不能 import `meowagent/`。违反此铁律 = 自动 PR reject。

---

## 二、进/不进 meowcat 判断表

meowcat 定义猫的生物学蓝图——猫有什么器官、器官对外暴露什么方法。
具体用什么材料实现器官，是 meowagent 的事。

| ✅ 能进 meowcat/（猫的蓝图）    | ❌ 不能进 meowcat/（具体实现）            |
| ------------------------------- | ----------------------------------------- |
| 所有器官的 Protocol 接口定义    | 任何器官的具体实现（`class Hippocampus`） |
| Cat 装配骨架（CatBase）         | 具体存储实现（`class SqliteGraphStore`）  |
| Pipeline 执行器                 | 具体感官实现（ASR 代码/Playwright 调用）  |
| 闭环事件名常量                  | CLI / TUI / Textual 组件                  |
| 事件总线（EventBus）            | 业务 prompt 模板                          |
| 通用数据形状（EpisodeShape 等） | 具体 ORM 类（`class Episode`）            |
| 框架级异常                      | 具体适配器 YAML                           |

**关键**：`meowcat/protocols.py` 可以定义 `HippocampusProtocol`（定义海马体对外方法），
但绝不能包含 `class Hippocampus: ...`（那是 meowagent 的事）。

**默认宁可留 meowagent/**。只有被 3 次以上不同器官复用的基础设施，才提升到 meowcat/。

---

## 三、AI 开发自查（每次改代码前后）

### 改代码前问自己

```
□ 这个文件属于 meowcat/ 还是 meowagent/？
□ 如果要加 meowcat/ 文件：有没有违反"不能进"表的任何一项？
□ 如果要让 meowcat/ import 任何东西：来源是 Python 标准库、pydantic、或 meowcat 内部？
  → 不是以上三者的话，停下，改成 meowagent/ 里做
```

### 改代码后问自己

```
□ meowcat/ 有没有 import meowagent/？（必须无）
□ meowcat/ 里有没有写死的具体类名（SqliteGraphStore / LiteLLMProvider / TextualApp 等）？
  → 有的话改成 Protocol 注解
□ 如果现在要把 meowcat/ 目录 cp 到独立 repo 发 pypi，会不会有 import 错误？
  → 会的话说明依赖方向错了
```

---

## 四、新增器官的标准流程（Protocol-First）

1. **先写 Protocol**：在 `meowcat/protocols.py` 定义接口（如 `class TelegramSense(Protocol)`）。如果已有合适 Protocol 就不新增。
2. **再写实现**：在 `meowagent/cat/senses/` 放具体实现。
3. **装配点用接口类型注解**：`self.ears: Sense = TelegramEars(...)`，不写具体类型。
4. **发现 Protocol 不够用**：停下来评估——是 Protocol 粒度错了，还是这个能力根本不该进 meowcat？

---

## 五、切面压测判断（每个 v0.5.x 新功能完成后）

| 完成状态                                     | 含义                         | 行动                               |
| -------------------------------------------- | ---------------------------- | ---------------------------------- |
| 只改 `meowagent/`，`meowcat/` 一行不动       | ✅ 切面对了，Protocol 扛住了 | 继续                               |
| `meowcat/` 骨架小幅扩展（新闭环钩子等）      | 🟡 正常扩展                  | 继续，记录到版本 review            |
| `meowcat/` 多处要改才能支持新功能            | 🚨 抽象抽错了                | **停下来**，重新评估 Protocol 切面 |
| 必须让 `meowcat/` import `meowagent/` 才能跑 | 🚨 方向反了                  | **立即回滚**，重新设计             |

---

## 六、和 P-02 的关系

P-02 原"不引入框架"条款已更新为"保持代码可抽性"。两者一致：

- P-02: 最少代码量、按猫构造切模块、Cat 是唯一组装点
- P-03: 把切模块的边界物理化到 `meowcat/` vs `meowagent/`

**P-03 不增加代码量，只规定代码放哪**。违反 P-03 也违反 P-02。

---

## 七、v0.6.0 分包发 pypi 的预演检查

v0.6.0 正式拆包前，以下检查必须全过：

```
□ meowcat/ 总接口量合理（~3000 行以内；超出时人工复查，不是硬上限）
□ meowcat/ 零 import meowagent
□ meowcat/ 只依赖 Python 标准库 + pydantic（或预先评估过的小依赖）
□ 运行 python -c "import meowcat" 在不装 meowagent 的环境下能成功
□ meowagent 拿掉自身 cat 目录，仅依赖 meowcat + meowcat-defaults 还能跑
□ 单元测试对 meowcat/ 独立存在（不混在 meowagent 测试里）
```

提前按此检查倒推，每个 v0.5.x 版本末尾顺带验证一次。
