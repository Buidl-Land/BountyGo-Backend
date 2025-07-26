# Multi-Agent System API 使用文档

## 概述

Multi-Agent System API 提供了智能协调的多Agent服务，包括：

- 智能用户输入处理
- 自然语言聊天交互
- 用户偏好管理
- 个性化任务推荐
- 系统状态监控

## 基础信息

- **基础URL**: `/api/v1/multi-agent`
- **认证方式**: Bearer Token (JWT)
- **内容类型**: `application/json`

## API端点

### 1. 处理用户输入

**POST** `/api/v1/multi-agent/process`

智能处理用户输入，支持文本、URL、图片等多种内容类型。

#### 请求参数

```json
{
  "content": "https://github.com/example/project 请帮我分析这个项目",
  "context": {
    "task_type": "编程",
    "language": "中文",
    "create_task": true
  }
}
```

#### 响应示例

```json
{
  "success": true,
  "task_info": {
    "title": "Python Web项目开发",
    "description": "基于GitHub项目的Web应用开发任务",
    "reward": 500.0,
    "reward_currency": "USD",
    "deadline": "2024-12-31T23:59:59",
    "tags": ["python", "web", "github"],
    "difficulty_level": "中级",
    "estimated_hours": 20
  },
  "response_message": "已成功分析项目并创建任务",
  "user_intent": "task_creation",
  "suggestions": [
    "可以添加更多技术细节",
    "建议设置更具体的截止日期"
  ],
  "processing_time": 3.2,
  "error_message": null
}
```

#### 使用示例

```bash
curl -X POST "http://localhost:8000/api/v1/multi-agent/process" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "请帮我分析这个URL: https://github.com/example/project",
    "context": {"create_task": true}
  }'
```

### 2. 智能聊天交互

**POST** `/api/v1/multi-agent/chat`

与智能助手进行自然语言对话，自动识别用户意图。

#### 请求参数

```json
{
  "message": "我想找一些Python相关的编程任务"
}
```

#### 响应示例

```json
{
  "message": "我为您找到了几个Python相关的任务，您可以查看推荐列表。这些任务都符合您的技能水平。",
  "task_info": null,
  "suggestions": [
    "查看个性化推荐",
    "更新技能档案",
    "设置任务偏好"
  ],
  "requires_action": true,
  "action_type": "show_recommendations",
  "processing_time": 1.8
}
```

### 3. 用户偏好管理

#### 获取用户偏好

**GET** `/api/v1/multi-agent/preferences`

获取当前用户的偏好设置。

#### 响应示例

```json
{
  "user_id": "user123",
  "output_format": "detailed",
  "language": "zh-CN",
  "analysis_focus": ["technical_requirements", "reward_analysis"],
  "quality_threshold": 0.8,
  "auto_create_tasks": true,
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### 更新用户偏好

**PUT** `/api/v1/multi-agent/preferences`

更新用户偏好设置。

#### 请求参数

```json
{
  "output_format": "concise",
  "language": "en-US",
  "analysis_focus": ["reward_analysis", "deadline_analysis"],
  "quality_threshold": 0.9,
  "auto_create_tasks": false
}
```

#### 获取偏好建议

**GET** `/api/v1/multi-agent/preferences/suggestions`

基于用户行为获取偏好优化建议。

#### 响应示例

```json
{
  "suggestions": [
    {
      "preference_key": "analysis_focus",
      "suggested_value": ["technical_requirements", "difficulty_assessment"],
      "reason": "基于您的历史任务选择，建议关注技术要求分析",
      "confidence": 0.85
    }
  ]
}
```

### 4. 个性化推荐系统

#### 获取任务推荐

**GET** `/api/v1/multi-agent/recommendations?limit=10`

获取基于用户档案的个性化任务推荐。

#### 响应示例

```json
{
  "recommendations": [
    {
      "task_id": 123,
      "title": "Python Web爬虫开发",
      "description": "开发一个高效的Web数据采集工具",
      "reward": 800.0,
      "reward_currency": "USD",
      "tags": ["python", "web-scraping", "data"],
      "difficulty_level": "中级",
      "estimated_hours": 25,
      "deadline": "2024-02-15T23:59:59Z",
      "match_score": 0.92,
      "match_reasons": [
        "匹配您的Python技能",
        "符合您的薪资期望",
        "与您的兴趣领域相关"
      ]
    }
  ],
  "total_count": 1,
  "user_profile": {
    "skills": ["python", "web-development", "data-analysis"],
    "interests": ["web3", "automation", "data-science"],
    "preferences": {
      "output_format": "detailed",
      "language": "zh-CN",
      "analysis_focus": ["technical_requirements"],
      "task_types": ["programming", "web3"]
    }
  }
}
```

#### 自然语言推荐请求

**POST** `/api/v1/multi-agent/ask-recommendations`

通过自然语言描述获取推荐。

#### 请求参数

```json
{
  "message": "我想找一些区块链相关的高薪任务，最好是Solidity开发"
}
```

#### 更新用户档案

**POST** `/api/v1/multi-agent/update-user-profile`

更新用户技能和兴趣档案以改善推荐效果。

#### 请求参数

```json
{
  "skills": ["python", "solidity", "web3", "smart-contracts"],
  "interests": ["blockchain", "defi", "nft", "dao"]
}
```

### 5. 系统监控

#### 系统状态检查

**GET** `/api/v1/multi-agent/status`

获取多Agent系统的详细状态信息。

#### 响应示例

```json
{
  "coordinator_status": {
    "initialized": true,
    "processing_stats": {
      "total_requests": 1250,
      "success_rate": 0.96,
      "avg_processing_time": 2.8
    },
    "orchestrator": {
      "active_agents": 5,
      "queue_size": 3,
      "last_health_check": "2024-01-15T10:25:00Z"
    }
  },
  "config_summary": {
    "default_model": "qwen/qwen3-coder-480b-a35b-instruct",
    "enabled_features": ["url_parsing", "image_analysis", "recommendations"],
    "cache_enabled": true
  },
  "performance_stats": {
    "coordinator": {
      "memory_usage": "245MB",
      "cpu_usage": "15%"
    },
    "preference_manager": {
      "cache_hit_rate": 0.78,
      "avg_response_time": 0.5
    }
  }
}
```

#### 健康检查

**GET** `/api/v1/multi-agent/health`

快速健康检查端点。

#### 响应示例

```json
{
  "status": "healthy",
  "components": {
    "smart_coordinator": true,
    "config_manager": true,
    "preference_manager": true,
    "agent_orchestrator": true
  }
}
```

### 6. 交互历史

**GET** `/api/v1/multi-agent/history?limit=50`

获取用户的交互历史记录。

#### 响应示例

```json
{
  "history": [
    {
      "input_content": "分析这个GitHub项目",
      "input_type": "text_with_url",
      "user_intent": "task_creation",
      "result_success": true,
      "processing_time": 3.2,
      "timestamp": "2024-01-15T10:20:00Z",
      "metadata": {
        "url_detected": "https://github.com/example/project",
        "task_created": true
      }
    }
  ]
}
```

### 7. 便捷分析接口

#### URL分析

**POST** `/api/v1/multi-agent/analyze-url`

快速分析URL内容的便捷接口。

#### 请求参数

```json
{
  "url": "https://github.com/example/project",
  "create_task": true
}
```

#### 图片分析

**POST** `/api/v1/multi-agent/analyze-image`

快速分析图片内容的便捷接口。

#### 请求参数

```json
{
  "image_data": "data:image/png;base64,iVBORw0KGgoAAAANS...",
  "create_task": false
}
```

## 支持的输入类型

Multi-Agent系统支持以下输入类型：

1. **纯文本内容**
   - 任务描述
   - 需求说明
   - 问题咨询

2. **URL链接**
   - GitHub项目链接
   - 任务发布页面
   - 技术文档链接

3. **图片内容**
   - 任务截图
   - 需求图表
   - 设计稿

4. **混合内容**
   - 文本 + URL
   - 文本 + 图片
   - 多种类型组合

## 用户意图识别

系统能自动识别以下用户意图：

- `task_creation` - 创建任务
- `task_search` - 搜索任务
- `information_query` - 信息查询
- `preference_update` - 偏好更新
- `recommendation_request` - 推荐请求
- `general_chat` - 一般聊天

## 错误处理

### 常见错误码

- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 认证失败
- `429 Too Many Requests`: 请求频率过高
- `500 Internal Server Error`: 服务器内部错误

### 错误响应格式

```json
{
  "detail": "错误描述信息",
  "error_code": "INVALID_INPUT",
  "suggestions": ["检查输入格式", "重试请求"]
}
```

## 最佳实践

### 1. 输入优化
- 提供清晰的上下文信息
- 使用结构化的输入格式
- 避免过长的单次输入

### 2. 偏好设置
- 定期更新用户偏好
- 根据反馈调整设置
- 利用偏好建议功能

### 3. 推荐系统
- 保持用户档案更新
- 提供反馈改善推荐
- 利用自然语言查询

### 4. 性能优化
- 合理设置请求频率
- 利用缓存机制
- 监控系统状态

## 集成示例

### JavaScript/TypeScript

```typescript
class MultiAgentClient {
  private baseUrl = 'http://localhost:8000/api/v1/multi-agent';
  private token: string;

  constructor(token: string) {
    this.token = token;
  }

  async processInput(content: string, context?: any) {
    const response = await fetch(`${this.baseUrl}/process`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ content, context }),
    });
    return response.json();
  }

  async chat(message: string) {
    const response = await fetch(`${this.baseUrl}/chat`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    });
    return response.json();
  }

  async getRecommendations(limit = 10) {
    const response = await fetch(`${this.baseUrl}/recommendations?limit=${limit}`, {
      headers: {
        'Authorization': `Bearer ${this.token}`,
      },
    });
    return response.json();
  }

  async updatePreferences(preferences: any) {
    const response = await fetch(`${this.baseUrl}/preferences`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(preferences),
    });
    return response.json();
  }
}

// 使用示例
const client = new MultiAgentClient('your-token');

// 处理用户输入
const result = await client.processInput(
  "请分析这个项目: https://github.com/example/project",
  { create_task: true }
);

// 智能聊天
const chatResponse = await client.chat("我想找Python相关的任务");

// 获取推荐
const recommendations = await client.getRecommendations(5);
```

### Python

```python
import requests
from typing import Optional, Dict, Any, List

class MultiAgentClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1/multi-agent", token: str = None):
        self.base_url = base_url
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def process_input(self, content: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """处理用户输入"""
        response = self.session.post(
            f"{self.base_url}/process",
            json={"content": content, "context": context}
        )
        response.raise_for_status()
        return response.json()

    def chat(self, message: str) -> Dict[str, Any]:
        """智能聊天"""
        response = self.session.post(
            f"{self.base_url}/chat",
            json={"message": message}
        )
        response.raise_for_status()
        return response.json()

    def get_recommendations(self, limit: int = 10) -> Dict[str, Any]:
        """获取推荐"""
        response = self.session.get(
            f"{self.base_url}/recommendations",
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()

    def update_preferences(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """更新偏好"""
        response = self.session.put(
            f"{self.base_url}/preferences",
            json=preferences
        )
        response.raise_for_status()
        return response.json()

    def get_preferences(self) -> Dict[str, Any]:
        """获取偏好"""
        response = self.session.get(f"{self.base_url}/preferences")
        response.raise_for_status()
        return response.json()

    def update_user_profile(self, skills: List[str], interests: List[str]) -> Dict[str, Any]:
        """更新用户档案"""
        response = self.session.post(
            f"{self.base_url}/update-user-profile",
            json={"skills": skills, "interests": interests}
        )
        response.raise_for_status()
        return response.json()

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        response = self.session.get(f"{self.base_url}/status")
        response.raise_for_status()
        return response.json()

# 使用示例
client = MultiAgentClient(token="your-token")

try:
    # 处理输入
    result = client.process_input(
        "请帮我分析这个GitHub项目并创建任务",
        {"url": "https://github.com/example/project", "create_task": True}
    )
    print("处理结果:", result)
    
    # 智能聊天
    chat_response = client.chat("我想找一些Web3相关的高薪任务")
    print("聊天回复:", chat_response["message"])
    
    # 获取推荐
    recommendations = client.get_recommendations(5)
    print(f"找到 {len(recommendations['recommendations'])} 个推荐任务")
    
    # 更新偏好
    preferences = client.update_preferences({
        "language": "zh-CN",
        "analysis_focus": ["technical_requirements", "reward_analysis"],
        "auto_create_tasks": True
    })
    print("偏好已更新")
    
except requests.exceptions.RequestException as e:
    print("请求失败:", e)
```

## 更新日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 支持多种输入类型处理
- 智能聊天交互功能
- 用户偏好管理系统
- 个性化推荐引擎
- 系统监控和健康检查

### 未来计划
- 支持更多输入格式
- 增强推荐算法
- 添加批量处理功能
- 优化性能和响应速度
- 支持更多语言和地区