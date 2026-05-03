# v1.0.6 审查记录

## 关键决策

### ADR: 不引入 `importlib.metadata` 替代文件读取

**问题**: 当前 `__init__.py` 通过 `pathlib.Path` 读取 `pyproject.toml` 获取
版本号，`importlib.metadata.version("meowcat")` 是更标准的做法。

**决策**: 保持文件读取方式。原因：`importlib.metadata` 在 editable install
（`pip install -e .`）下行为不一致，而文件读取在开发和生产环境均可靠。

### 发现: v1.0.5 未在 meowcat 独立仓库测试

**问题**: v1.0.5 的 CI 只跑在父仓库的 `meowcat/` 被 `.gitignore` ignore 前，
独立仓库 `qyiun666/meowcat` 没有 CI 触发，导致路径 bug 未被发现。

**措施**: 独立仓库已有 `.github/workflows/`，后续 push tag 会触发 CI。

## 统计

| 指标       | 值         |
| ---------- | ---------- |
| 修改文件   | 2          |
| 变更行     | 2          |
| 测试       | 567 passed |
| 破坏性变更 | 无         |
