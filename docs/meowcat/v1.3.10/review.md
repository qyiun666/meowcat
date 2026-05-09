# v1.3.10 审查记录

## 问题与决策

| # | 问题 | 决策 |
|---|------|------|
| 1 | CI lint job mypy `import-not-found` on `textual`/`playwright` | lint job 安装 `-e ".[plus,tui]"` 而非仅 mypy+ruff |
| 2 | `workflow_dispatch` 无关联 tag，`github-release` 失败 | 新增 step 自动从 pyproject.toml 读版本创建 tag |
| 3 | pypi 版本冲突导致 github-release 被阻断 | 拆为独立 job，仅依赖 call-test |

## 关键决策

- **手动发包**：Release 不再自动随 tag 触发，由开发者通过 `gh workflow run` 手动启动
- **job 解耦**：pypi 和 github-release 各自独立，单点失败不影响另一方
