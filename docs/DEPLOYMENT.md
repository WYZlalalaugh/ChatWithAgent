# ChatAgent 部署指南

## 概述

ChatAgent 是一个开源的大语言模型原生即时通信机器人开发平台，支持多种部署方式。本文档提供了完整的部署指南。

## 系统要求

### 最低要求
- **CPU**: 2核心
- **内存**: 4GB RAM
- **存储**: 20GB 可用空间
- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Windows 10+ / macOS 10.15+

### 推荐配置
- **CPU**: 4核心或更多
- **内存**: 8GB RAM 或更多
- **存储**: 50GB SSD
- **网络**: 稳定的互联网连接

## 前置依赖

### Docker 和 Docker Compose
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# CentOS/RHEL
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Windows
# 下载并安装 Docker Desktop for Windows
# https://www.docker.com/products/docker-desktop

# macOS
# 下载并安装 Docker Desktop for Mac
# https://www.docker.com/products/docker-desktop
```

## 快速部署

### 1. 克隆项目
```bash
git clone https://github.com/your-org/chatagent.git
cd chatagent
```

### 2. 配置环境变量
```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件
nano .env  # 或使用其他编辑器
```

### 3. 一键部署
```bash
# Linux/macOS
chmod +x deploy.sh
./deploy.sh dev up

# Windows
deploy.bat dev up
```

## 详细部署步骤

### 1. 环境配置

编辑 `.env` 文件，配置以下关键参数：

```bash
# 应用配置
SECRET_KEY=your-super-secret-key-here
JWT_SECRET=your-jwt-secret-key-here

# 数据库配置
MYSQL_ROOT_PASSWORD=secure-root-password
MYSQL_PASSWORD=secure-user-password

# LLM API配置
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# 平台集成配置
QQ_APP_ID=your-qq-app-id
QQ_TOKEN=your-qq-token
WECHAT_APP_ID=your-wechat-app-id
```

### 2. 构建镜像

```bash
# 构建所有服务镜像
docker-compose build

# 或构建特定服务
docker-compose build backend
docker-compose build frontend
```

### 3. 启动服务

#### 开发环境
```bash
docker-compose up -d mysql redis backend frontend
```

#### 预发布环境
```bash
docker-compose --profile vector-db up -d mysql redis backend frontend chroma
```

#### 生产环境
```bash
docker-compose --profile vector-db --profile monitoring up -d
```

### 4. 初始化数据库
```bash
# 等待数据库启动
sleep 30

# 运行数据库迁移
docker-compose exec backend python -m alembic upgrade head
```

### 5. 验证部署
```bash
# 检查服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f

# 健康检查
curl http://localhost:8000/health
curl http://localhost:80/health
```

## 部署环境说明

### 开发环境 (dev)
- **服务**: MySQL, Redis, Backend, Frontend
- **用途**: 本地开发和测试
- **端口**: 
  - 前端: 80
  - 后端: 8000
  - MySQL: 3306
  - Redis: 6379

### 预发布环境 (staging)
- **服务**: MySQL, Redis, Backend, Frontend, Chroma
- **用途**: 预发布测试和集成测试
- **增加服务**:
  - Chroma 向量数据库: 8001

### 生产环境 (prod)
- **服务**: 全部服务 + 监控组件
- **用途**: 生产环境部署
- **增加服务**:
  - Nginx 负载均衡: 8080
  - Prometheus 监控: 9090
  - Grafana 仪表板: 3000

## 服务配置

### Backend 服务
- **镜像**: chatagent-backend
- **端口**: 8000
- **健康检查**: `/health`
- **日志**: `/app/logs`
- **上传**: `/app/uploads`

### Frontend 服务
- **镜像**: chatagent-frontend
- **端口**: 80
- **代理**: API请求转发到 Backend
- **静态文件**: Nginx 提供

### MySQL 数据库
- **镜像**: mysql:8.0
- **端口**: 3306
- **数据卷**: `mysql_data`
- **初始化**: `scripts/init.sql`

### Redis 缓存
- **镜像**: redis:7-alpine
- **端口**: 6379
- **数据卷**: `redis_data`
- **配置**: `redis.conf`

## 高级配置

### SSL/TLS 配置

1. 准备SSL证书：
```bash
mkdir -p nginx/ssl
# 将证书文件放入 nginx/ssl 目录
```

2. 配置 Nginx：
```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/nginx/ssl/your-cert.pem;
    ssl_certificate_key /etc/nginx/ssl/your-key.pem;
    # ... 其他SSL配置
}
```

### 负载均衡配置

```bash
# 启用 Nginx 负载均衡
docker-compose --profile nginx up -d nginx
```

### 监控配置

```bash
# 启用监控服务
docker-compose --profile monitoring up -d prometheus grafana
```

访问地址：
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin123)

### 数据备份

```bash
# 自动备份
./deploy.sh dev backup

# 手动备份 MySQL
docker-compose exec mysql mysqldump -u root -p chatagent > backup.sql

# 手动备份 Redis
docker-compose exec redis redis-cli --rdb backup.rdb
```

### 数据恢复

```bash
# 从备份恢复
./deploy.sh dev restore backups/20231201_120000

# 手动恢复 MySQL
docker-compose exec -T mysql mysql -u root -p chatagent < backup.sql
```

## 故障排除

### 常见问题

#### 1. 服务启动失败
```bash
# 查看详细日志
docker-compose logs [service-name]

# 检查资源使用
docker stats

# 重启服务
docker-compose restart [service-name]
```

#### 2. 数据库连接失败
```bash
# 检查数据库状态
docker-compose exec mysql mysqladmin ping

# 查看数据库日志
docker-compose logs mysql

# 重置数据库
docker-compose down
docker volume rm chatagent_mysql_data
docker-compose up -d mysql
```

#### 3. 前端无法访问后端
```bash
# 检查网络连接
docker network ls
docker network inspect chatagent_chatagent-network

# 检查端口映射
docker-compose ps
```

#### 4. 内存不足
```bash
# 清理无用资源
docker system prune -a

# 调整服务资源限制
# 在 docker-compose.yml 中添加：
deploy:
  resources:
    limits:
      memory: 512M
```

### 性能优化

#### 1. 数据库优化
```sql
-- 增加缓冲池大小
SET GLOBAL innodb_buffer_pool_size = 1073741824; -- 1GB

-- 优化查询缓存
SET GLOBAL query_cache_size = 134217728; -- 128MB
```

#### 2. Redis 优化
```conf
# redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
```

#### 3. 应用优化
```bash
# 调整工作进程数
# 在 backend/Dockerfile 中:
CMD ["gunicorn", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "main:app"]
```

## 安全建议

### 1. 生产环境安全
- 更改所有默认密码
- 使用强密码和密钥
- 启用防火墙规则
- 定期更新系统和依赖

### 2. 网络安全
- 使用 HTTPS
- 配置适当的 CORS 策略
- 启用速率限制
- 使用 WAF（Web应用防火墙）

### 3. 数据安全
- 定期备份数据
- 加密敏感配置
- 启用访问日志
- 监控异常活动

## 更新和维护

### 1. 应用更新
```bash
# 拉取最新代码
git pull

# 重新构建并部署
./deploy.sh prod update
```

### 2. 系统维护
```bash
# 清理资源
./deploy.sh prod cleanup

# 查看系统状态
./deploy.sh prod status

# 重启所有服务
./deploy.sh prod restart
```

### 3. 数据库维护
```bash
# 数据库迁移
docker-compose exec backend python -m alembic upgrade head

# 数据库备份
docker-compose exec mysql mysqldump -u root -p chatagent > backup_$(date +%Y%m%d).sql
```

## 扩展部署

### 1. 多实例部署
```yaml
# docker-compose.scale.yml
services:
  backend:
    scale: 3
  
  frontend:
    scale: 2
```

### 2. 微服务拆分
- 将不同功能模块独立部署
- 使用容器编排平台（Kubernetes）
- 实现服务发现和负载均衡

### 3. 云平台部署
- AWS ECS/EKS
- Google Cloud Run/GKE
- Azure Container Instances/AKS
- 阿里云容器服务

## 支持和帮助

- **文档**: [项目Wiki](https://github.com/your-org/chatagent/wiki)
- **问题报告**: [GitHub Issues](https://github.com/your-org/chatagent/issues)
- **社区讨论**: [GitHub Discussions](https://github.com/your-org/chatagent/discussions)
- **邮件支持**: support@chatagent.com