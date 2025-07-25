# BountyGo 配置指南

本文档描述了 BountyGo 后端应用的环境配置选项，包括开发和生产环境的配置建议。

## 环境文件

### .env.example
包含所有配置选项的示例文件，用作配置模板。

### .env.dev  
开发环境专用配置，包含适合本地开发的默认值。

### .env
实际使用的环境配置文件（不包含在版本控制中）。

## 核心配置

### 应用设置
```bash
APP_NAME=BountyGo Backend          # 应用名称
DEBUG=true                         # 调试模式（生产环境应设为false）
VERSION=1.0.0                      # 应用版本
ENVIRONMENT=development            # 环境类型：development/production
```

### 安全配置
```bash
SECRET_KEY=your-secret-key-here    # JWT签名密钥（生产环境必须至少32字符）
JWT_ALGORITHM=HS256                # JWT算法
ACCESS_TOKEN_EXPIRE_MINUTES=15     # 访问令牌过期时间（分钟）
REFRESH_TOKEN_EXPIRE_DAYS=30       # 刷新令牌过期时间（天）
```

### 数据库配置
```bash
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
DATABASE_POOL_SIZE=10              # 连接池大小
DATABASE_MAX_OVERFLOW=20           # 连接池最大溢出
```

### Redis配置
```bash
REDIS_URL=redis://localhost:6379/0 # Redis连接URL
REDIS_CACHE_TTL=300                # 缓存TTL（秒）
```

## PPIO AI模型配置

URL AI代理使用PPIO平台的大语言模型进行内容分析。

### 基础配置
```bash
PPIO_API_KEY=sk_your_api_key_here           # PPIO API密钥（必需）
PPIO_BASE_URL=https://api.ppinfra.com/v3/openai  # API基础URL
PPIO_MODEL_NAME=qwen/qwen3-coder-480b-a35b-instruct  # 模型名称
PPIO_MAX_TOKENS=4000                        # 最大token数
PPIO_TEMPERATURE=0.1                        # 温度参数（0-2）
```

### 支持的模型

按推荐优先级排序：

1. **qwen/qwen3-coder-480b-a35b-instruct** （推荐）
   - 支持结构化输出和函数调用
   - 专门优化编程任务
   - 适合代码和技术内容分析

2. **moonshotai/kimi-k2-instruct**
   - 支持结构化输出和函数调用
   - 性价比高
   - 中文理解能力强

3. **deepseek/deepseek-r1-0528**
   - 支持结构化输出和函数调用
   - 推理能力强
   - 适合复杂逻辑分析

4. **qwen/qwen3-235b-a22b-instruct-2507**
   - 支持结构化输出和函数调用
   - 大参数模型，理解能力强

### API密钥获取

1. 访问 [PPIO平台](https://api.ppinfra.com/)
2. 注册账户并完成认证
3. 在控制台创建API密钥
4. 密钥格式：`sk_xxxxxxxxxxxxxxxxx`

## URL代理配置

### 内容提取设置
```bash
CONTENT_EXTRACTION_TIMEOUT=30      # 网页抓取超时时间（秒）
MAX_CONTENT_LENGTH=50000           # 最大内容长度（字符）
```

### 代理设置
```bash
USE_PROXY=false                    # 是否使用代理
PROXY_URL=                         # 代理URL（如果启用代理）
```

### 缓存配置
```bash
ENABLE_CONTENT_CACHE=true          # 启用内容缓存
CONTENT_CACHE_TTL=3600             # 缓存TTL（秒，默认1小时）
```

## OAuth配置

### Google OAuth
```bash
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

获取Google OAuth凭据：
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建项目或选择现有项目
3. 启用Google+ API
4. 创建OAuth 2.0客户端ID
5. 配置授权重定向URI

## 开发环境配置

### 测试令牌
```bash
DEV_TEST_TOKEN=dev-bountygo-test-token-2024  # 开发测试令牌
DEV_TEST_USER_EMAIL=dev@bountygo.com         # 测试用户邮箱
DEV_TEST_USER_NICKNAME=开发测试用户           # 测试用户昵称
```

开发环境可以使用测试令牌绕过OAuth认证：
```bash
curl -H "Authorization: Bearer dev-bountygo-test-token-2024" \
     http://localhost:8000/api/v1/users/me
```

## 生产环境配置

### 安全要求
- `SECRET_KEY` 必须至少32字符，使用强随机字符串
- `DEBUG` 必须设为 `false`
- `ENVIRONMENT` 设为 `production`
- 移除或禁用 `DEV_TEST_TOKEN`

### 性能优化
```bash
DATABASE_POOL_SIZE=20              # 增加数据库连接池
DATABASE_MAX_OVERFLOW=40           # 增加连接池溢出
REDIS_CACHE_TTL=1800              # 增加缓存时间
CONTENT_CACHE_TTL=7200            # 增加内容缓存时间
```

### 监控配置
```bash
RATE_LIMIT_PER_MINUTE=100         # 增加速率限制
CONTENT_EXTRACTION_TIMEOUT=60     # 增加超时时间
```

## 配置验证

应用启动时会自动验证配置。可以通过以下方式手动验证：

```python
from app.core.config import settings

# 验证PPIO配置
ppio_validation = settings.validate_ppio_config()
if not ppio_validation["valid"]:
    print("PPIO配置错误:", ppio_validation["errors"])

# 验证URL代理配置
agent_validation = settings.validate_url_agent_config()
if not agent_validation["valid"]:
    print("URL代理配置错误:", agent_validation["errors"])

# 获取配置摘要
config_summary = settings.get_config_summary()
print("配置摘要:", config_summary)
```

## 故障排除

### 常见问题

1. **PPIO API密钥无效**
   - 检查密钥格式是否以 `sk_` 开头
   - 确认密钥未过期
   - 验证账户余额充足

2. **数据库连接失败**
   - 检查 `DATABASE_URL` 格式
   - 确认数据库服务运行正常
   - 验证用户名密码正确

3. **Redis连接失败**
   - 检查 `REDIS_URL` 格式
   - 确认Redis服务运行
   - 验证网络连接

4. **内容提取超时**
   - 增加 `CONTENT_EXTRACTION_TIMEOUT`
   - 检查网络连接
   - 考虑启用代理

### 调试模式

启用调试模式获取详细日志：
```bash
DEBUG=true
```

### 配置检查脚本

创建配置检查脚本：
```python
#!/usr/bin/env python3
import asyncio
from app.core.config import settings
from app.agent.config import url_agent_settings

async def check_config():
    print("=== BountyGo 配置检查 ===")
    
    # 基础配置
    print(f"环境: {settings.ENVIRONMENT}")
    print(f"调试模式: {settings.DEBUG}")
    
    # PPIO配置验证
    ppio_config = url_agent_settings.get_ppio_config()
    try:
        is_valid = await ppio_config.validate_api_connection()
        print(f"PPIO API连接: {'✓ 正常' if is_valid else '✗ 失败'}")
    except Exception as e:
        print(f"PPIO API连接: ✗ 失败 - {e}")
    
    # 配置验证
    ppio_validation = settings.validate_ppio_config()
    agent_validation = settings.validate_url_agent_config()
    
    if ppio_validation["errors"]:
        print("PPIO配置错误:")
        for error in ppio_validation["errors"]:
            print(f"  - {error}")
    
    if agent_validation["errors"]:
        print("URL代理配置错误:")
        for error in agent_validation["errors"]:
            print(f"  - {error}")
    
    print("配置检查完成")

if __name__ == "__main__":
    asyncio.run(check_config())
```

## 环境迁移

### 从开发到生产

1. 复制 `.env.example` 到生产服务器
2. 修改生产环境特定配置
3. 设置强密钥和密码
4. 配置生产数据库和Redis
5. 获取生产环境OAuth凭据
6. 验证所有配置项

### 配置备份

定期备份环境配置（去除敏感信息）：
```bash
# 创建配置模板
grep -v -E "(SECRET_KEY|PASSWORD|API_KEY)" .env > .env.template
```

## 更新日志

- v1.0.0: 初始配置文档
- 添加PPIO AI模型配置
- 添加URL代理配置选项
- 添加配置验证功能