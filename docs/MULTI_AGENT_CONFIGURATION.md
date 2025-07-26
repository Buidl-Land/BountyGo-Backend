# 多Agent系统配置指南

## 概述

BountyGo支持两种多Agent配置方案：

1. **配置文件方式** - 在配置文件中指定不同Agent使用的模型
2. **CAMEL-AI框架集成** - 使用CAMEL-AI的Workforce模块进行多Agent协作

## 🎯 方案1：配置文件方式（推荐）

### 环境变量配置

在 `.env` 文件中配置不同Agent的模型：

```bash
# Multi-Agent System Configuration
MULTI_AGENT_FRAMEWORK=camel-ai
DEFAULT_MODEL_PROVIDER=ppio

# PPIO Models for different agents
PPIO_API_KEY=your_ppio_api_key_here
PPIO_BASE_URL=https://api.ppinfra.com/v3/openai

# URL Parser Agent - 使用编程优化模型
URL_PARSER_MODEL=qwen/qwen3-coder-480b-a35b-instruct
URL_PARSER_TEMPERATURE=0.1

# Image Analyzer Agent - 使用视觉模型
IMAGE_ANALYZER_MODEL=baidu/ernie-4.5-vl-28b-a3b
IMAGE_ANALYZER_TEMPERATURE=0.1

# Content Extractor Agent - 使用通用模型
CONTENT_EXTRACTOR_MODEL=moonshotai/kimi-k2-instruct
CONTENT_EXTRACTOR_TEMPERATURE=0.1

# Task Creator Agent - 使用推理优化模型
TASK_CREATOR_MODEL=deepseek/deepseek-r1-0528
TASK_CREATOR_TEMPERATURE=0.0

# Quality Checker Agent - 使用高性能模型
QUALITY_CHECKER_MODEL=qwen/qwen3-235b-a22b-instruct-2507
QUALITY_CHECKER_TEMPERATURE=0.0
```

### 代码中的使用

```python
from app.agent.multi_agent_config import ModelConfigManager, AgentRole

# 创建配置管理器
config_manager = ModelConfigManager()

# 获取特定任务的模型配置
url_parser_config = config_manager.get_model_for_task("url_parsing")
image_analyzer_config = config_manager.get_model_for_task("image_analysis")

# 在Agent中使用
url_parsing_agent = URLParsingAgent(url_parser_config)
image_parsing_agent = ImageParsingAgent(image_analyzer_config)
```

### 硬编码配置示例

如果不想使用环境变量，可以在代码中硬编码：

```python
from app.agent.multi_agent_config import (
    ModelConfigManager, AgentRole, AgentModelConfig, ModelProvider
)

# 创建配置管理器
manager = ModelConfigManager()

# 硬编码配置不同Agent
manager.add_agent_config(
    AgentRole.URL_PARSER,
    AgentModelConfig(
        provider=ModelProvider.PPIO,
        model_name="qwen/qwen3-coder-480b-a35b-instruct",
        api_key="your_api_key",
        base_url="https://api.ppinfra.com/v3/openai",
        temperature=0.1,
        system_message="你是URL解析专家"
    )
)

manager.add_agent_config(
    AgentRole.IMAGE_ANALYZER,
    AgentModelConfig(
        provider=ModelProvider.PPIO,
        model_name="baidu/ernie-4.5-vl-28b-a3b",
        api_key="your_api_key",
        base_url="https://api.ppinfra.com/v3/openai",
        supports_vision=True,
        temperature=0.1,
        system_message="你是图片分析专家"
    )
)
```

## 🚀 方案2：CAMEL-AI Workforce集成

### 安装依赖

```bash
pip install camel-ai
```

### 基本使用

```python
from app.agent.camel_workforce_service import CAMELWorkforceService
import asyncio

async def main():
    # 创建Workforce服务
    workforce_service = CAMELWorkforceService()
    
    # 初始化
    await workforce_service.initialize()
    
    # 使用多Agent处理URL
    task_info = await workforce_service.process_url_with_workforce(
        url="https://github.com/example/project",
        additional_context={"task_type": "编程", "language": "中文"}
    )
    
    print(f"任务标题: {task_info.title}")
    print(f"任务描述: {task_info.description}")
    
    # 使用多Agent处理图片
    with open("task_image.png", "rb") as f:
        image_data = f.read()
    
    image_task_info = await workforce_service.process_image_with_workforce(
        image_data=image_data,
        additional_prompt="请重点关注技术要求"
    )
    
    # 清理资源
    await workforce_service.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

### 自定义Workforce配置

```python
from app.agent.camel_workforce_service import create_camel_workforce_service

# 创建自定义Workforce
workforce_service = create_camel_workforce_service(
    workforce_size=3,           # 3个Agent协作
    collaboration_mode="hierarchical"  # 层次化协作
)
```

## 📊 协作模式说明

### 1. Pipeline模式（推荐）
- **特点**: Agent按顺序处理任务
- **适用场景**: 复杂任务需要分步骤处理
- **优势**: 结果可控，错误容易定位

```
URL解析 → 内容提取 → 任务创建 → 质量检查
```

### 2. Hierarchical模式
- **特点**: 有协调者Agent统一管理
- **适用场景**: 需要中央控制的任务
- **优势**: 协调性好，资源利用高效

```
协调者
├── URL解析Agent
├── 内容提取Agent
└── 任务创建Agent
```

### 3. Workforce模式（CAMEL-AI）
- **特点**: 多Agent并行协作，自动协商
- **适用场景**: 复杂决策任务
- **优势**: 智能化程度高，结果质量好

## 🔧 模型选择策略

### 按任务类型选择模型

| 任务类型 | 推荐模型 | 原因 |
|---------|---------|------|
| URL解析 | qwen/qwen3-coder-480b-a35b-instruct | 编程优化，结构化分析能力强 |
| 图片分析 | baidu/ernie-4.5-vl-28b-a3b | 视觉理解能力，免费使用 |
| 内容提取 | moonshotai/kimi-k2-instruct | 通用能力强，性价比高 |
| 任务创建 | deepseek/deepseek-r1-0528 | 推理能力强，逻辑性好 |
| 质量检查 | qwen/qwen3-235b-a22b-instruct-2507 | 大参数模型，准确性高 |

### 按成本考虑

- **免费选择**: baidu/ernie-4.5-vl-28b-a3b (视觉), moonshotai/kimi-k2-instruct (文本)
- **性价比选择**: qwen系列模型
- **高质量选择**: deepseek-r1, qwen3-235b等大参数模型

### 按速度考虑

- **快速响应**: 小参数模型 (7B-13B)
- **平衡选择**: 中等参数模型 (70B-235B)
- **高质量**: 大参数模型 (400B+)

## 🛠️ 实际部署建议

### 1. 生产环境配置

```python
# 生产环境 - 性能优先
production_config = {
    AgentRole.URL_PARSER: "qwen/qwen3-coder-480b-a35b-instruct",
    AgentRole.IMAGE_ANALYZER: "baidu/ernie-4.5-vl-28b-a3b", 
    AgentRole.CONTENT_EXTRACTOR: "moonshotai/kimi-k2-instruct",
    AgentRole.TASK_CREATOR: "deepseek/deepseek-r1-0528",
    AgentRole.QUALITY_CHECKER: "qwen/qwen3-235b-a22b-instruct-2507"
}
```

### 2. 开发环境配置

```python
# 开发环境 - 成本优先
development_config = {
    AgentRole.URL_PARSER: "moonshotai/kimi-k2-instruct",
    AgentRole.IMAGE_ANALYZER: "baidu/ernie-4.5-vl-28b-a3b",
    AgentRole.CONTENT_EXTRACTOR: "moonshotai/kimi-k2-instruct", 
    AgentRole.TASK_CREATOR: "moonshotai/kimi-k2-instruct",
    AgentRole.QUALITY_CHECKER: "moonshotai/kimi-k2-instruct"
}
```

### 3. 降级策略

```python
# 主模型不可用时的备用模型
fallback_config = {
    "primary": "qwen/qwen3-coder-480b-a35b-instruct",
    "fallback": "moonshotai/kimi-k2-instruct",
    "emergency": "通用默认模型"
}
```

## 🔍 监控和调试

### 状态检查

```python
# 检查Workforce状态
status = await workforce_service.get_workforce_status()
print(f"Agent数量: {status['agents_count']}")
print(f"协作模式: {status['workforce_config']['mode']}")
```

### 性能监控

```python
# 记录各Agent的性能指标
performance_metrics = {
    "url_parsing_time": 2.5,
    "image_analysis_time": 8.1, 
    "task_creation_time": 1.8,
    "total_time": 12.4
}
```

## 💡 最佳实践

### 1. 模型配置原则
- **专用模型优于通用模型** - 为特定任务选择专门优化的模型
- **视觉任务必须使用视觉模型** - 图片分析任务必须用支持视觉的模型
- **成本与质量平衡** - 根据业务需求选择合适的模型等级

### 2. 系统设计原则
- **渐进式部署** - 先从单Agent开始，逐步扩展到多Agent
- **降级保护** - 设置备用模型，确保服务可用性
- **监控告警** - 监控各Agent的性能和错误率

### 3. 配置管理原则
- **环境隔离** - 开发、测试、生产使用不同配置
- **版本控制** - 配置变更要有版本记录
- **安全存储** - API密钥等敏感信息安全存储

## 🔗 相关链接

- [CAMEL-AI官方文档](https://docs.camel-ai.org/)
- [PPIO模型列表](https://api.ppinfra.com/models)
- [BountyGo Agent配置示例](./examples/agent_config_examples.py) 