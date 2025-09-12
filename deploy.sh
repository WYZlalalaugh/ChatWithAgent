#!/bin/bash

# ChatAgent部署脚本
# 使用方法: ./deploy.sh [环境] [操作]
# 环境: dev|staging|prod
# 操作: up|down|restart|logs|status

set -e

# 默认配置
ENV=${1:-dev}
ACTION=${2:-up}
PROJECT_NAME="chatagent"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    log_success "依赖检查完成"
}

# 环境检查
check_environment() {
    log_info "检查环境配置..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            log_warning ".env文件不存在，正在从.env.example复制..."
            cp .env.example .env
            log_warning "请编辑.env文件并配置必要的环境变量"
        else
            log_error ".env文件和.env.example文件都不存在"
            exit 1
        fi
    fi
    
    # 检查关键环境变量
    source .env
    
    if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "your-super-secret-key-change-this-in-production" ]; then
        log_warning "请在.env文件中设置安全的SECRET_KEY"
    fi
    
    if [ -z "$JWT_SECRET" ] || [ "$JWT_SECRET" = "your-jwt-secret-key-change-this-in-production" ]; then
        log_warning "请在.env文件中设置安全的JWT_SECRET"
    fi
    
    log_success "环境配置检查完成"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    mkdir -p logs
    mkdir -p uploads
    mkdir -p data/mysql
    mkdir -p data/redis
    mkdir -p data/chroma
    mkdir -p monitoring/prometheus
    mkdir -p monitoring/grafana/dashboards
    mkdir -p monitoring/grafana/datasources
    mkdir -p nginx/ssl
    
    log_success "目录创建完成"
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    docker-compose build --no-cache
    
    log_success "镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    case $ENV in
        "dev")
            docker-compose up -d mysql redis backend frontend
            ;;
        "staging")
            docker-compose --profile vector-db up -d mysql redis backend frontend chroma
            ;;
        "prod")
            docker-compose --profile vector-db --profile monitoring up -d
            ;;
        *)
            log_error "未知环境: $ENV"
            exit 1
            ;;
    esac
    
    log_success "服务启动完成"
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    
    docker-compose down
    
    log_success "服务停止完成"
}

# 重启服务
restart_services() {
    log_info "重启服务..."
    
    stop_services
    start_services
    
    log_success "服务重启完成"
}

# 查看日志
show_logs() {
    log_info "显示服务日志..."
    
    docker-compose logs -f --tail=100
}

# 查看状态
show_status() {
    log_info "服务状态:"
    
    docker-compose ps
    
    echo ""
    log_info "健康检查:"
    
    # 检查后端健康状态
    if curl -f http://localhost:${BACKEND_PORT:-8000}/health &>/dev/null; then
        log_success "后端服务: 健康"
    else
        log_error "后端服务: 不健康"
    fi
    
    # 检查前端健康状态
    if curl -f http://localhost:${FRONTEND_PORT:-80}/health &>/dev/null; then
        log_success "前端服务: 健康"
    else
        log_error "前端服务: 不健康"
    fi
    
    # 检查数据库连接
    if docker-compose exec -T mysql mysqladmin ping -h localhost &>/dev/null; then
        log_success "MySQL数据库: 健康"
    else
        log_error "MySQL数据库: 不健康"
    fi
    
    # 检查Redis连接
    if docker-compose exec -T redis redis-cli ping &>/dev/null; then
        log_success "Redis缓存: 健康"
    else
        log_error "Redis缓存: 不健康"
    fi
}

# 数据库初始化
init_database() {
    log_info "初始化数据库..."
    
    # 等待MySQL启动
    log_info "等待MySQL启动..."
    while ! docker-compose exec -T mysql mysqladmin ping -h localhost &>/dev/null; do
        sleep 2
    done
    
    log_info "运行数据库迁移..."
    docker-compose exec backend python -m alembic upgrade head
    
    log_success "数据库初始化完成"
}

# 备份数据
backup_data() {
    log_info "备份数据..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # 备份MySQL数据
    docker-compose exec -T mysql mysqldump -u root -p$MYSQL_ROOT_PASSWORD $MYSQL_DATABASE > "$BACKUP_DIR/mysql_backup.sql"
    
    # 备份Redis数据
    docker-compose exec -T redis redis-cli --rdb - > "$BACKUP_DIR/redis_backup.rdb"
    
    # 备份上传文件
    cp -r uploads "$BACKUP_DIR/"
    
    # 备份日志
    cp -r logs "$BACKUP_DIR/"
    
    log_success "数据备份完成: $BACKUP_DIR"
}

# 恢复数据
restore_data() {
    BACKUP_DIR=$1
    
    if [ -z "$BACKUP_DIR" ]; then
        log_error "请指定备份目录"
        exit 1
    fi
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "备份目录不存在: $BACKUP_DIR"
        exit 1
    fi
    
    log_info "恢复数据从: $BACKUP_DIR"
    
    # 恢复MySQL数据
    if [ -f "$BACKUP_DIR/mysql_backup.sql" ]; then
        docker-compose exec -T mysql mysql -u root -p$MYSQL_ROOT_PASSWORD $MYSQL_DATABASE < "$BACKUP_DIR/mysql_backup.sql"
        log_success "MySQL数据恢复完成"
    fi
    
    # 恢复上传文件
    if [ -d "$BACKUP_DIR/uploads" ]; then
        cp -r "$BACKUP_DIR/uploads/"* uploads/
        log_success "上传文件恢复完成"
    fi
    
    log_success "数据恢复完成"
}

# 清理资源
cleanup() {
    log_info "清理Docker资源..."
    
    # 停止并删除容器
    docker-compose down -v
    
    # 删除未使用的镜像
    docker image prune -f
    
    # 删除未使用的卷
    docker volume prune -f
    
    log_success "资源清理完成"
}

# 更新服务
update_services() {
    log_info "更新服务..."
    
    # 拉取最新代码
    git pull
    
    # 重新构建镜像
    build_images
    
    # 重启服务
    restart_services
    
    log_success "服务更新完成"
}

# 主逻辑
main() {
    case $ACTION in
        "up")
            check_dependencies
            check_environment
            create_directories
            build_images
            start_services
            sleep 10
            init_database
            show_status
            ;;
        "down")
            stop_services
            ;;
        "restart")
            restart_services
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "status")
            show_status
            ;;
        "backup")
            backup_data
            ;;
        "restore")
            restore_data $3
            ;;
        "cleanup")
            cleanup
            ;;
        "update")
            update_services
            ;;
        "init-db")
            init_database
            ;;
        *)
            echo "使用方法: $0 [环境] [操作]"
            echo "环境: dev|staging|prod (默认: dev)"
            echo "操作: up|down|restart|logs|status|backup|restore|cleanup|update|init-db"
            exit 1
            ;;
    esac
}

# 执行主逻辑
main