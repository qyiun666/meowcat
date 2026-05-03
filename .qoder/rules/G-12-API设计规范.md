---
trigger: model_decision
description: API 设计规范，包括 RESTful 设计、版本控制、请求响应格式、查询参数、认证授权、错误处理、文档化、幂等性、CORS、性能优化。当设计或修改 API 接口时使用此规则。
---

# G-12: API 设计规范

## 1. RESTful 设计原则

### 1.1 基本规则

- 使用 HTTP 方法表示操作（GET/POST/PUT/PATCH/DELETE）
- 资源使用名词，不使用动词
- 集合使用复数形式
- URL 应该是层次化的，反映资源关系
- 统一返回 HTTP 200，通过业务码区分成功/失败

### 1.2 示例

```
正确：
  GET    /api/v1/users              # 获取用户列表
  GET    /api/v1/users/:id          # 获取单个用户
  POST   /api/v1/users              # 创建用户
  PUT    /api/v1/users/:id          # 完整更新用户
  PATCH  /api/v1/users/:id          # 部分更新用户
  DELETE /api/v1/users/:id          # 删除用户
  GET    /api/v1/users/:id/orders   # 获取用户的订单

错误：
  GET  /api/getUsers
  POST /api/createUser
  GET  /api/user/:id
  POST /api/users/delete/:id
```

## 2. API 版本控制

### 2.1 规则

- 在 URL 中包含版本号（`/v1/`、`/v2/`）
- 版本号使用整数，不使用小数
- 主要版本变更时增加版本号
- 保持旧版本向后兼容一段时间
- 提前通知废弃计划

### 2.2 示例

```
正确：
  /api/v1/users
  /api/v2/users

错误：
  /api/users
  /api/v1.2/users
  /api/2023-11-10/users
```

## 3. 请求与响应格式

### 3.1 基本规则

- 使用 JSON 作为默认格式
- 请求使用 `Content-Type: application/json`
- 响应统一结构：`{ code, message, data }`
- 时间使用 ISO 8601 格式
- JSON 字段使用 snake_case
- 分页使用统一参数（page, page_size）

### 3.2 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 123,
    "name": "John Doe",
    "email": "john@example.com",
    "create_time": "2025-11-10T10:30:00Z"
  }
}
```

### 3.3 错误响应

```json
{
  "code": 1001,
  "message": "邮箱格式无效"
}
```

### 3.4 分页响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "list": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

## 4. 业务码与 HTTP 状态码

### 4.1 设计原则

所有 API 统一返回 HTTP 200，通过 JSON 中的 `code` 字段区分业务结果。错误码体系详见 G-10。

### 4.2 错误码区间

| 区间      | 分类          |
| --------- | ------------- |
| 0         | 成功          |
| 1001-1999 | 参数错误      |
| 2001-2999 | 认证/授权错误 |
| 3001-3999 | 资源错误      |
| 4001-4999 | 业务错误      |
| 5001-5999 | 系统错误      |
| 9001-9999 | 第三方错误    |

### 4.3 示例

```go
// Go - 创建资源
func CreateUser(c *gin.Context) {
    var req CreateUserRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(200, Response{
            Code:    1001,
            Message: "参数校验失败",
        })
        return
    }

    user, err := userService.Create(req)
    if err != nil {
        var appErr *AppError
        if errors.As(err, &appErr) {
            c.JSON(200, Response{Code: appErr.Code, Message: appErr.Message})
            return
        }
        c.JSON(200, Response{Code: 5001, Message: "系统繁忙，请稍后重试"})
        return
    }

    c.JSON(200, Response{Code: 0, Message: "success", Data: user})
}

// Go - 删除资源
func DeleteUser(c *gin.Context) {
    id := c.Param("id")
    if err := userService.Delete(id); err != nil {
        if errors.Is(err, ErrNotFound) {
            c.JSON(200, Response{Code: 3001, Message: "用户不存在"})
            return
        }
        c.JSON(200, Response{Code: 5001, Message: "系统繁忙，请稍后重试"})
        return
    }

    c.JSON(200, Response{Code: 0, Message: "success"})
}
```

## 5. 查询参数规范

### 5.1 参数命名

| 用途     | 参数            | 示例                              |
| -------- | --------------- | --------------------------------- |
| 分页     | page, page_size | `?page=1&page_size=20`            |
| 排序     | sort_by, order  | `?sort_by=create_time&order=desc` |
| 过滤     | 字段名          | `?status=1&user_id=123`           |
| 搜索     | q 或 search     | `?q=john`                         |
| 字段选择 | fields          | `?fields=id,name,email`           |
| 关联资源 | include         | `?include=orders,profile`         |
| 范围查询 | 字段名[操作符]  | `?create_time[gte]=2025-01-01`    |

### 5.2 示例

```
GET /api/v1/users?page=1&page_size=20
GET /api/v1/users?sort_by=create_time&order=desc
GET /api/v1/users?status=1&role=admin
GET /api/v1/users?q=john
GET /api/v1/users?fields=id,name,email
GET /api/v1/users?include=orders,profile
GET /api/v1/users?create_time[gte]=2025-01-01&create_time[lte]=2025-12-31
```

## 6. 认证与授权

### 6.1 规则

- 使用 JWT 或 OAuth 2.0 认证
- API 密钥用于服务间调用
- 敏感操作需要额外验证（MFA）
- 使用 HTTPS 传输
- 实施速率限制

### 6.2 JWT 认证中间件示例

```go
func Authenticate() gin.HandlerFunc {
    return func(c *gin.Context) {
        token := c.GetHeader("Authorization")
        if token == "" {
            c.JSON(200, Response{Code: 2001, Message: "缺少认证令牌"})
            c.Abort()
            return
        }

        token = strings.TrimPrefix(token, "Bearer ")
        claims, err := jwt.ParseToken(token, config.JWTSecret)
        if err != nil {
            c.JSON(200, Response{Code: 2002, Message: "令牌无效或已过期"})
            c.Abort()
            return
        }

        c.Set("user", claims)
        c.Next()
    }
}
```

## 7. 错误处理标准

### 7.1 统一响应结构

```go
type Response struct {
    Code    int    `json:"code"`
    Message string `json:"message"`
    Data    any    `json:"data,omitempty"`
}
```

### 7.2 规则

- 使用 4 位数字错误码（详见 G-10）
- 提供清晰的用户友好消息
- 生产环境不暴露堆栈跟踪
- 详细错误仅记录到服务端日志

## 8. API 文档化

### 8.1 规则

- 使用 OpenAPI/Swagger 规范
- 文档包含所有端点、参数、响应
- 提供请求示例和响应示例
- 文档与代码同步更新
- 提供交互式 API 测试界面

### 8.2 示例

使用 OpenAPI 3.0 规范，文档包含所有端点、参数、响应示例：

```yaml
openapi: 3.0.0
paths:
  /api/v1/users:
    get:
      summary: Get user list
      parameters:
        - { name: page, in: query, schema: { type: integer, default: 1 } }
        - { name: page_size, in: query, schema: { type: integer, default: 20 } }
      responses:
        "200":
          description: Success (code=0 表示成功，其他为业务错误码)
```

## 9. 幂等性设计

### 9.1 规则

- GET, PUT, DELETE 操作应该是幂等的
- POST 使用幂等键避免重复创建
- 使用乐观锁处理并发更新
- 提供操作去重机制

### 9.2 幂等键处理

```go
func CreateOrder(c *gin.Context) {
    idempotencyKey := c.GetHeader("Idempotency-Key")

    if idempotencyKey != "" {
        existing, err := cache.Get(idempotencyKey)
        if err == nil && existing != nil {
            c.JSON(200, existing)
            return
        }
    }

    order, err := orderService.Create(req)
    if err != nil {
        c.JSON(200, Response{Code: 4001, Message: "创建订单失败"})
        return
    }

    resp := Response{Code: 0, Message: "success", Data: order}
    if idempotencyKey != "" {
        cache.Set(idempotencyKey, resp, 3600)
    }

    c.JSON(200, resp)
}
```

### 9.3 乐观锁

```go
func UpdateUser(c *gin.Context) {
    id := c.Param("id")
    var req UpdateUserRequest
    c.ShouldBindJSON(&req)

    user, err := userService.Get(id)
    if err != nil {
        c.JSON(200, Response{Code: 3001, Message: "用户不存在"})
        return
    }

    if user.Version != req.Version {
        c.JSON(200, Response{Code: 3003, Message: "资源已被其他请求修改，请刷新后重试"})
        return
    }

    user.Version++
    userService.Update(user)
    c.JSON(200, Response{Code: 0, Message: "success", Data: user})
}
```

## 10. CORS 配置

### 10.1 规则

- 配置允许的域名白名单
- 设置允许的 HTTP 方法
- 配置允许的请求头
- 启用凭证支持（如需要）

### 10.2 示例

```go
import "github.com/gin-contrib/cors"

func SetupCORS() gin.HandlerFunc {
    config := cors.DefaultConfig()
    config.AllowOrigins = []string{
        "https://example.com",
        "https://app.example.com",
    }
    config.AllowMethods = []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
    config.AllowHeaders = []string{"Content-Type", "Authorization", "X-Request-ID", "Idempotency-Key"}
    config.ExposeHeaders = []string{"X-Total-Count", "X-Page-Count"}
    config.AllowCredentials = true
    config.MaxAge = 24 * time.Hour

    return cors.New(config)
}
```

## 11. 性能优化

### 11.1 规则

- 实施响应缓存（ETag, Cache-Control）
- 支持字段过滤减少传输数据
- 使用分页避免大数据集
- 实施压缩（gzip）
- 提供批量端点减少请求次数

### 11.2 ETag 缓存

```go
func GetUser(c *gin.Context) {
    user, err := userService.Get(c.Param("id"))
    if err != nil {
        c.JSON(200, Response{Code: 3001, Message: "用户不存在"})
        return
    }

    etag := generateETag(user)

    if c.GetHeader("If-None-Match") == etag {
        c.Status(304)
        return
    }

    c.Header("ETag", etag)
    c.Header("Cache-Control", "max-age=300")
    c.JSON(200, Response{Code: 0, Message: "success", Data: user})
}
```

### 11.3 字段过滤

```go
func ListUsers(c *gin.Context) {
    fields := c.Query("fields")
    var selectFields []string
    if fields != "" {
        selectFields = strings.Split(fields, ",")
    }

    users, err := userService.List(selectFields)
    if err != nil {
        c.JSON(200, Response{Code: 5002, Message: "查询失败"})
        return
    }

    c.JSON(200, Response{Code: 0, Message: "success", Data: users})
}
```

### 11.4 压缩

```go
import "github.com/gin-contrib/gzip"

// 启用 gzip 压缩
r.Use(gzip.Gzip(gzip.DefaultCompression))
```
