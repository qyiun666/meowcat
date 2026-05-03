# v1.0.11 任务清单 — synthesize Path

> 创建日期: 2026-05-03 | 基版本: v1.0.10

---

## 任务拆解

- [x] 1. `path.py` 导入 CORTEX + BUILTIN_PATHS 新增 synthesize Path
- [x] 2. 创建 v1.0.11 文档（design / tasks / README / review）
- [x] 3. 编写测试（~5 个）
- [x] 4. 运行测试验证
- [x] 5. 更新路线图标记 v1.0.11 完成

---

## 验收清单

- [x] `synthesize` 路径存在于 BUILTIN_PATHS
- [x] 路径属性: from=BRAINSTEM, to=CORTEX, method=synthesize, mode=read
- [x] BUILTIN_PATHS 无重名（22+1=23 条路径全部唯一）
- [x] 全部现有测试通过（零回归）
- [x] 新测试通过
- [x] `meowcat/path.py` 零新增依赖
