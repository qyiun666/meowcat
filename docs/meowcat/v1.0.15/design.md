# v1.0.15 设计文档 — 长流程 Long-Running Workflow（编排持久化）

> 来源: `.qoder/plans/meowcat-v1.0.10-roadmap.md` v1.0.15 章节
> 架构参考: `docs/架构/00-meowcat-框架架构.md`

---

## 1. 设计目标

三个"长"是一个东西：猫接到任务 → 编排分身接力干活 → 跑 3 天不断 → 重启恢复状态 → 等用户授权后继续。

框架保证：**状态不丢，重启可续，内存不炸。**
框架不做：步骤拆解（LLM）、kitten 执行逻辑、触发策略。

## 2. 一次完整的长流程

```
用户: "帮我重构整个 auth 模块"
  │
  ▼
主猫: 拆解为 8 个步骤，创建 Workflow 实体
  │
  ├── Step 1: 分析现状              → spawn Kitten-A → 完成 ✓ → checkpoint
  ├── Step 2: 设计新接口             → spawn Kitten-B → 完成 ✓ → checkpoint
  ├── Step 3: 用户确认设计方案       → 💬 等待用户回复（暂停）
  │                                      │ 3 天后用户回复 "方案 OK"
  ├── Step 4: 迁移 User 模型        → spawn Kitten-C → 完成 ✓ → checkpoint
  ├── ...                                │ 猫进程重启
  │                                      │ cat.start() → 扫描未完成 Workflow
  ├── Step 5: 迁移 Session 逻辑     → spawn Kitten-D → 继续 ✓
  ├── ...
  └── Step 8: 全量测试              → spawn Kitten-H → 完成 ✓ → Workflow complete
```

## 3. 核心设计：三件事合一

| 能力                          | 如何实现                                                                                              |
| ----------------------------- | ----------------------------------------------------------------------------------------------------- |
| **长会话** — 重启后记得上下文 | Workflow 实体存 Hippocampus。cat.start() 扫出未完成 workflow → 自动加载 plan + 历史 checkpoint        |
| **长续航** — 3 天不爆内存     | 每个 Step 完成后压缩上一 Step 的 episode（decay 加强）。locate 时只拉当前 workflow 相关记忆，自动截断 |
| **长流程** — 跨会话任务不丢   | 每步自动写 checkpoint 到 Hippocampus 实体。断电/重启 → 读 checkpoint 继续                             |

## 4. 新增组件

### 4.1 WorkflowShape 数据模型 (`models.py`)

```python
class WorkflowShape(BaseModel):
    entity_id: str
    cat_id: str
    session_id: str
    status: str = "active"       # "active" | "awaiting_user" | "completed" | "failed"
    plan: list[str]              # 步骤描述列表
    current_step: int = 0        # 当前在第几步
    checkpoint: dict[str, Any]   # 当前步骤的断点数据
    kittens_spawned: list[str]   # 已 spawn 的 kitten 列表
    created_at: str
    updated_at: str
```

### 4.2 HippocampusProtocol 新增 (`protocols_brain.py`)

```python
def list_active_workflows(self, cat_id: str) -> list[dict[str, Any]]: ...
```

### 4.3 新增 Path + Chain

```python
# 编排域新路径 (path.py)
Path("workflow_create",     BRAINSTEM, HIPPOCAMPUS, "add_entity",    "write", "创建工作流"),
Path("workflow_checkpoint", BRAINSTEM, HIPPOCAMPUS, "append_content","write", "写检查点"),
Path("workflow_resume",     BRAINSTEM, HIPPOCAMPUS, "get_entity",    "read",  "恢复工作流"),

# 编排链 (chain.py)
Chain("workflow_chain", ("workflow_create", "execute_tool", "workflow_checkpoint"),
      "工作流单步 — 创建→执行→存档"),
```

全部复用已有 Hippocampus 方法，零新器官。

### 4.4 Cat 生命周期自动衔接 (`assembly.py`)

```python
class CatBase:
    async def start(self) -> None:
        # 1. 扫描 Hippocampus 中未完成的 Workflow → 加载到 _active_workflows
        # 2. 发射 lifecycle.start
        # 3. 依次调用 on_start hooks
        await self._resume_workflows()
        await self._events.emit(Lifecycle.START, {"cat": self})
        for hook in self._start_hooks:
            await hook(self)

    async def shutdown(self) -> None:
        # 1. 遍历所有 active workflow → 写 checkpoint
        # 2. 逆序调用 on_shutdown hooks
        # 3. 发射 lifecycle.shutdown
        await self._checkpoint_workflows()
        for hook in reversed(self._shutdown_hooks):
            await hook(self)
        await self._events.emit(Lifecycle.SHUTDOWN, {"cat": self})
```

### 4.5 公开 API

```python
# 注册工作流（应用层创建 WorkflowShape 后调用）
cat.register_workflow(wf_dict)

# 查询活跃工作流
cat.active_workflows()  # → list[dict]
```

### 4.6 Framework-guaranteed checkpoint

| 时机                     | 触发                              |
| ------------------------ | --------------------------------- |
| Kitten complete → absorb | 应用层自行存档                    |
| Kitten stuck → dismiss   | 应用层自行存档                    |
| Cat.shutdown()           | **框架自动存档**所有活跃 workflow |
| 用户回复触发 resume      | 应用层自行读档                    |

## 5. 框架不做什么

- 不决定如何拆解步骤（LLM 做的事，应用层）
- 不实现 kitten 的具体执行逻辑（应用层）
- 不提供 workflow 的触发策略（heartbeat 已够）
- **不自动 resume 执行** — `_resume_workflows()` 只加载状态，不触发执行（应用层决定何时继续）

## 6. 与已有机制的关系

| 概念            | 触发时机          | 用途                            |
| --------------- | ----------------- | ------------------------------- |
| Loop.trigger    | 某个 event 发生时 | 自动化执行回路（已有）          |
| Cat.on_start    | 猫启动时          | 初始化 Gateway、连接 DB         |
| Cat.on_shutdown | 猫关闭时          | 关闭 Gateway、**存档 Workflow** |
| Workflow        | 长任务进行中      | **跨会话持久化**编排状态        |

Workflow checkpoint 是 on_shutdown 之前自动执行的，确保状态在清理前保存完毕。

## 7. 设计原则

- **零开销关闭** — 无 Hippocampus 或无活跃 workflow 时 start()/shutdown() 行为完全不变
- **静默失败** — 扫描/存档异常不影响启动/关闭主流程
- **不改变事件签名** — Lifecycle.START / Lifecycle.SHUTDOWN 不变
- **不污染器官体系** — Workflow 是纯数据模型 + 现有 Hippocampus 方法复用
- **复用 > 新建** — 全部复用已有 Path/Chain 机制和 Hippocampus CRUD

## 8. 改动范围

| 文件                                  | 改动                                                                               | 行数 |
| ------------------------------------- | ---------------------------------------------------------------------------------- | ---- |
| `meowcat/models.py`                   | WorkflowShape 数据模型                                                             | +14  |
| `meowcat/protocols_brain.py`          | HippocampusProtocol.list_active_workflows()                                        | +3   |
| `meowcat/path.py`                     | 3 条编排域 Path                                                                    | +7   |
| `meowcat/chain.py`                    | WORKFLOW_CHAIN                                                                     | +6   |
| `meowcat/assembly.py`                 | \_active_workflows + register/active + \_resume/\_checkpoint + start/shutdown 集成 | +64  |
| `meowcat/__init__.py`                 | 导出 WorkflowShape + WORKFLOW_CHAIN                                                | +4   |
| `meowcat/defaults/organs.py`          | NoopHippocampus.list_active_workflows()                                            | +18  |
| `tests/test_v051_protocol_checked.py` | Dummy 类补齐 list_active_workflows                                                 | +2   |
| `tests/test_v528a_chain.py`           | 数量断言更新                                                                       | +3   |
| `tests/test_v528b_loop.py`            | 路径数量更新                                                                       | +3   |
| **合计**                              |                                                                                    | ~124 |
