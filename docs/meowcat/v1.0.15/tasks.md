# v1.0.15 任务清单 — 长流程 Long-Running Workflow

> 创建日期: 2026-05-03 | 基版本: v1.0.14

---

## 任务拆解

- [x] 1. `models.py` 新增 WorkflowShape 数据模型
- [x] 2. `protocols_brain.py` HippocampusProtocol 新增 list_active_workflows()
- [x] 3. `path.py` BUILTIN_PATHS 新增 3 条编排域路径
- [x] 4. `chain.py` BUILTIN_CHAINS 新增 workflow_chain
- [x] 5. `assembly.py` CatBase.**init** 新增 \_active_workflows 字典
- [x] 6. `assembly.py` CatBase 新增 register_workflow() / active_workflows() 公开方法
- [x] 7. `assembly.py` CatBase 新增 \_resume_workflows() / \_checkpoint_workflows() 私有方法
- [x] 8. `assembly.py` 修改 start() — emit 前扫描并加载未完成 Workflow
- [x] 9. `assembly.py` 修改 shutdown() — hooks 前存档所有活跃 Workflow
- [x] 10. `__init__.py` 导出 WorkflowShape + WORKFLOW_CHAIN
- [x] 11. `defaults/organs.py` NoopHippocampus 实现 list_active_workflows()
- [x] 12. 更新已有测试文件（协议 Dummy 类、数量断言）
- [x] 13. 创建 v1.0.15 文档（design / tasks / README）
- [x] 14. 编写新测试（31 个）
- [x] 15. 运行全部测试验证零回归 (676 passed, 0 failed)

---

## 验收清单

- [x] WorkflowShape 可从 `meowcat` 正确导入
- [x] WorkflowShape 默认值正确（status="active", current_step=0, plan=[], 等）
- [x] BUILTIN_PATHS 含 3 条编排域路径（workflow_create / workflow_checkpoint / workflow_resume）
- [x] BUILTIN_CHAINS 含 workflow_chain（6 条链路）
- [x] CatBase 构造后 \_active_workflows 为空字典
- [x] register_workflow(wf) 正确注册到 \_active_workflows
- [x] active_workflows() 只返回 status 为 active/awaiting_user 的
- [x] start() 前注册 workflow 到 Hippocampus → shutdown() → start() 后自动恢复
- [x] shutdown() 自动存档所有活跃 workflow（append_content 写入 checkpoint）
- [x] 无 Hippocampus 时 start()/shutdown() 不报错（静默跳过）
- [x] 无活跃 workflow 时 shutdown() 零开销
- [x] NoopHippocampus.list_active_workflows() 正确过滤 type/status/cat_id
- [x] NoopHippocampus.list_active_workflows() 空列表时返回 []
- [x] WORKFLOW_CHAIN 可从 `meowcat` 正确导入
- [x] workflow_chain path 序列正确：(workflow_create, execute_tool, workflow_checkpoint)
- [x] \_resume_workflows() 静默处理 Hippocampus 未挂载
- [x] \_checkpoint_workflows() 静默处理 Nervous 未启用
- [x] start() 先执行 \_resume_workflows()，再 emit lifecycle.start，再 hooks
- [x] shutdown() 先执行 \_checkpoint_workflows()，再 hooks，再 emit lifecycle.shutdown
- [x] 全部现有测试通过（零回归）
