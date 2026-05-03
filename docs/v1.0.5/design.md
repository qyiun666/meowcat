# v1.0.5 设计

## 背景

来自 v1.0.0 review.md 未解决问题：`protocols.py`（622 行）超出 500 行限制。

## 拆分决策

### 按类别拆分

```
protocols.py (622)
    ↓
protocols.py (229)        — StageProtocol, KittenProtocol, CatProtocol, OrchestratorProtocol, SettingsProtocol, AdapterProtocol
protocols_brain.py (288)  — Diagnosable, OrganProtocol, 脑区协议, LLMProviderProtocol, GrowthProtocol
protocols_sense.py (92)   — EarsProtocol, EyesProtocol, WhiskersProtocol, PawsProtocol
protocols_storage.py (83) — GraphStorageProtocol, L6StorageProtocol, VectorStorageProtocol, SharedStorageProtocol
```

### 循环导入处理

- `GrowthProtocol` 继承 `OrganProtocol` → `Diagnosable` 和 `OrganProtocol` 移入 `protocols_brain.py`
- `protocols.py` 从 `protocols_brain.py` re-export 基础协议
- 无循环导入

### 兼容性策略

- `protocols.py` 通过 `from meowcat.protocols_xxx import ...` re-export 所有协议
- `__all__` 保持不变，25 个 Protocol 名称完全不变
- `from meowcat import XProtocol` 和 `from meowcat.protocols import XProtocol` 均不变
