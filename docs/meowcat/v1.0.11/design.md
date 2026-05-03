# v1.0.11 设计文档 — synthesize Path（世界观综合）

> 来源: `.qoder/plans/meowcat-v1.0.10-roadmap.md` v1.0.11 章节
> 架构参考: `docs/架构/00-meowcat-框架架构.md`

---

## 1. 设计目标

为 meowcat 框架新增一条原子路径 `synthesize`：**脑干 (BRAINSTEM) → 皮层 (CORTEX)**，调用 `CortexProtocol.synthesize()` 方法，实现"世界观综合"能力。

---

## 2. 背景

三层前置条件早已就位，唯缺一行 Path：

| 前置条件                      | 位置                                               | 状态      |
| ----------------------------- | -------------------------------------------------- | --------- |
| `CortexProtocol.synthesize()` | `protocols_brain.py:260`                           | ✅ 已定义 |
| `BRAINSTEM → CORTEX` 边       | `biology.py:177` CORTEX 的 `in_edges` 含 BRAINSTEM | ✅ 已存在 |
| `CORTEX` 坐标                 | `anatomy.py`                                       | ✅ 已存在 |

---

## 3. 改动

### 3.1 `meowcat/path.py`

**导入新增**：`CORTEX` 加入 anatomy import 列表。

**BUILTIN_PATHS 新增一行**：

```python
# ── 综合域 ──
Path("synthesize",         BRAINSTEM,   CORTEX,
     "synthesize",          "read",  "世界观综合"),
```

### 3.2 设计说明

- **from=BRAINSTEM**：脑干作为总调度中枢，下令执行综合
- **to=CORTEX**：皮层作为四层世界观存储器，响应 `synthesize()` 调用
- **method=synthesize**：对应 `CortexProtocol.synthesize(max_tokens=400) -> str`
- **mode=read**：只读操作，不修改皮层数据
- **零协议改动**：`CortexProtocol.synthesize()` 无需修改
- **零器官改动**：CORTEX 的 in_edges 已含 BRAINSTEM

### 3.3 框架语义

框架不关心 `synthesize()` 的内部实现 — 可以是 LLM 摘要、规则聚类、纯统计。框架只管"脑干下令 → 皮层执行"这条神经通路。

---

## 4. 改动范围

| 文件              | 改动                                    | 行数 |
| ----------------- | --------------------------------------- | ---- |
| `meowcat/path.py` | import 加 CORTEX + BUILTIN_PATHS 加一行 | +3   |

**零修改**（不改任何其他文件）。

---

## 5. 测试策略 (~5 个)

| 测试                                 | 覆盖                                 |
| ------------------------------------ | ------------------------------------ |
| synthesize path 存在于 BUILTIN_PATHS | 路径注册                             |
| synthesize 路径属性正确              | name/from_organ/to_organ/method/mode |
| BUILTIN_PATHS 无重名                 | 包含 synthesize 后的去重校验         |
| PathRegistry.run("synthesize")       | 执行路径等价于 cat.signal            |
| pathways 向后兼容                    | 旧 API 无影响                        |
