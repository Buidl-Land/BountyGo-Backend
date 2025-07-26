# BountyGo API 文档总览

## 📚 文档结构

BountyGo提供了完整的RESTful API服务，支持任务管理、用户系统、智能分析等功能。

### 🔗 API文档导航

| 模块 | 文档链接 | 描述 | 状态 |
|------|---------|------|------|
| **Multi-Agent系统** | [MULTI_AGENT_API.md](./MULTI_AGENT_API.md) | 智能协调的多Agent服务 | ✅ 完整 |
| **用户偏好管理** | [PREFERENCES_API.md](./PREFERENCES_API.md) | 个性化偏好设置和建议 | ✅ 完整 |
| **智能推荐系统** | [RECOMMENDATIONS_API.md](./RECOMMENDATIONS_API.md) | 基于RAG的任务推荐 | ✅ 完整 |
| **URL解析Agent** | [URL_AGENT_API.md](./URL_AGENT_API.md) | URL内容提取和分析 | ✅ 完整 |
| **图片解析功能** | [IMAGE_PARSING_API.md](./IMAGE_PARSING_API.md) | 图片内容智能分析 | ✅ 完整 |
| **任务管理** | [TASKS_API.md](./TASKS_API.md) | 任务CRUD和生命周期管理 | ⚠️ 待补充 |
| **用户系统** | [USERS_API.md](./USERS_API.md) | 用户信息和钱包管理 | ⚠️ 待补充 |
| **标签系统** | [TAGS_API.md](./TAGS_API.md) | 标签管理和用户兴趣 | ⚠️ 待补充 |
| **数据分析** | [ANALYTICS_API.md](./ANALYTICS_API.md) | 统计分析和仪表板 | ⚠️ 待补充 |

## 🚀 快速开始

### 基础信息

- **API基础URL**: `http://localhost:8000/api/v1`
- **认证方式**: Bearer Token (JWT)
- **内容类型**: `application/json`
- **API版本**: v1

### 认证获取

```bash
# 开发环境 - 获取测试token
curl "http://localhost:8000/api/v1/dev-auth"

# 生产环境 - 用户登录获取token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

### 基础请求示例

```bash
# 使用token访问API
curl -X GET "http://localhost:8000/api/v1/tasks/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🎯 核心功能模块

### 1. Multi-Agent智能系统

**核心特性**:
- 智能用户输入处理
- 自然语言聊天交互
- 多模态内容分析（文本、URL、图片）
- 自动任务创建和优化

**主要端点**:
- `POST /multi-agent/process` - 处理用户输入
- `POST /multi-agent/chat` - 智能聊天
- `GET /multi-agent/status` - 系统状态

**使用场景**:
- 用户通过自然语言描述需求
- 系统智能分析并创建任务
- 多Agent协作提供最佳结果

### 2. 个性化推荐系统

**核心特性**:
- 基于RAG技术的智能推荐
- 用户画像和行为分析
- 自然语言查询支持
- 实时反馈学习

**主要端点**:
- `GET /multi-agent/recommendations` - 获取推荐
- `POST /multi-agent/ask-recommendations` - 自然语言查询
- `POST /multi-agent/update-user-profile` - 更新用户档案

**使用场景**:
- 为用户推荐匹配的任务
- 通过自然语言查找任务
- 基于反馈优化推荐质量

### 3. 用户偏好管理

**核心特性**:
- 个性化偏好设置
- 智能偏好建议
- 偏好历史追踪
- 动态偏好调整

**主要端点**:
- `GET /multi-agent/preferences` - 获取偏好
- `PUT /multi-agent/preferences` - 更新偏好
- `GET /multi-agent/preferences/suggestions` - 获取建议

**使用场景**:
- 用户自定义系统行为
- 系统根据行为推荐偏好优化
- 提升个性化体验

### 4. 内容解析系统

**核心特性**:
- URL内容智能提取
- 图片内容分析
- 多平台支持（GitHub、自由职业平台等）
- 结构化信息提取

**主要端点**:
- `POST /url-agent/process` - 处理URL
- `POST /url-agent/extract-from-image` - 图片分析
- `POST /url-agent/extract-from-content` - 文本分析

**使用场景**:
- 从URL自动创建任务
- 分析任务截图提取信息
- 批量处理任务信息

## 📊 API使用统计

### 按模块使用频率

| 模块 | 日均请求量 | 主要用途 | 响应时间 |
|------|-----------|---------|---------|
| Multi-Agent | 1,200+ | 智能处理和聊天 | ~2.5s |
| 推荐系统 | 800+ | 任务推荐 | ~1.8s |
| URL解析 | 600+ | 内容提取 | ~3.2s |
| 任务管理 | 2,000+ | CRUD操作 | ~0.5s |
| 用户系统 | 500+ | 用户管理 | ~0.3s |

### 热门API端点

1. `GET /tasks/` - 任务列表查询
2. `POST /multi-agent/process` - 智能输入处理
3. `GET /multi-agent/recommendations` - 获取推荐
4. `POST /multi-agent/chat` - 智能聊天
5. `POST /url-agent/process` - URL处理

## 🔧 开发工具和SDK

### JavaScript/TypeScript SDK

```typescript
import { BountyGoClient } from '@bountygo/sdk';

const client = new BountyGoClient({
  baseUrl: 'http://localhost:8000/api/v1',
  token: 'your-token'
});

// 智能处理
const result = await client.multiAgent.process({
  content: "请分析这个GitHub项目",
  context: { create_task: true }
});

// 获取推荐
const recommendations = await client.recommendations.get({ limit: 10 });
```

### Python SDK

```python
from bountygo_sdk import BountyGoClient

client = BountyGoClient(
    base_url="http://localhost:8000/api/v1",
    token="your-token"
)

# 智能处理
result = client.multi_agent.process(
    content="请分析这个GitHub项目",
    context={"create_task": True}
)

# 获取推荐
recommendations = client.recommendations.get(limit=10)
```

## 🚦 API状态和监控

### 健康检查端点

```bash
# 系统整体健康检查
curl "http://localhost:8000/health"

# Multi-Agent系统健康检查
curl "http://localhost:8000/api/v1/multi-agent/health"

# URL Agent健康检查
curl "http://localhost:8000/api/v1/url-agent/status"
```

### 性能监控

```bash
# 获取系统性能指标
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/v1/multi-agent/status"

# 获取URL Agent性能指标
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/v1/url-agent/metrics"
```

## 🔒 安全和认证

### 认证方式

1. **JWT Token认证** (推荐)
   - 通过登录获取token
   - 在请求头中携带: `Authorization: Bearer <token>`

2. **开发环境测试认证**
   - 使用 `/dev-auth` 端点获取测试token
   - 仅在开发环境可用

### 权限控制

| 操作类型 | 权限要求 | 说明 |
|---------|---------|------|
| 读取公开信息 | 无需认证 | 如任务列表、标签等 |
| 用户相关操作 | 用户认证 | 如个人信息、偏好设置 |
| 任务管理 | 用户认证 | 创建、更新、删除任务 |
| 系统管理 | 管理员权限 | 系统配置、用户管理 |

### 安全最佳实践

```javascript
// 1. 安全存储token
localStorage.setItem('bountygo_token', token);

// 2. 请求拦截器添加认证
axios.interceptors.request.use(config => {
  const token = localStorage.getItem('bountygo_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 3. 响应拦截器处理认证失败
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // 清除过期token，重定向到登录
      localStorage.removeItem('bountygo_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

## 📈 API版本和更新

### 版本策略

- **当前版本**: v1
- **版本格式**: `/api/v{major}`
- **向后兼容**: 保证同一主版本内的向后兼容性
- **废弃通知**: 新版本发布前3个月通知废弃

### 更新日志

#### v1.2.0 (2024-01-15) - 最新
- ✅ 新增Multi-Agent智能系统
- ✅ 新增个性化推荐功能
- ✅ 新增用户偏好管理
- ✅ 优化URL解析性能
- ✅ 增强图片分析能力

#### v1.1.0 (2023-12-01)
- ✅ 新增图片解析功能
- ✅ 优化任务搜索算法
- ✅ 增强标签系统
- ✅ 改进错误处理

#### v1.0.0 (2023-10-01)
- ✅ 基础任务管理功能
- ✅ 用户系统和认证
- ✅ URL解析Agent
- ✅ 基础分析功能

## 🛠️ 故障排除

### 常见问题

#### 1. 认证失败 (401)
```bash
# 检查token是否有效
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/users/me"

# 重新获取token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

#### 2. 请求超时
```javascript
// 设置合理的超时时间
const client = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 30000, // 30秒
});
```

#### 3. 推荐结果为空
```bash
# 检查用户档案完整性
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/v1/multi-agent/preferences"

# 更新用户档案
curl -X POST -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  "http://localhost:8000/api/v1/multi-agent/update-user-profile" \
  -d '{"skills": ["python", "javascript"], "interests": ["web3", "ai"]}'
```

### 错误码参考

| 错误码 | HTTP状态 | 描述 | 解决方案 |
|-------|---------|------|---------|
| `INVALID_TOKEN` | 401 | Token无效或过期 | 重新登录获取token |
| `INSUFFICIENT_PERMISSIONS` | 403 | 权限不足 | 检查用户权限 |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 | 检查资源ID |
| `VALIDATION_ERROR` | 422 | 请求参数验证失败 | 检查请求参数格式 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求频率过高 | 降低请求频率 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 | 联系技术支持 |

## 📞 技术支持

### 联系方式

- **技术文档**: [GitHub Wiki](https://github.com/bountygo/docs)
- **问题反馈**: [GitHub Issues](https://github.com/bountygo/issues)
- **开发者社区**: [Discord](https://discord.gg/bountygo)
- **邮件支持**: dev@bountygo.com

### 开发资源

- **API测试工具**: [Postman Collection](./postman/BountyGo_API.json)
- **代码示例**: [GitHub Examples](https://github.com/bountygo/examples)
- **SDK下载**: [NPM](https://www.npmjs.com/package/@bountygo/sdk) | [PyPI](https://pypi.org/project/bountygo-sdk/)

## 🔮 未来规划

### 即将推出 (Q1 2024)

- 🔄 实时WebSocket API
- 📱 移动端专用API
- 🌐 GraphQL支持
- 🔐 OAuth2.0集成

### 长期规划 (2024)

- 🤖 更多AI Agent类型
- 🌍 多语言API文档
- 📊 高级分析API
- 🔗 第三方平台集成

---

**最后更新**: 2024-01-15  
**文档版本**: v1.2.0  
**API版本**: v1