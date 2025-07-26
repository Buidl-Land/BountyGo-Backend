# URL Agent API 使用文档

## 概述

URL Agent API 提供了AI驱动的URL内容提取和任务信息解析功能。通过这些API，用户可以：

- 从URL中智能提取任务信息
- 分析文本内容并提取结构化数据
- 自动创建任务到数据库
- 监控服务状态和性能

## 基础信息

- **基础URL**: `/api/v1/url-agent`
- **认证方式**: Bearer Token (JWT)
- **内容类型**: `application/json`

## API端点

### 1. 处理URL并提取任务信息

**POST** `/api/v1/url-agent/process`

处理URL并提取任务信息，可选择自动创建任务。

#### 请求参数

```json
{
  "url": "https://github.com/example/project",
  "auto_create": false
}
```

#### 响应示例

```json
{
  "success": true,
  "task_id": 123,
  "extracted_info": {
    "title": "Python Web Scraping Project",
    "description": "Build a web scraping tool using Python and BeautifulSoup",
    "reward": 500.0,
    "reward_currency": "USD",
    "deadline": "2024-12-31T23:59:59",
    "tags": ["python", "web-scraping", "beautifulsoup"],
    "difficulty_level": "中级",
    "estimated_hours": 20
  },
  "processing_time": 2.5
}
```

#### 使用示例

```bash
curl -X POST "http://localhost:8000/api/v1/url-agent/process" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/XSpoonAi/spoon-devcall-s1",
    "auto_create": false
  }'
```

### 2. 从URL提取任务信息（公开端点）

**POST** `/api/v1/url-agent/extract-info`

从URL提取任务信息，不创建任务。此端点无需认证。

#### 请求参数

```json
{
  "url": "https://github.com/example/project"
}
```

#### 响应示例

```json
{
  "title": "XSpoonAi/spoon-devcall-s1 开发贡献",
  "description": "通过在GitHub上创建账户来参与XSpoonAi/spoon-devcall-s1项目的开发工作",
  "reward": null,
  "reward_currency": null,
  "deadline": null,
  "tags": ["github", "安全", "企业级开发", "开源贡献"],
  "difficulty_level": "中级",
  "estimated_hours": 20
}
```

#### 使用示例

```bash
curl -X POST "http://localhost:8000/api/v1/url-agent/extract-info" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/XSpoonAi/spoon-devcall-s1"
  }'
```

### 3. 从文本内容提取任务信息（公开端点）

**POST** `/api/v1/url-agent/extract-from-content`

从文本内容提取任务信息。此端点无需认证。

#### 请求参数

```json
{
  "content": "Looking for a Python developer to build a web scraping tool. Budget: $500. Deadline: 2024-12-31."
}
```

#### 响应示例

```json
{
  "title": "Python Developer Needed for Web Scraping Project",
  "description": "We are looking for an experienced Python developer to build a web scraping tool",
  "reward": 500.0,
  "reward_currency": "USD",
  "deadline": "2024-12-31T00:00:00",
  "tags": ["python", "web-scraping", "developer"],
  "difficulty_level": "中级",
  "estimated_hours": null
}
```

### 4. 从任务信息创建任务

**POST** `/api/v1/url-agent/create-task`

从提取的任务信息创建任务到数据库。

#### 请求参数

```json
{
  "title": "Python Web Scraping Project",
  "description": "Build a web scraping tool",
  "reward": 500.0,
  "reward_currency": "USD",
  "deadline": "2024-12-31T23:59:59",
  "tags": ["python", "web-scraping"],
  "difficulty_level": "中级",
  "estimated_hours": 20
}
```

#### 查询参数

- `source_url` (可选): 源URL

### 5. 获取服务状态（公开端点）

**GET** `/api/v1/url-agent/status`

获取URL代理服务状态和健康检查结果。

#### 响应示例

```json
{
  "service_name": "URLAgentService",
  "status": "healthy",
  "components": {
    "content_extractor": {"status": "ready"},
    "url_parsing_agent": {"status": "ready"},
    "ppio_client": {"status": "ready", "connection_test": true}
  },
  "metrics": {
    "total_requests": 100,
    "success_rate": 0.95,
    "avg_processing_time": 2.3
  }
}
```

### 6. 获取性能指标

**GET** `/api/v1/url-agent/metrics`

获取详细的性能指标（需要认证）。

### 7. 重置性能指标

**POST** `/api/v1/url-agent/reset-metrics`

重置性能指标（需要认证）。

## 支持的URL类型

URL Agent 支持以下类型的URL：

1. **GitHub项目和Issue**
   - `https://github.com/user/repo`
   - `https://github.com/user/repo/issues/123`

2. **自由职业平台**
   - Upwork, Freelancer, Fiverr等平台的任务页面

3. **开发者社区**
   - Stack Overflow Jobs
   - AngelList
   - Remote OK

4. **其他包含任务信息的网页**
   - 公司招聘页面
   - 项目需求文档
   - 任务描述页面

## 错误处理

### 常见错误码

- `400 Bad Request`: 请求参数错误或URL无效
- `401 Unauthorized`: 缺少或无效的认证令牌
- `500 Internal Server Error`: 服务器内部错误

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### 常见错误情况

1. **URL验证失败**
   - 不支持的协议（仅支持http/https）
   - 内网地址访问被禁止
   - URL格式无效

2. **内容提取失败**
   - 网页无法访问（404, 500等）
   - 网络连接超时
   - 内容类型不支持（非HTML）

3. **AI分析失败**
   - API配额不足
   - 内容格式无法解析
   - 模型服务不可用

## 开发环境测试

在开发环境中，可以使用测试token进行API测试：

```bash
# 获取测试token信息
curl "http://localhost:8000/api/v1/dev-auth"

# 使用测试token
curl -X POST "http://localhost:8000/api/v1/url-agent/process" \
  -H "Authorization: Bearer dev-bountygo-Dsdlr9dYRAlfT0H9VFTF_g-2024" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/example/project", "auto_create": false}'
```

## 性能考虑

1. **处理时间**: 通常2-5秒，取决于网页复杂度和AI分析时间
2. **并发限制**: 建议不超过10个并发请求
3. **缓存**: 相同URL的结果会被缓存一段时间
4. **重试机制**: 内置3次重试机制处理临时错误

## 最佳实践

1. **URL预验证**: 在发送请求前验证URL格式
2. **错误处理**: 实现适当的错误处理和用户提示
3. **超时设置**: 设置合理的请求超时时间（建议30秒）
4. **批量处理**: 避免短时间内大量请求，使用队列机制
5. **结果验证**: 验证提取的任务信息是否符合预期

## 集成示例

### JavaScript/TypeScript

```typescript
interface TaskInfo {
  title: string;
  description?: string;
  reward?: number;
  reward_currency?: string;
  deadline?: string;
  tags: string[];
  difficulty_level?: string;
  estimated_hours?: number;
}

class URLAgentClient {
  private baseUrl = 'http://localhost:8000/api/v1/url-agent';
  private token?: string;

  constructor(token?: string) {
    this.token = token;
  }

  async extractInfo(url: string): Promise<TaskInfo> {
    const response = await fetch(`${this.baseUrl}/extract-info`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  async processUrl(url: string, autoCreate = false) {
    if (!this.token) {
      throw new Error('Token required for this operation');
    }

    const response = await fetch(`${this.baseUrl}/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`,
      },
      body: JSON.stringify({ url, auto_create: autoCreate }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }
}

// 使用示例
const client = new URLAgentClient('your-token');

try {
  const taskInfo = await client.extractInfo('https://github.com/example/project');
  console.log('提取的任务信息:', taskInfo);
} catch (error) {
  console.error('提取失败:', error);
}
```

### Python

```python
import requests
from typing import Optional, Dict, Any

class URLAgentClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1/url-agent", token: Optional[str] = None):
        self.base_url = base_url
        self.token = token
        self.session = requests.Session()
        
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def extract_info(self, url: str) -> Dict[str, Any]:
        """从URL提取任务信息"""
        response = self.session.post(
            f"{self.base_url}/extract-info",
            json={"url": url}
        )
        response.raise_for_status()
        return response.json()

    def extract_from_content(self, content: str) -> Dict[str, Any]:
        """从文本内容提取任务信息"""
        response = self.session.post(
            f"{self.base_url}/extract-from-content",
            json={"content": content}
        )
        response.raise_for_status()
        return response.json()

    def process_url(self, url: str, auto_create: bool = False) -> Dict[str, Any]:
        """处理URL并可选择创建任务"""
        if not self.token:
            raise ValueError("Token required for this operation")
            
        response = self.session.post(
            f"{self.base_url}/process",
            json={"url": url, "auto_create": auto_create}
        )
        response.raise_for_status()
        return response.json()

    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        response = self.session.get(f"{self.base_url}/status")
        response.raise_for_status()
        return response.json()

# 使用示例
client = URLAgentClient(token="your-token")

try:
    # 提取任务信息
    task_info = client.extract_info("https://github.com/example/project")
    print("提取的任务信息:", task_info)
    
    # 处理URL并创建任务
    result = client.process_url("https://github.com/example/project", auto_create=True)
    print("处理结果:", result)
    
except requests.exceptions.RequestException as e:
    print("请求失败:", e)
```

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 支持GitHub URL解析
- 基础的任务信息提取功能
- 服务状态监控

### 3. 图片解析功能

#### 从Base64图片提取任务信息

**POST** `/api/v1/url-agent/extract-from-image`

从Base64编码的图片中提取结构化任务信息。

#### 请求参数

```json
{
  "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...",
  "additional_prompt": "请重点分析技术要求",
  "context": {
    "task_type": "编程",
    "platform": "GitHub",
    "language": "中文"
  }
}
```

#### 使用示例

```bash
curl -X POST "http://localhost:8000/api/v1/url-agent/extract-from-image" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANS...",
    "additional_prompt": "请分析这个任务截图"
  }'
```

#### 文件上传图片解析

**POST** `/api/v1/url-agent/upload-image`

直接上传图片文件进行任务信息提取。

#### 请求参数（multipart/form-data）

- `file`: 图片文件 (支持 JPG, PNG, GIF, BMP, WebP)
- `additional_prompt`: 额外分析提示（可选）
- `context_json`: JSON格式的上下文信息（可选）

#### 使用示例

```bash
curl -X POST "http://localhost:8000/api/v1/url-agent/upload-image" \
  -F "file=@task_screenshot.png" \
  -F "additional_prompt=请提取任务的奖励信息" \
  -F 'context_json={"task_type":"编程","language":"中文"}'
```

**注意**: 图片解析功能的详细文档请参考：[图片解析API文档](./image_parsing_api.md)

### 未来计划
- 支持更多平台URL
- 批量处理功能
- 结果缓存优化
- 更精确的AI分析模型
- 视频内容解析功能