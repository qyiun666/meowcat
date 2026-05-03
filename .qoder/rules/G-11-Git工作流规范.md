---
trigger: model_decision
description: Git工作流规范，分支策略、提交规范、代码审查、版本发布。当进行Git操作时使用此规则。
---

# G-11: Git 工作流规范

## 分支策略

### 分支类型

```
main        - 生产分支，永远可部署
develop     - 开发分支，集成测试通过
feature/*   - 功能分支，从 develop 创建
hotfix/*    - 紧急修复，从 main 创建
release/*   - 发布分支，从 develop 创建
```

### 分支流程

```
main
  ↑
  |  hotfix/*  ----→  紧急修复
  |
develop
  ↑
  |  feature/*  --->  功能开发
  |
  +-- feature/user-auth
  +-- feature/campaign-stats
```

## 提交规范

### 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

| 类型     | 说明                   |
| -------- | ---------------------- |
| feat     | 新功能                 |
| fix      | 修复 bug               |
| docs     | 文档更新               |
| style    | 代码格式（不影响功能） |
| refactor | 重构                   |
| perf     | 性能优化               |
| test     | 测试相关               |
| chore    | 构建/工具/依赖更新     |

### 示例

```
feat(user): 添加用户登录功能

- 实现 JWT 认证
- 添加登录/登出接口
- 添加密码加密

Closes #123
```

```
fix(campaign): 修复广告计划状态更新失败

问题：状态变更时未检查权限
解决：添加权限校验

Fixes #456
```

### 提交原子性

- 一个提交只做一件事
- 提交应该是可编译/可运行的
- 避免"半成品"提交

## 工作流

### 功能开发

```bash
# 1. 从 develop 创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/user-auth

# 2. 开发并提交
git add .
git commit -m "feat(auth): 添加登录接口"

# 3. 推送到远程
git push origin feature/user-auth

# 4. 创建 PR 合并到 develop
# 5. 删除功能分支
git branch -d feature/user-auth
```

### 紧急修复

```bash
# 1. 从 main 创建热修复分支
git checkout main
git pull origin main
git checkout -b hotfix/fix-login-bug

# 2. 修复并提交
git commit -m "fix(auth): 修复登录失败问题"

# 3. 合并到 main 和 develop
git checkout main
git merge hotfix/fix-login-bug
git push origin main

git checkout develop
git merge hotfix/fix-login-bug
git push origin develop

# 4. 打标签
git tag -a v1.0.1 -m "修复登录问题"
git push origin v1.0.1
```

## 代码审查

### PR 规范

```markdown
## 描述

简要说明改动内容

## 改动类型

- [ ] 新功能
- [ ] Bug 修复
- [ ] 重构
- [ ] 文档更新

## 检查清单

- [ ] 代码能编译/通过类型检查
- [ ] 添加了必要的测试
- [ ] 更新了相关文档
- [ ] 自我审查通过

## 关联 Issue

Fixes #123
```

### 审查检查清单

```
□ 代码逻辑正确
□ 命名规范
□ 错误处理完善
□ 无安全漏洞
□ 有必要的注释
□ 测试覆盖
□ 无调试代码（console.log/print）
```

## 版本发布

### 版本号规范（SemVer）

```
主版本号.次版本号.修订号

1.0.0  - 重大更新，不兼容
1.1.0  - 新功能，兼容
1.1.1  - Bug 修复
```

### 发布流程

```bash
# 1. 创建发布分支
git checkout develop
git checkout -b release/v1.1.0

# 2. 版本更新（修改版本号等）
git commit -m "chore(release): 准备 v1.1.0"

# 3. 合并到 main
git checkout main
git merge release/v1.1.0

# 4. 打标签
git tag -a v1.1.0 -m "发布 v1.1.0"
git push origin v1.1.0

# 5. 合并回 develop
git checkout develop
git merge release/v1.1.0
```

## 最佳实践

### Do

- 频繁提交，小步快跑
- 写清晰的提交信息
- 在功能分支开发
- 合并前更新到最新代码
- 删除已合并的分支

### Don't

- 直接在 main 开发
- 提交敏感信息（密码、密钥）
- 提交大文件
- 提交依赖目录（node_modules/）
- 使用 `git push -f`
