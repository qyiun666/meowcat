# v1.3.10 任务拆解

## T-01 — CI lint 安装可选依赖

**文件**: `.github/workflows/_test.yml`

lint job `pip install mypy ruff` → `pip install -e ".[plus,tui]" mypy ruff`

## T-02 — Release 改 workflow_dispatch

**文件**: `.github/workflows/release.yml`

`on: push: tags: ["v*"]` → `on: workflow_dispatch`

## T-03 — github-release 自动创建 tag

**文件**: `.github/workflows/release.yml`

新增 step: 从 pyproject.toml 读取 version，`git tag v{version}` + push

## T-04 — pypi/github-release 拆独立 job

**文件**: `.github/workflows/release.yml`

`github-release` 的 `needs: [pypi]` → `needs: [call-test]`

## T-05 — 文档更新 + release

**文件**: CHANGELOG.md, docs/meowcat/v1.3.10/
