# BountyGo 部署配置指南

本文档详细说明了BountyGo后端应用的部署配置，包括Docker部署、生产环境优化和监控配置。

## 目录

- [部署概述](#部署概述)
- [Docker部署](#docker部署)
- [生产环境部署](#生产环境部署)
- [环境变量配置](#环境变量配置)
- [数据库配置](#数据库配置)
- [Redis配置](#redis配置)
- [Nginx配置](#nginx配置)
- [SSL/TLS配置](#ssltls配置)
- [监控和日志](#监控和日志)
- [性能优化](#性能优化)
- [安全配置](#安全配置)
- [备份和恢复](#备份和恢复)
- [故障排除](#故障排除)

## 部署概述

BountyGo支持多种部署方式：

1. **Docker Compose** - 推荐用于开发和小规模部署
2. **Kubernetes** - 推荐用于大规模生产部署
3. **传统服务器** - 直接在服务器上运行

### 系统要求

**最低要求：**
- CPU: 2核心
- 内存: 4GB RAM
- 存储: 20GB SSD
- 网络: 100Mbps

**推荐配置：**
- CPU: 4核心或更多
- 内存: 8GB RAM或更多
- 存储: 50GB SSD或更多
- 网络: 1Gbps

## Docker部署

### 开发环境部署

```bash
# 1. 克隆项目
git clone <repository-url>
cd bountygo-backend

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置必要的配置

# 3. 启动服务
docker-compose up -d

# 4. 查看服务状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f app
```

### 生产环境部署

```bash
# 1. 准备生产配置
cp .env.prod .env
# 编辑 .env 文件，设置生产环境配置

# 2. 构建生产镜像
docker-compose -f docker-compose.prod.yml build

# 3. 启动生产服务
docker-compose -f docker-compose.prod.yml up -d

# 4. 验证部署
docker-compose -f docker-compose.prod.yml ps
```

### Docker Compose配置详解

#### 开发环境 (docker-compose.yml)

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=true
      - ENVIRONMENT=development
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: bountygo
      POSTGRES_USER: bountygo
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

#### 生产环境 (docker-compose.prod.yml)

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    environment:
      - DEBUG=false
      - ENVIRONMENT=production
    depends_on:
      - db
      - redis
    restart: always
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: always

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: always
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: always
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru

volumes:
  postgres_data:
  redis_data:
```

## 生产环境部署

### 1. 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker和Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 重新登录以应用组权限
logout
```

### 2. 项目部署

```bash
# 创建部署目录
sudo mkdir -p /opt/bountygo
sudo chown $USER:$USER /opt/bountygo
cd /opt/bountygo

# 克隆项目
git clone <repository-url> .

# 配置环境变量
cp .env.prod .env
nano .env  # 编辑生产配置

# 创建必要目录
mkdir -p logs backups ssl

# 设置权限
chmod 600 .env
```

### 3. SSL证书配置

```bash
# 使用Let's Encrypt获取SSL证书
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot certonly --standalone -d yourdomain.com

# 复制证书到项目目录
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/
sudo chown $USER:$USER ssl/*
```

### 4. 启动服务

```bash
# 验证配置
python scripts/validate_config.py

# 启动生产服务
docker-compose -f docker-compose.prod.yml up -d

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

## 环境变量配置

### 生产环境必需配置

```bash
# 应用配置
APP_NAME=BountyGo Backend
DEBUG=false
ENVIRONMENT=production
VERSION=1.0.0

# 安全配置
SECRET_KEY=your-production-secret-key-at-least-32-characters-long-and-random
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# 数据库配置
DATABASE_URL=postgresql+asyncpg://bountygo:secure-password@db:5432/bountygo
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis配置
REDIS_URL=redis://redis:6379/0
REDIS_CACHE_TTL=1800

# CORS配置
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Google OAuth
GOOGLE_CLIENT_ID=your-production-google-client-id
GOOGLE_CLIENT_SECRET=your-production-google-client-secret

# PPIO模型配置
PPIO_API_KEY=sk_your_production_ppio_api_key
PPIO_BASE_URL=https://api.ppinfra.com/v3/openai
PPIO_MODEL_NAME=qwen/qwen3-coder-480b-a35b-instruct
PPIO_MAX_TOKENS=4000
PPIO_TEMPERATURE=0.1
PPIO_TIMEOUT=90
PPIO_MAX_RETRIES=3

# URL代理配置
CONTENT_EXTRACTION_TIMEOUT=60
MAX_CONTENT_LENGTH=100000
USE_PROXY=false
ENABLE_CONTENT_CACHE=true
CONTENT_CACHE_TTL=7200
USER_AGENT=BountyGo-URLAgent/1.0
MAX_REDIRECTS=5
VERIFY_SSL=true

# 速率限制
RATE_LIMIT_PER_MINUTE=100

# 数据库凭据（Docker使用）
POSTGRES_DB=bountygo
POSTGRES_USER=bountygo
POSTGRES_PASSWORD=your-secure-database-password
```

### 配置验证

```bash
# 运行配置验证
docker-compose -f docker-compose.prod.yml exec app python scripts/validate_config.py

# 检查环境变量
docker-compose -f docker-compose.prod.yml exec app env | grep -E "(PPIO|DATABASE|REDIS)"
```

## 数据库配置

### PostgreSQL优化

#### 1. 数据库配置文件 (postgresql.conf)

```ini
# 内存配置
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# 连接配置
max_connections = 100
listen_addresses = '*'

# 日志配置
log_statement = 'all'
log_duration = on
log_min_duration_statement = 1000

# 性能配置
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

#### 2. 数据库初始化

```bash
# 创建数据库和用户
docker-compose -f docker-compose.prod.yml exec db psql -U postgres -c "
CREATE DATABASE bountygo;
CREATE USER bountygo WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE bountygo TO bountygo;
"

# 运行数据库迁移
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

#### 3. 数据库备份

```bash
# 创建备份脚本
cat > backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/bountygo/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="bountygo_backup_${DATE}.sql"

docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U bountygo bountygo > "${BACKUP_DIR}/${BACKUP_FILE}"

# 压缩备份文件
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

# 删除7天前的备份
find "${BACKUP_DIR}" -name "bountygo_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
EOF

chmod +x backup_db.sh

# 设置定时备份
crontab -e
# 添加以下行（每天凌晨2点备份）
0 2 * * * /opt/bountygo/backup_db.sh
```

## Redis配置

### Redis优化配置

```bash
# Redis配置文件
cat > redis.conf << 'EOF'
# 内存配置
maxmemory 512mb
maxmemory-policy allkeys-lru

# 持久化配置
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec

# 网络配置
timeout 300
tcp-keepalive 300

# 日志配置
loglevel notice
logfile /var/log/redis/redis-server.log
EOF
```

### Redis监控

```bash
# 监控Redis状态
docker-compose -f docker-compose.prod.yml exec redis redis-cli info memory
docker-compose -f docker-compose.prod.yml exec redis redis-cli info stats
```

## Nginx配置

### 生产环境Nginx配置

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:8000;
    }

    # 速率限制
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;

    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # HTTPS重定向
    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # 主服务器配置
    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        # 静态文件
        location /static/ {
            alias /app/static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        # API路由
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # 认证路由（更严格的速率限制）
        location /api/v1/auth/ {
            limit_req zone=auth burst=10 nodelay;
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 健康检查
        location /health {
            proxy_pass http://app;
            access_log off;
        }

        # 文档
        location /docs {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 默认路由
        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## SSL/TLS配置

### 自动续期SSL证书

```bash
# 创建续期脚本
cat > renew_ssl.sh << 'EOF'
#!/bin/bash
# 停止nginx
docker-compose -f docker-compose.prod.yml stop nginx

# 续期证书
certbot renew --standalone

# 复制新证书
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/

# 重启nginx
docker-compose -f docker-compose.prod.yml start nginx

echo "SSL certificate renewed successfully"
EOF

chmod +x renew_ssl.sh

# 设置定时续期（每月1号凌晨3点）
crontab -e
# 添加以下行
0 3 1 * * /opt/bountygo/renew_ssl.sh
```

## 监控和日志

### 日志配置

```bash
# 创建日志目录
mkdir -p logs/{app,nginx,postgres,redis}

# 配置日志轮转
cat > /etc/logrotate.d/bountygo << 'EOF'
/opt/bountygo/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f /opt/bountygo/docker-compose.prod.yml restart app
    endscript
}
EOF
```

### 监控脚本

```bash
# 创建监控脚本
cat > monitor.sh << 'EOF'
#!/bin/bash
COMPOSE_FILE="docker-compose.prod.yml"

# 检查服务状态
check_service() {
    local service=$1
    local status=$(docker-compose -f $COMPOSE_FILE ps -q $service)
    
    if [ -z "$status" ]; then
        echo "❌ $service is not running"
        return 1
    else
        echo "✅ $service is running"
        return 0
    fi
}

# 检查所有服务
echo "🔍 Checking services..."
check_service app
check_service db
check_service redis
check_service nginx

# 检查磁盘空间
echo "💾 Disk usage:"
df -h /

# 检查内存使用
echo "🧠 Memory usage:"
free -h

# 检查Docker资源使用
echo "🐳 Docker resource usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
EOF

chmod +x monitor.sh
```

### 健康检查

```bash
# 创建健康检查脚本
cat > health_check.sh << 'EOF'
#!/bin/bash
API_URL="https://yourdomain.com"

# 检查API健康状态
health_status=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health")

if [ "$health_status" = "200" ]; then
    echo "✅ API health check passed"
else
    echo "❌ API health check failed (HTTP $health_status)"
    # 发送告警通知
    # curl -X POST -H 'Content-type: application/json' \
    #     --data '{"text":"BountyGo API health check failed"}' \
    #     YOUR_SLACK_WEBHOOK_URL
fi

# 检查数据库连接
db_status=$(docker-compose -f docker-compose.prod.yml exec -T app python -c "
from app.core.database import engine
try:
    engine.connect()
    print('OK')
except:
    print('FAIL')
")

if [ "$db_status" = "OK" ]; then
    echo "✅ Database connection OK"
else
    echo "❌ Database connection failed"
fi
EOF

chmod +x health_check.sh

# 设置定时健康检查（每5分钟）
crontab -e
# 添加以下行
*/5 * * * * /opt/bountygo/health_check.sh
```

## 性能优化

### 应用性能优化

1. **数据库连接池优化**
```bash
# 在.env中设置
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

2. **Redis缓存优化**
```bash
# 启用内容缓存
ENABLE_CONTENT_CACHE=true
CONTENT_CACHE_TTL=7200

# Redis内存优化
REDIS_CACHE_TTL=1800
```

3. **PPIO API优化**
```bash
# 增加超时时间
PPIO_TIMEOUT=90
PPIO_MAX_RETRIES=3

# 优化token使用
PPIO_MAX_TOKENS=4000
PPIO_TEMPERATURE=0.1
```

### 系统性能优化

```bash
# 系统内核参数优化
cat >> /etc/sysctl.conf << 'EOF'
# 网络优化
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_max_tw_buckets = 5000

# 内存优化
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
EOF

# 应用内核参数
sysctl -p
```

## 安全配置

### 防火墙配置

```bash
# 安装ufw
sudo apt install ufw

# 默认策略
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许SSH
sudo ufw allow ssh

# 允许HTTP和HTTPS
sudo ufw allow 80
sudo ufw allow 443

# 启用防火墙
sudo ufw enable

# 查看状态
sudo ufw status
```

### 安全加固

```bash
# 1. 创建专用用户
sudo useradd -r -s /bin/false bountygo
sudo usermod -aG docker bountygo

# 2. 设置文件权限
sudo chown -R bountygo:bountygo /opt/bountygo
sudo chmod 600 /opt/bountygo/.env
sudo chmod 700 /opt/bountygo/ssl

# 3. 禁用root SSH登录
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# 4. 安装fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## 备份和恢复

### 自动备份脚本

```bash
# 创建完整备份脚本
cat > full_backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/bountygo/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="bountygo_full_backup_${DATE}"

# 创建备份目录
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# 备份数据库
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U bountygo bountygo > "${BACKUP_DIR}/${BACKUP_NAME}/database.sql"

# 备份Redis数据
docker-compose -f docker-compose.prod.yml exec -T redis redis-cli BGSAVE
docker cp $(docker-compose -f docker-compose.prod.yml ps -q redis):/data/dump.rdb "${BACKUP_DIR}/${BACKUP_NAME}/redis.rdb"

# 备份配置文件
cp .env "${BACKUP_DIR}/${BACKUP_NAME}/"
cp -r ssl "${BACKUP_DIR}/${BACKUP_NAME}/"
cp -r nginx "${BACKUP_DIR}/${BACKUP_NAME}/"

# 备份应用日志
cp -r logs "${BACKUP_DIR}/${BACKUP_NAME}/"

# 压缩备份
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" -C "${BACKUP_DIR}" "${BACKUP_NAME}"
rm -rf "${BACKUP_DIR}/${BACKUP_NAME}"

# 删除30天前的备份
find "${BACKUP_DIR}" -name "bountygo_full_backup_*.tar.gz" -mtime +30 -delete

echo "Full backup completed: ${BACKUP_NAME}.tar.gz"
EOF

chmod +x full_backup.sh

# 设置定时完整备份（每周日凌晨1点）
crontab -e
# 添加以下行
0 1 * * 0 /opt/bountygo/full_backup.sh
```

### 恢复脚本

```bash
# 创建恢复脚本
cat > restore.sh << 'EOF'
#!/bin/bash
if [ $# -ne 1 ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    exit 1
fi

BACKUP_FILE=$1
RESTORE_DIR="/tmp/bountygo_restore"

# 解压备份文件
mkdir -p "$RESTORE_DIR"
tar -xzf "$BACKUP_FILE" -C "$RESTORE_DIR"

BACKUP_NAME=$(basename "$BACKUP_FILE" .tar.gz)
BACKUP_PATH="$RESTORE_DIR/$BACKUP_NAME"

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 恢复数据库
docker-compose -f docker-compose.prod.yml up -d db
sleep 10
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS bountygo;"
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres -c "CREATE DATABASE bountygo;"
docker-compose -f docker-compose.prod.yml exec -T db psql -U bountygo bountygo < "$BACKUP_PATH/database.sql"

# 恢复Redis数据
docker-compose -f docker-compose.prod.yml up -d redis
sleep 5
docker cp "$BACKUP_PATH/redis.rdb" $(docker-compose -f docker-compose.prod.yml ps -q redis):/data/dump.rdb
docker-compose -f docker-compose.prod.yml restart redis

# 恢复配置文件
cp "$BACKUP_PATH/.env" .
cp -r "$BACKUP_PATH/ssl" .
cp -r "$BACKUP_PATH/nginx" .

# 启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 清理临时文件
rm -rf "$RESTORE_DIR"

echo "Restore completed successfully"
EOF

chmod +x restore.sh
```

## 故障排除

### 常见问题和解决方案

#### 1. 服务启动失败

```bash
# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看详细日志
docker-compose -f docker-compose.prod.yml logs app

# 重启服务
docker-compose -f docker-compose.prod.yml restart app
```

#### 2. 数据库连接问题

```bash
# 检查数据库服务
docker-compose -f docker-compose.prod.yml exec db pg_isready -U bountygo

# 测试数据库连接
docker-compose -f docker-compose.prod.yml exec app python -c "
from app.core.database import engine
print('Database connection:', engine.connect())
"
```

#### 3. Redis连接问题

```bash
# 检查Redis服务
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# 查看Redis信息
docker-compose -f docker-compose.prod.yml exec redis redis-cli info
```

#### 4. SSL证书问题

```bash
# 检查证书有效期
openssl x509 -in ssl/fullchain.pem -text -noout | grep "Not After"

# 测试SSL配置
curl -I https://yourdomain.com

# 重新获取证书
./renew_ssl.sh
```

#### 5. 性能问题

```bash
# 查看资源使用情况
docker stats

# 查看应用性能
docker-compose -f docker-compose.prod.yml exec app python -c "
from app.core.config import settings
print(settings.get_config_summary())
"

# 优化数据库
docker-compose -f docker-compose.prod.yml exec db psql -U bountygo -c "VACUUM ANALYZE;"
```

### 紧急恢复流程

1. **服务完全宕机**
```bash
# 停止所有服务
docker-compose -f docker-compose.prod.yml down

# 清理Docker资源
docker system prune -f

# 重新启动
docker-compose -f docker-compose.prod.yml up -d
```

2. **数据库损坏**
```bash
# 从最新备份恢复
./restore.sh backups/bountygo_full_backup_YYYYMMDD_HHMMSS.tar.gz
```

3. **配置文件丢失**
```bash
# 从备份恢复配置
cp backups/latest/.env .
cp -r backups/latest/ssl .
cp -r backups/latest/nginx .
```

### 监控和告警

```bash
# 创建告警脚本
cat > alert.sh << 'EOF'
#!/bin/bash
SERVICE_NAME="BountyGo"
WEBHOOK_URL="YOUR_SLACK_WEBHOOK_URL"

send_alert() {
    local message=$1
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"🚨 $SERVICE_NAME Alert: $message\"}" \
        "$WEBHOOK_URL"
}

# 检查服务状态
if ! ./health_check.sh > /dev/null 2>&1; then
    send_alert "Service health check failed"
fi

# 检查磁盘空间
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    send_alert "Disk usage is ${DISK_USAGE}%"
fi

# 检查内存使用
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "$MEMORY_USAGE" -gt 90 ]; then
    send_alert "Memory usage is ${MEMORY_USAGE}%"
fi
EOF

chmod +x alert.sh

# 设置定时告警检查（每10分钟）
crontab -e
# 添加以下行
*/10 * * * * /opt/bountygo/alert.sh
```

---

**注意：** 
1. 请根据实际环境调整配置参数
2. 定期测试备份和恢复流程
3. 监控系统资源使用情况
4. 及时更新SSL证书和依赖包
5. 保持系统和Docker镜像的安全更新