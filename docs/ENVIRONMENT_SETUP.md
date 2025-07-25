# BountyGo 环境配置指南

本文档提供了 BountyGo 后端应用的完整环境配置指南，包括开发、测试和生产环境的配置说明。

## 快速开始

### 1. 环境文件设置

```bash
# 复制环境配置模板
cp .env.example .env

# 或者使用开发环境配置
cp .env.dev .env

# 编辑配置文件
nano .env
```

### 2. 必需配置项

在开始之前，请确保设置以下必需的配置项：

```bash
# 数据库连接
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# PPIO API密钥（用于AI功能）
PPIO_API_KEY=sk_your_actual_api_key_here

# Google OAuth（用于用户认证）
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# 应用密钥（生产环境必须至少32字符）
SECRET_KEY=your-secret-key-here
```

### 3. 配置验证

```bash
# 运行配置验证脚本
python scripts/validate_config.py
```

## 环境文件说明

### .env.example
包含所有配置选项的示例文件，用作配置模板。包含详细的注释和推荐值。

### .env.dev
开发环境专用配置，包含适合本地开发的默认值和测试配置。

### .env.prod
生产环境配置模板，包含生产环境的安全配置和性能优化设置。

### .env
实际使用的环境配置文件（不包含在版本控制中）。

## 详细配置说明

### 应用基础配置

```bash
# 应用信息
APP_NAME=BountyGo Backend          # 应用名称
DEBUG=true                         # 调试模式（生产环境必须为false）
VERSION=1.0.0                      # 应用版本
ENVIRONMENT=development            # 环境类型：development/production
```

**注意事项：**
- 生产环境必须设置 `DEBUG=false`
- `ENVIRONMENT` 影响多个功能的行为，包括错误处理和日志级别

### 安全配置

```bash
# JWT和安全设置
SECRET_KEY=your-secret-key-here    # JWT签名密钥
JWT_ALGORITHM=HS256                # JWT算法
ACCESS_TOKEN_EXPIRE_MINUTES=15     # 访问令牌过期时间
REFRESH_TOKEN_EXPIRE_DAYS=30       # 刷新令牌过期时间
```

**安全要求：**
- 生产环境 `SECRET_KEY` 必须至少32字符
- 使用强随机字符串作为密钥
- 定期轮换生产环境密钥

### 数据库配置

```bash
# PostgreSQL数据库
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
DATABASE_POOL_SIZE=10              # 连接池大小
DATABASE_MAX_OVERFLOW=20           # 连接池最大溢出

# 可选：单独的数据库参数（用于Docker）
POSTGRES_DB=bountygo
POSTGRES_USER=bountygo
POSTGRES_PASSWORD=your-password
```

**性能调优：**
- 开发环境：`DATABASE_POOL_SIZE=5-10`
- 生产环境：`DATABASE_POOL_SIZE=20-50`

### Redis配置

```bash
# Redis缓存
REDIS_URL=redis://localhost:6379/0 # Redis连接URL
REDIS_CACHE_TTL=300                # 默认缓存TTL（秒）
```

## PPIO AI模型配置

URL AI代理使用PPIO平台的大语言模型进行智能内容分析。

### 基础配置

```bash
# PPIO API配置
PPIO_API_KEY=sk_your_api_key_here           # API密钥（必需）
PPIO_BASE_URL=https://api.ppinfra.com/v3/openai  # API基础URL
PPIO_MODEL_NAME=qwen/qwen3-coder-480b-a35b-instruct  # 模型名称
PPIO_MAX_TOKENS=4000                        # 最大token数
PPIO_TEMPERATURE=0.1                        # 温度参数（0-2）
PPIO_TIMEOUT=60                             # 请求超时时间（秒）
PPIO_MAX_RETRIES=3                          # 最大重试次数
```

### 支持的模型

按推荐优先级排序：

1. **qwen/qwen3-coder-480b-a35b-instruct** （推荐）
   - 支持结构化输出和函数调用
   - 专门优化编程任务
   - 适合代码和技术内容分析
   - 中文理解能力强

2. **moonshotai/kimi-k2-instruct**
   - 支持结构化输出和函数调用
   - 性价比高
   - 中文理解能力强
   - 适合一般内容分析

3. **deepseek/deepseek-r1-0528**
   - 支持结构化输出和函数调用
   - 推理能力强
   - 适合复杂逻辑分析

4. **qwen/qwen3-235b-a22b-instruct-2507**
   - 支持结构化输出和函数调用
   - 大参数模型，理解能力强
   - 成本较高

### API密钥获取

1. 访问 [PPIO平台](https://api.ppinfra.com/)
2. 注册账户并完成实名认证
3. 在控制台创建API密钥
4. 密钥格式：`sk_xxxxxxxxxxxxxxxxx`
5. 确保账户有足够余额

### 配置验证

```python
# 验证PPIO配置
from app.core.config import settings

validation = settings.validate_ppio_config()
if not validation["valid"]:
    print("配置错误:", validation["errors"])
```

## URL代理配置

### 内容提取设置

```bash
# 网页抓取配置
CONTENT_EXTRACTION_TIMEOUT=30      # 网页抓取超时时间（秒）
MAX_CONTENT_LENGTH=50000           # 最大内容长度（字符）
USER_AGENT=BountyGo-URLAgent/1.0   # 用户代理字符串
MAX_REDIRECTS=5                    # 最大重定向次数
VERIFY_SSL=true                    # 是否验证SSL证书
```

### 代理设置

```bash
# 网络代理配置
USE_PROXY=false                    # 是否使用代理
PROXY_URL=                         # 代理URL（支持http/https/socks4/socks5）
```

**代理URL格式：**
- HTTP代理：`http://proxy.example.com:8080`
- HTTPS代理：`https://proxy.example.com:8080`
- SOCKS4代理：`socks4://proxy.example.com:1080`
- SOCKS5代理：`socks5://proxy.example.com:1080`
- 带认证：`http://username:password@proxy.example.com:8080`

### 缓存配置

```bash
# 内容缓存设置
ENABLE_CONTENT_CACHE=true          # 启用内容缓存
CONTENT_CACHE_TTL=3600             # 缓存TTL（秒，默认1小时）
```

**缓存策略：**
- 开发环境：较短的TTL（1小时）便于测试
- 生产环境：较长的TTL（2-6小时）提高性能

## OAuth配置

### Google OAuth

```bash
# Google OAuth设置
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

**获取Google OAuth凭据：**

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建项目或选择现有项目
3. 启用Google+ API和Google Identity API
4. 创建OAuth 2.0客户端ID
5. 配置授权重定向URI：
   - 开发环境：`http://localhost:3000/auth/callback`
   - 生产环境：`https://yourdomain.com/auth/callback`

## 开发环境配置

### 开发测试功能

```bash
# 开发环境测试配置
DEV_TEST_TOKEN=dev-bountygo-test-token-2024  # 开发测试令牌
DEV_TEST_USER_EMAIL=dev@bountygo.com         # 测试用户邮箱
DEV_TEST_USER_NICKNAME=开发测试用户           # 测试用户昵称
```

**使用测试令牌：**

```bash
# 绕过OAuth认证进行API测试
curl -H "Authorization: Bearer dev-bountygo-test-token-2024" \
     http://localhost:8000/api/v1/users/me
```

### 开发环境优化

```bash
# 开发环境性能设置
DATABASE_POOL_SIZE=5               # 较小的连接池
CONTENT_CACHE_TTL=300             # 较短的缓存时间
PPIO_TIMEOUT=30                   # 较短的超时时间
```

## 生产环境配置

### 安全要求

```bash
# 生产环境安全配置
DEBUG=false                        # 必须关闭调试模式
ENVIRONMENT=production             # 设置为生产环境
SECRET_KEY=your-very-long-and-random-secret-key  # 强密钥
VERIFY_SSL=true                   # 必须验证SSL
```

**安全检查清单：**
- [ ] `DEBUG=false`
- [ ] `SECRET_KEY` 至少32字符
- [ ] 移除或禁用 `DEV_TEST_TOKEN`
- [ ] 使用HTTPS
- [ ] 限制 `ALLOWED_HOSTS`
- [ ] 使用强数据库密码

### 性能优化

```bash
# 生产环境性能配置
DATABASE_POOL_SIZE=20              # 增加数据库连接池
DATABASE_MAX_OVERFLOW=40           # 增加连接池溢出
REDIS_CACHE_TTL=1800              # 增加缓存时间
CONTENT_CACHE_TTL=7200            # 增加内容缓存时间
PPIO_TIMEOUT=90                   # 增加AI请求超时
CONTENT_EXTRACTION_TIMEOUT=60     # 增加内容提取超时
```

### 监控配置

```bash
# 生产环境监控
RATE_LIMIT_PER_MINUTE=100         # 增加速率限制
MAX_CONTENT_LENGTH=100000         # 增加内容长度限制
```

## 配置验证和测试

### 自动验证

```bash
# 运行完整配置验证
python scripts/validate_config.py

# 验证特定配置
python -c "
from app.core.config import settings
print('PPIO配置:', settings.validate_ppio_config())
print('URL代理配置:', settings.validate_url_agent_config())
print('生产环境配置:', settings.validate_production_config())
"
```

### 手动测试

```python
# 测试PPIO连接
import asyncio
from app.agent.config import url_agent_settings

async def test_ppio():
    config = url_agent_settings.get_ppio_config()
    result = await config.validate_api_connection()
    print(f"PPIO连接测试: {'成功' if result else '失败'}")

asyncio.run(test_ppio())
```

### 配置检查脚本

创建自定义配置检查脚本：

```python
#!/usr/bin/env python3
"""自定义配置检查脚本"""
import os
from app.core.config import settings

def check_required_configs():
    """检查必需的配置项"""
    required_configs = [
        'DATABASE_URL',
        'PPIO_API_KEY', 
        'SECRET_KEY',
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET'
    ]
    
    missing = []
    for config in required_configs:
        if not getattr(settings, config, None):
            missing.append(config)
    
    if missing:
        print(f"❌ 缺少必需配置: {', '.join(missing)}")
        return False
    
    print("✅ 所有必需配置已设置")
    return True

def check_environment_specific():
    """检查环境特定配置"""
    if settings.is_production():
        if settings.DEBUG:
            print("❌ 生产环境不应启用DEBUG")
            return False
        if len(settings.SECRET_KEY) < 32:
            print("❌ 生产环境SECRET_KEY太短")
            return False
    
    print(f"✅ {settings.ENVIRONMENT}环境配置正确")
    return True

if __name__ == "__main__":
    print("🔍 BountyGo 配置检查")
    print("=" * 30)
    
    checks = [
        check_required_configs(),
        check_environment_specific()
    ]
    
    if all(checks):
        print("\n🎉 配置检查通过！")
    else:
        print("\n💥 配置检查失败！")
```

## 故障排除

### 常见问题

#### 1. PPIO API连接失败

**症状：** API调用返回401或403错误

**解决方案：**
```bash
# 检查API密钥格式
echo $PPIO_API_KEY | grep "^sk_"

# 测试API连接
curl -H "Authorization: Bearer $PPIO_API_KEY" \
     https://api.ppinfra.com/v3/openai/models
```

#### 2. 数据库连接失败

**症状：** 应用启动时数据库连接错误

**解决方案：**
```bash
# 检查数据库URL格式
echo $DATABASE_URL

# 测试数据库连接
python -c "
import asyncpg
import asyncio
async def test():
    conn = await asyncpg.connect('$DATABASE_URL')
    await conn.close()
    print('数据库连接成功')
asyncio.run(test())
"
```

#### 3. Redis连接失败

**症状：** 缓存功能不工作

**解决方案：**
```bash
# 测试Redis连接
redis-cli -u $REDIS_URL ping

# 或使用Python测试
python -c "
import redis
r = redis.from_url('$REDIS_URL')
print('Redis连接:', r.ping())
"
```

#### 4. 内容提取超时

**症状：** URL处理经常超时

**解决方案：**
```bash
# 增加超时时间
CONTENT_EXTRACTION_TIMEOUT=60

# 启用代理（如果网络受限）
USE_PROXY=true
PROXY_URL=http://your-proxy:8080
```

### 调试技巧

#### 1. 启用详细日志

```bash
# 开启调试模式
DEBUG=true

# 查看配置摘要
python -c "
from app.core.config import settings
import json
print(json.dumps(settings.get_config_summary(), indent=2))
"
```

#### 2. 分步测试

```python
# 分步测试各个组件
import asyncio
from app.agent.service import URLAgentService
from app.core.database import get_db

async def test_components():
    # 测试内容提取
    from app.agent.content_extractor import ContentExtractor
    extractor = ContentExtractor()
    content = await extractor.extract_content("https://example.com")
    print("内容提取:", "成功" if content else "失败")
    
    # 测试AI分析
    from app.agent.url_parsing_agent import URLParsingAgent
    agent = URLParsingAgent()
    result = await agent.analyze_content("测试内容")
    print("AI分析:", "成功" if result else "失败")

asyncio.run(test_components())
```

## 部署建议

### Docker部署

```dockerfile
# 在Dockerfile中设置环境变量
ENV ENVIRONMENT=production
ENV DEBUG=false

# 复制生产配置
COPY .env.prod .env
```

### 环境变量管理

```bash
# 使用环境变量覆盖配置
export PPIO_API_KEY=sk_production_key
export DATABASE_URL=postgresql://...

# 或使用配置文件
docker run -v /path/to/.env:/app/.env bountygo:latest
```

### 健康检查

```python
# 添加健康检查端点
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "ppio": await check_ppio_api()
    }
    
    if all(checks.values()):
        return {"status": "healthy", "checks": checks}
    else:
        raise HTTPException(500, {"status": "unhealthy", "checks": checks})
```

## 更新日志

- **v1.0.0**: 初始配置文档
- **v1.1.0**: 添加PPIO AI模型配置
- **v1.2.0**: 添加URL代理配置选项
- **v1.3.0**: 添加生产环境配置和验证
- **v1.4.0**: 添加详细的故障排除指南