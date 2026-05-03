# v1.0.5 审查记录

## 关键决策

### ADR: Diagnosable/OrganProtocol 移入 protocols_brain.py

**问题**: `GrowthProtocol` 继承 `OrganProtocol`，若 `OrganProtocol` 留在 `protocols.py` 会形成循环导入（`protocols.py` → `protocols_brain.py` → `protocols.py`）。

**决策**: 将 `Diagnosable` 和 `OrganProtocol` 移入 `protocols_brain.py`。`protocols.py` 通过 re-export 保持兼容。

**替代方案**: 拆分出独立的 `protocols_base.py` — 被否决，仅 2 个基础 Protocol 不值得额外文件。

### ADR: HippocampusProtocol 类型标注简化

**问题**: 原始文件中使用了 `# type: ignore[name-defined] # noqa: F821` 标注（如 `entities: dict[str, EntityShape]`），这些 import 在 TYPE_CHECKING 块中。

**处理**: 在 `protocols_brain.py` 中将 TYPE_CHECKING import 简化为 `LocateResultShape`（仅 `ThalamusProtocol` 显式使用），其余使用 `Any` 替代避免类型检查噪音。功能等价。

## 遇到的问题

无。

## 统计

| 指标       | 值                          |
| ---------- | --------------------------- |
| 新增文件   | 3                           |
| 删除行     | ~390 (从 protocols.py 移出) |
| 新增行     | ~470 (3 个新文件)           |
| 净增行     | ~80 (文件头/import 重复)    |
| 测试       | 567 passed                  |
| 破坏性变更 | 无                          |
