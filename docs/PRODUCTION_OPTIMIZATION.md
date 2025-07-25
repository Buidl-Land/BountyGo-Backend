# BountyGo 生产环境优化指南

本文档详细说明了BountyGo后端应用在生产环境中的性能优化配置和最佳实践。

## 目录

- [应用层优化](#应用层优化)
- [数据库优化](#数据库优化)
- [Redis缓存优化](#redis缓存优化)
- [PPIO模型优化](#ppio模型优化)
- [URL代理优化](#url代理优化)
- [系统层优化](#系统层优化)
- [Docker优化](#docker优化)
- [网络优化](#网络优化)
- [监控和调优](#监控和调优)

## 应用层优化

### FastAPI配置优化

```python
# app/main.py 生产环境优化配置
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI(
    title="BountyGo Backend",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,  # 生产环境可关闭文档
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# 添加压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 添加可信主机中间件
if settings.is_production():
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=settings.get_allowed_hosts()
    )
```

### 异步处理优化

```python
# 优化异步连接池
import asyncio
import aiohttp

# 全局连接池配置
connector = aiohttp.TCPConnector(
    limit=100,  # 总连接数限制
    limit_per_host=30,  # 每个主机连接数限制
    ttl_dns_cache=300,  # DNS缓存TTL
    use_dns_cache=True,
    keepalive_timeout=30,
    enable_cleanup_closed=True
)

# 在应用启动时创建全局session
async def create_http_session():
    return aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=60),
        headers={'User-Agent': settings.USER_AGENT}
    )
```

### 内存管理优化

```python
# app/core/config.py 内存优化配置
class Settings(BaseSettings):
    # 数据库连接池优化
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Redis连接池优化
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_RETRY_ON_TIMEOUT: bool = True
    REDIS_HEALTH_CHECK_INTERVAL: int = 30
    
    # 应用内存限制
    MAX_CONCURRENT_REQUESTS: int = 100
    REQUEST_TIMEOUT: int = 60
```

## 数据库优化

### PostgreSQL配置优化

```ini
# postgresql.conf 生产环境优化
# 内存配置
shared_buffers = 256MB                    # 25% of RAM
effective_cache_size = 1GB                # 75% of RAM
work_mem = 4MB                           # Per connection
maintenance_work_mem = 64MB              # For maintenance operations
wal_buffers = 16MB                       # WAL buffer size

# 连接配置
max_connections = 100                     # 根据实际需求调整
listen_addresses = '*'
port = 5432

# 查询优化
random_page_cost = 1.1                   # SSD优化
effective_io_concurrency = 200           # SSD并发IO
default_statistics_target = 100          # 统计信息采样

# 检查点配置
checkpoint_completion_target = 0.9       # 检查点完成目标
checkpoint_timeout = 10min               # 检查点超时
max_wal_size = 1GB                      # WAL最大大小
min_wal_size = 80MB                     # WAL最小大小

# 日志配置
log_destination = 'stderr'
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_statement = 'mod'                    # 记录修改语句
log_duration = on
log_min_duration_statement = 1000        # 记录慢查询(>1s)

# 自动清理配置
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 1min
```

### 数据库索引优化

```sql
-- 为常用查询创建索引
-- 用户表索引
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY idx_users_created_at ON users(created_at);

-- 任务表索引
CREATE INDEX CONCURRENTLY idx_tasks_sponsor_id ON tasks(sponsor_id);
CREATE INDEX CONCURRENTLY idx_tasks_status ON tasks(status);
CREATE INDEX CONCURRENTLY idx_tasks_created_at ON tasks(created_at);
CREATE INDEX CONCURRENTLY idx_tasks_deadline ON tasks(deadline);

-- 标签表索引
CREATE INDEX CONCURRENTLY idx_tags_name ON tags(name);
CREATE INDEX CONCURRENTLY idx_tags_category ON tags(category);

-- 任务标签关联表索引
CREATE INDEX CONCURRENTLY idx_task_tags_task_id ON task_tags(task_id);
CREATE INDEX CONCURRENTLY idx_task_tags_tag_id ON task_tags(tag_id);

-- 复合索引
CREATE INDEX CONCURRENTLY idx_tasks_status_created_at ON tasks(status, created_at);
CREATE INDEX CONCURRENTLY idx_tasks_sponsor_status ON tasks(sponsor_id, status);
```

### 数据库连接池优化

```python
# app/core/database.py 连接池优化
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_pre_ping=True,  # 连接健康检查
    echo=settings.DEBUG,
    future=True
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

## Redis缓存优化

### Redis配置优化

```conf
# redis.conf 生产环境优化
# 内存配置
maxmemory 512mb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# 持久化配置
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# 网络配置
timeout 300
tcp-keepalive 300
tcp-backlog 511

# 客户端配置
maxclients 10000

# 慢日志配置
slowlog-log-slower-than 10000
slowlog-max-len 128

# 安全配置
protected-mode yes
# requirepass your-redis-password

# 性能配置
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
list-compress-depth 0
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
```

### Redis缓存策略优化

```python
# app/core/redis.py 缓存优化
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

# 优化的Redis连接池
redis_pool = ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
    health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
    socket_keepalive=True,
    socket_keepalive_options={},
)

redis_client = redis.Redis(connection_pool=redis_pool)

# 缓存装饰器优化
import functools
import json
import hashlib

def cache_result(ttl: int = 3600, key_prefix: str = ""):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{_generate_cache_key(args, kwargs)}"
            
            # 尝试从缓存获取
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            await redis_client.setex(
                cache_key, 
                ttl, 
                json.dumps(result, default=str)
            )
            return result
        return wrapper
    return decorator

def _generate_cache_key(args, kwargs):
    """生成缓存键"""
    key_data = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(key_data.encode()).hexdigest()
```

## PPIO模型优化

### PPIO客户端优化

```python
# app/agent/client.py PPIO优化配置
class PPIOModelClient:
    def __init__(self, config: PPIOModelConfig):
        self.config = config
        self._session = None
        self._semaphore = asyncio.Semaphore(10)  # 限制并发请求
        
    async def _get_session(self):
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=20,
                limit_per_host=10,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30
            )
            
            timeout = aiohttp.ClientTimeout(
                total=self.config.timeout,
                connect=10,
                sock_read=30
            )
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'Authorization': f'Bearer {self.config.api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'BountyGo-URLAgent/1.0'
                }
            )
        return self._session
    
    async def generate_completion(self, messages: List[dict], **kwargs):
        async with self._semaphore:  # 限制并发
            return await self._make_request(messages, **kwargs)
```

### 模型调用优化

```python
# 批量处理优化
async def batch_process_urls(urls: List[str], batch_size: int = 5):
    """批量处理URL，避免过多并发请求"""
    results = []
    
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        batch_tasks = [process_single_url(url) for url in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        results.extend(batch_results)
        
        # 批次间延迟，避免API限流
        if i + batch_size < len(urls):
            await asyncio.sleep(1)
    
    return results

# 请求重试优化
async def retry_with_backoff(func, max_retries=3, base_delay=1):
    """指数退避重试"""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)
```

## URL代理优化

### 内容提取优化

```python
# app/agent/content_extractor.py 优化配置
class ContentExtractor:
    def __init__(self):
        self.session = None
        self.semaphore = asyncio.Semaphore(20)  # 限制并发请求
        
    async def _get_session(self):
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(
                total=settings.CONTENT_EXTRACTION_TIMEOUT,
                connect=10,
                sock_read=30
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'User-Agent': settings.USER_AGENT}
            )
        return self.session
    
    @cache_result(ttl=settings.CONTENT_CACHE_TTL, key_prefix="content")
    async def extract_content(self, url: str) -> WebContent:
        async with self.semaphore:
            return await self._extract_content_impl(url)
```

### 内容处理优化

```python
# 内容清理优化
def optimize_content_cleaning(html_content: str) -> str:
    """优化的内容清理"""
    # 使用lxml解析器（更快）
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 移除不需要的标签
    for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'header']):
        tag.decompose()
    
    # 移除广告和跟踪元素
    for tag in soup.find_all(attrs={'class': re.compile(r'ad|advertisement|tracking|analytics')}):
        tag.decompose()
    
    # 提取主要内容
    main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main'))
    
    if main_content:
        text = main_content.get_text(strip=True, separator=' ')
    else:
        text = soup.get_text(strip=True, separator=' ')
    
    # 清理文本
    text = re.sub(r'\s+', ' ', text)  # 合并空白字符
    text = text[:settings.MAX_CONTENT_LENGTH]  # 限制长度
    
    return text
```

## 系统层优化

### 操作系统优化

```bash
# /etc/sysctl.conf 系统优化配置
# 网络优化
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_max_tw_buckets = 5000
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_congestion_control = bbr

# 内存优化
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.overcommit_memory = 1

# 文件系统优化
fs.file-max = 65535
fs.inotify.max_user_watches = 524288

# 应用系统配置
sysctl -p
```

### 文件描述符限制

```bash
# /etc/security/limits.conf
* soft nofile 65535
* hard nofile 65535
* soft nproc 65535
* hard nproc 65535

# 验证配置
ulimit -n
ulimit -u
```

## Docker优化

### 多阶段构建优化

```dockerfile
# Dockerfile.prod 优化版本
FROM python:3.11-slim as builder

# 设置构建参数
ARG DEBIAN_FRONTEND=noninteractive

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    libjpeg-dev \
    zlib1g-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 升级pip并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel \
    && pip install --no-cache-dir -r requirements.txt

# 生产阶段
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    curl \
    libxml2 \
    libxslt1.1 \
    libjpeg62-turbo \
    zlib1g \
    libffi8 \
    libssl3 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 创建应用用户
RUN useradd --create-home --shell /bin/bash --uid 1000 app

# 设置工作目录
WORKDIR /app

# 复制应用代码
COPY --chown=app:app . .

# 切换到应用用户
USER app

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["gunicorn", "app.main:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--worker-connections", "1000", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--preload", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

### Docker Compose资源限制

```yaml
# docker-compose.prod.yml 资源优化
services:
  app:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
        monitor: 60s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s
```

## 网络优化

### Nginx优化配置

```nginx
# nginx/nginx.conf 性能优化
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    # 基础优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 100;
    
    # 压缩配置
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
    
    # 缓存配置
    open_file_cache max=1000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;
    
    # 缓冲区配置
    client_body_buffer_size 128k;
    client_max_body_size 10m;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 4k;
    output_buffers 1 32k;
    postpone_output 1460;
    
    # 代理缓冲区
    proxy_buffering on;
    proxy_buffer_size 128k;
    proxy_buffers 4 256k;
    proxy_busy_buffers_size 256k;
    
    # 上游配置
    upstream app {
        least_conn;
        server app:8000 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }
    
    # 速率限制
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;
    limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:10m;
    
    server {
        listen 443 ssl http2;
        server_name yourdomain.com;
        
        # SSL优化
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        ssl_buffer_size 8k;
        
        # 连接限制
        limit_conn conn_limit_per_ip 20;
        
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://app;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
        }
    }
}
```

## 监控和调优

### 性能监控脚本

```bash
#!/bin/bash
# performance_monitor.sh

# 应用性能监控
monitor_app_performance() {
    echo "=== Application Performance ==="
    
    # API响应时间
    curl -w "@curl-format.txt" -o /dev/null -s "https://yourdomain.com/health"
    
    # 数据库连接数
    docker-compose -f docker-compose.prod.yml exec -T db psql -U bountygo -c "
        SELECT count(*) as active_connections 
        FROM pg_stat_activity 
        WHERE state = 'active';
    "
    
    # Redis内存使用
    docker-compose -f docker-compose.prod.yml exec -T redis redis-cli info memory | grep used_memory_human
    
    # 应用内存使用
    docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}"
}

# 系统资源监控
monitor_system_resources() {
    echo "=== System Resources ==="
    
    # CPU使用率
    top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4}'
    
    # 内存使用率
    free | grep Mem | awk '{printf("%.2f%%\n", ($3/$2) * 100.0)}'
    
    # 磁盘使用率
    df -h / | awk 'NR==2{print $5}'
    
    # 网络连接数
    ss -s
}

# 数据库性能监控
monitor_database_performance() {
    echo "=== Database Performance ==="
    
    # 慢查询
    docker-compose -f docker-compose.prod.yml exec -T db psql -U bountygo -c "
        SELECT query, mean_time, calls 
        FROM pg_stat_statements 
        ORDER BY mean_time DESC 
        LIMIT 10;
    "
    
    # 数据库大小
    docker-compose -f docker-compose.prod.yml exec -T db psql -U bountygo -c "
        SELECT pg_size_pretty(pg_database_size('bountygo'));
    "
    
    # 表大小
    docker-compose -f docker-compose.prod.yml exec -T db psql -U bountygo -c "
        SELECT schemaname,tablename,
               pg_size_pretty(size) as size,
               pg_size_pretty(total_size) as total_size
        FROM (
            SELECT schemaname,tablename,
                   pg_relation_size(schemaname||'.'||tablename) as size,
                   pg_total_relation_size(schemaname||'.'||tablename) as total_size
            FROM pg_tables
            WHERE schemaname = 'public'
        ) t
        ORDER BY total_size DESC;
    "
}

# 主函数
main() {
    echo "BountyGo Performance Monitor - $(date)"
    echo "========================================"
    
    monitor_app_performance
    echo
    monitor_system_resources
    echo
    monitor_database_performance
    
    echo "========================================"
}

main
```

### 性能调优建议

```bash
# 创建调优脚本
cat > tune_performance.sh << 'EOF'
#!/bin/bash

# 1. 数据库调优
echo "Tuning database..."
docker-compose -f docker-compose.prod.yml exec -T db psql -U bountygo -c "
    -- 更新统计信息
    ANALYZE;
    
    -- 重建索引
    REINDEX DATABASE bountygo;
    
    -- 清理死元组
    VACUUM ANALYZE;
"

# 2. Redis调优
echo "Tuning Redis..."
docker-compose -f docker-compose.prod.yml exec -T redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
docker-compose -f docker-compose.prod.yml exec -T redis redis-cli CONFIG SET save "900 1 300 10 60 10000"

# 3. 清理Docker资源
echo "Cleaning Docker resources..."
docker system prune -f
docker volume prune -f

# 4. 重启服务以应用优化
echo "Restarting services..."
docker-compose -f docker-compose.prod.yml restart

echo "Performance tuning completed!"
EOF

chmod +x tune_performance.sh
```

### 自动化性能报告

```python
# scripts/performance_report.py
import asyncio
import aiohttp
import time
import json
from datetime import datetime

async def generate_performance_report():
    """生成性能报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "api_performance": await test_api_performance(),
        "database_metrics": await get_database_metrics(),
        "redis_metrics": await get_redis_metrics(),
        "system_metrics": await get_system_metrics()
    }
    
    # 保存报告
    with open(f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    return report

async def test_api_performance():
    """测试API性能"""
    endpoints = [
        "/health",
        "/api/v1/users/me",
        "/api/v1/tasks",
    ]
    
    results = {}
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            start_time = time.time()
            try:
                async with session.get(f"https://yourdomain.com{endpoint}") as response:
                    response_time = time.time() - start_time
                    results[endpoint] = {
                        "status_code": response.status,
                        "response_time": response_time,
                        "success": response.status == 200
                    }
            except Exception as e:
                results[endpoint] = {
                    "error": str(e),
                    "success": False
                }
    
    return results

if __name__ == "__main__":
    asyncio.run(generate_performance_report())
```

---

**注意：**
1. 根据实际负载调整配置参数
2. 定期监控和调优性能
3. 在生产环境中逐步应用优化
4. 保持配置的可回滚性
5. 监控优化效果并持续改进