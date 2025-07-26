# 图片解析API 使用文档

## 概述

图片解析API基于PPIO视觉语言模型，能够智能分析图片内容并提取结构化的任务信息。支持多种图片格式，适用于任务截图、招聘海报、需求文档等场景。

## 支持的视觉模型

系统支持以下PPIO视觉语言模型：

| 模型名称 | 特点 | 推荐场景 |
|---------|------|----------|
| `baidu/ernie-4.5-vl-28b-a3b` | 支持结构化输出，免费 | 日常使用，推荐首选 |
| `thudm/glm-4.1v-9b-thinking` | 9B参数，轻量高效 | 快速处理 |
| `qwen/qwen2.5-vl-72b-instruct` | 72B参数，功能强大 | 复杂图片分析 |
| `baidu/ernie-4.5-vl-424b-a47b` | 424B参数，最强性能 | 高精度要求 |

## API端点

### 1. Base64图片解析

**POST** `/api/v1/url-agent/extract-from-image`

从Base64编码的图片数据中提取任务信息。

#### 请求参数

```json
{
  "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...",
  "additional_prompt": "请重点关注技术要求",
  "context": {
    "task_type": "编程",
    "platform": "GitHub",
    "language": "中文"
  }
}
```

#### 响应示例

```json
{
  "title": "Python Web爬虫开发",
  "description": "开发一个基于Scrapy的电商数据爬虫系统",
  "reward": 2000.0,
  "reward_currency": "USDT",
  "deadline": "2024-03-15T00:00:00",
  "tags": ["python", "scrapy", "爬虫", "数据采集"],
  "difficulty_level": "中级",
  "estimated_hours": 40
}
```

#### 使用示例

```bash
curl -X POST "http://localhost:8000/api/v1/url-agent/extract-from-image" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...",
    "additional_prompt": "这是一个编程任务图片，请提取详细的技术要求"
  }'
```

### 2. 文件上传解析

**POST** `/api/v1/url-agent/upload-image`

直接上传图片文件进行解析。

#### 请求参数（multipart/form-data）

- `file`: 图片文件
- `additional_prompt`: 额外分析提示（可选）
- `context_json`: JSON格式的上下文信息（可选）

#### 使用示例

```bash
curl -X POST "http://localhost:8000/api/v1/url-agent/upload-image" \
  -F "file=@task_screenshot.png" \
  -F "additional_prompt=请提取任务的技术栈要求" \
  -F 'context_json={"task_type":"开发","platform":"自由职业"}'
```

```python
import requests

with open("task_image.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/url-agent/upload-image",
        files={"file": f},
        data={
            "additional_prompt": "分析这个任务的奖励和难度",
            "context_json": '{"language": "中文"}'
        }
    )
    
task_info = response.json()
print(f"任务标题: {task_info['title']}")
```

## 技术规格

### 支持的图片格式

- **JPG/JPEG**: 最常用的图片格式
- **PNG**: 支持透明背景
- **GIF**: 支持动图（分析第一帧）
- **BMP**: Windows位图格式
- **WebP**: 现代高效格式

### 文件限制

- **最大文件大小**: 10MB
- **最大尺寸**: 4096 x 4096 像素
- **自动处理**: 超出尺寸会自动等比缩放

### 上下文参数

`context` 对象支持以下字段：

```json
{
  "task_type": "编程|设计|写作|营销|其他",
  "platform": "GitHub|Upwork|Fiverr|Freelancer|其他",
  "language": "中文|English|日本語|Français|其他",
  "focus_area": "技术栈|奖励|时间|难度|其他"
}
```

## 使用场景

### 1. 任务截图分析

适用于分析各种任务平台的截图：

```python
# 分析Upwork任务截图
context = {
    "task_type": "编程",
    "platform": "Upwork",
    "language": "English"
}
```

### 2. 招聘海报提取

从招聘图片中提取职位信息：

```python
# 分析招聘海报
context = {
    "task_type": "招聘",
    "focus_area": "薪资待遇",
    "language": "中文"
}
```

### 3. 需求文档分析

从文档截图中提取项目需求：

```python
# 分析需求文档
additional_prompt = "请重点提取功能需求和技术要求"
context = {
    "task_type": "项目开发",
    "focus_area": "技术栈"
}
```

### 4. 悬赏公告解析

从悬赏图片中提取赏金信息：

```python
# 分析Web3悬赏
context = {
    "task_type": "区块链",
    "platform": "GitHub",
    "focus_area": "奖励"
}
```

## JavaScript/TypeScript 集成

```typescript
interface ImageAnalysisRequest {
  image_base64: string;
  additional_prompt?: string;
  context?: {
    task_type?: string;
    platform?: string;
    language?: string;
    focus_area?: string;
  };
}

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

class ImageParsingClient {
  private baseUrl = 'http://localhost:8000/api/v1/url-agent';

  async analyzeImage(request: ImageAnalysisRequest): Promise<TaskInfo> {
    const response = await fetch(`${this.baseUrl}/extract-from-image`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Analysis failed: ${response.statusText}`);
    }

    return response.json();
  }

  async uploadAndAnalyze(
    file: File, 
    prompt?: string, 
    context?: any
  ): Promise<TaskInfo> {
    const formData = new FormData();
    formData.append('file', file);
    
    if (prompt) {
      formData.append('additional_prompt', prompt);
    }
    
    if (context) {
      formData.append('context_json', JSON.stringify(context));
    }

    const response = await fetch(`${this.baseUrl}/upload-image`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return response.json();
  }
}

// 使用示例
const client = new ImageParsingClient();

// 文件上传分析
const fileInput = document.getElementById('image-upload') as HTMLInputElement;
const file = fileInput.files?.[0];

if (file) {
  const result = await client.uploadAndAnalyze(
    file,
    "请分析这个任务的技术要求",
    { task_type: "编程", language: "中文" }
  );
  
  console.log('分析结果:', result);
}
```

## Python集成示例

```python
import asyncio
import base64
from app.agent.service import URLAgentService

async def analyze_image_file(image_path: str):
    """分析本地图片文件"""
    # 读取图片并转换为base64
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    # 创建服务实例
    service = URLAgentService()
    
    # 分析图片
    task_info = await service.extract_task_info_from_image(
        image_data=image_bytes,
        additional_prompt="请详细分析任务要求",
        context={
            "task_type": "编程",
            "platform": "自由职业",
            "language": "中文"
        }
    )
    
    return task_info

# 使用示例
async def main():
    result = await analyze_image_file("task_screenshot.png")
    print(f"任务标题: {result.title}")
    print(f"技能标签: {result.tags}")

asyncio.run(main())
```

## 错误处理

### 常见错误码

- `400 Bad Request`: 图片格式不支持或数据无效
- `413 Payload Too Large`: 图片文件过大
- `422 Unprocessable Entity`: 图片内容无法解析
- `500 Internal Server Error`: 服务器内部错误

### 错误响应格式

```json
{
  "detail": "图片格式不支持: image/tiff"
}
```

### 最佳实践

1. **图片预处理**: 确保图片清晰，文字可读
2. **大小优化**: 压缩图片以提高处理速度
3. **上下文信息**: 提供准确的上下文以提高解析精度
4. **错误重试**: 实现适当的重试机制
5. **结果验证**: 验证提取的信息是否合理

## 性能考虑

- **处理时间**: 通常5-15秒，取决于图片复杂度
- **并发限制**: 建议不超过5个并发请求
- **缓存策略**: 相同图片的结果会被缓存
- **模型选择**: 根据需求平衡精度和速度

## 开发环境测试

```bash
# 运行图片解析测试
conda activate camel-env
python app/agent/test_image_parsing.py

# 测试API端点
curl -X POST "http://localhost:8000/api/v1/url-agent/upload-image" \
  -F "file=@test_image.jpg" \
  -F "additional_prompt=测试解析"
```

## 注意事项

1. **隐私保护**: 图片不会被永久存储
2. **内容限制**: 不支持敏感或违法内容
3. **API限额**: 注意PPIO API的使用限额
4. **模型限制**: 视觉模型可能无法处理极模糊的图片

---

**图片解析API为BountyGo平台提供强大的视觉理解能力，让任务信息提取更加智能和便捷！** 🖼️✨ 