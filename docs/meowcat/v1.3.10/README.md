# meowcat v1.3.10 — CI/Release 修复

> 发布日期: 2026-05-09 | 上一版本: [v1.3.9](../v1.3.9/)

## 一句话

Bug 修复版本 — 解决 CI lint mypy `import-not-found` 错误 + Release workflow 重构为手动触发、独立 job。

## 做了什么

### CI 修复

- `_test.yml` lint job 安装 `pip install -e ".[plus,tui]"` 解决 `textual`/`playwright` mypy 模块找不到

### Release 重构

- 触发方式: `push: tags` → `workflow_dispatch`（手动发包）
- `github-release` job 自动从 pyproject.toml 读取版本创建 tag
- `pypi` 和 `github-release` 拆为独立 job（仅依赖 call-test），互不阻断

## 质量门

- ruff: zero errors
- mypy: zero errors (154 source files)
- pytest: 2007 passed

## 子任务进度

| 子任务 | 状态 | 描述 |
| ------ | ---- | ---- |
| T-01   | ✅   | CI lint 安装可选依赖 |
| T-02   | ✅   | Release 改 workflow_dispatch |
| T-03   | ✅   | github-release 自动创建 tag |
| T-04   | ✅   | pypi/github-release 拆为独立 job |
| T-05   | ✅   | 文档更新 + release v1.3.10 |
