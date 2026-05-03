---
trigger: model_decision
description: MeowAgent 项目开发哲学，模块边界、最少代码量、猫的构造隐喻。当开发或修改 MeowAgent 模块时使用此规则。
---

# P-02: MeowAgent 开发哲学

## 核心原则

三个词概括：**像猫一样写代码**。

### 1. 按猫的构造切模块

每只 Cat 的脑区就是模块边界：

| 脑区                | 文件              | 职责      | 禁止       |
| ------------------- | ----------------- | --------- | ---------- |
| 丘脑 Thalamus       | `thalamus.py`     | 路由分发  | 存业务逻辑 |
| 海马 Hippocampus    | `hippocampus.py`  | 记忆存取  | 管路由     |
| 大脑 Cerebrum       | `cerebrum.py`     | B模型调用 | 管记忆     |
| 小脑 Cerebellum     | `cerebellum.py`   | A模型调用 | 管记忆     |
| 额叶 Cortex         | `cortex.py`       | 世界观    | 管路由     |
| 杏仁核 Amygdala     | `amygdala.py`     | 否定修正  | 管生成     |
| 下丘脑 Hypothalamus | `hypothalamus.py` | 生长驱动  | 管调用     |

**Cat 是唯一组装点**：`agent.py` 负责组装所有脑区，脑区之间不直接 import。

新增模块必须先判断：属于哪个脑区？还是应该新开一个脑区？不确定时先放进已有脑区，命名空间够区分再独立。

### 2. 最少代码量

每个模块：

- 只做职责范围内的事，一行不多
- 能复用的不重写（查现有代码，不重复造轮子）
- 3 行能解决的不写 30 行
- 不引入不必要的抽象层

新增功能优先「就地扩展」到现有文件，代码复用超过 2 次才提取公共函数。

**不引入运行时框架，但保持代码可抽性**：v0.5.0 起按 `meowcat/` + `meowagent/` 双层物理分离，
详见 **P-03 MeowCat 可抽性纪律**。这不是引入框架，是让「按猫的构造切模块」的边界物理化。

### 3. 最高完成度

写完不是终点：

- 所有路径都要处理（正常、异常、边界）
- 错误不吞，日志不省
- 写完跑 `python -c "import meowagent"` 确认没炸 import

### 4. 忠于闭环

项目核心就三个闭环：

- **闭环A 记找给**：每轮对话 Hippocampus 记 → Thalamus 找 → BrainStem 给
- **闭环B 编排**：TaskOrchestrator 拆任务 → Kitten 分身执行 → 回收
- **闭环C 生长**：AnomalyGrowth / CorrectionGrowth → Crystallizer 结晶

任何新功能必须接进这三个闭环之一，不建孤岛。

### 5. 改核心必补测试

改 hippocampus / thalamus / brainstem / cerebrum / colony 等核心模块，必须同步补或改对应 `tests/test_v0*.py`。改了逻辑没补测试 = 没做完。

## 开发检查

```
□ 先读了架构文档吗？（docs/架构/00~03）
□ 这个改动属于哪个脑区？
□ 有没有破坏 Cat 是唯⼀组装点的约定？
□ 新代码能不能用更少的行数实现？
□ 错误路径都处理了吗？
□ 它接进了哪个闭环？（A/B/C）
□ import 环了吗？（脑区之间不能直接 import）
□ 核心模块改动补测试了吗？
□ [v0.5.0+] meowcat/ 有没有 import meowagent/？（必须无）
□ [v0.5.0+] 新增内容放对目录了吗？（参照 P-03 进/不进表）
```
