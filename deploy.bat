@echo off
REM ChatAgent Windows部署脚本
REM 使用方法: deploy.bat [环境] [操作]
REM 环境: dev|staging|prod
REM 操作: up|down|restart|logs|status

setlocal enabledelayedexpansion

REM 默认配置
set ENV=%1
if "%ENV%"=="" set ENV=dev

set ACTION=%2
if "%ACTION%"=="" set ACTION=up

set PROJECT_NAME=chatagent

REM 日志函数
call :log_info "ChatAgent部署脚本启动"

REM 检查依赖
call :check_dependencies
if errorlevel 1 exit /b 1

REM 检查环境
call :check_environment
if errorlevel 1 exit /b 1

REM 执行操作
if "%ACTION%"=="up" (
    call :deploy_up
) else if "%ACTION%"=="down" (
    call :deploy_down
) else if "%ACTION%"=="restart" (
    call :deploy_restart
) else if "%ACTION%"=="logs" (
    call :show_logs
) else if "%ACTION%"=="status" (
    call :show_status
) else if "%ACTION%"=="cleanup" (
    call :cleanup
) else if "%ACTION%"=="init-db" (
    call :init_database
) else (
    call :show_usage
    exit /b 1
)

call :log_info "操作完成"
goto :eof

REM ============================================================================
REM 函数定义
REM ============================================================================

:log_info
echo [INFO] %~1
goto :eof

:log_success
echo [SUCCESS] %~1
goto :eof

:log_warning
echo [WARNING] %~1
goto :eof

:log_error
echo [ERROR] %~1
goto :eof

:check_dependencies
call :log_info "检查依赖..."

docker --version >nul 2>&1
if errorlevel 1 (
    call :log_error "Docker未安装，请先安装Docker Desktop"
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    call :log_error "Docker Compose未安装，请先安装Docker Compose"
    exit /b 1
)

call :log_success "依赖检查完成"
goto :eof

:check_environment
call :log_info "检查环境配置..."

if not exist ".env" (
    if exist ".env.example" (
        call :log_warning ".env文件不存在，正在从.env.example复制..."
        copy ".env.example" ".env" >nul
        call :log_warning "请编辑.env文件并配置必要的环境变量"
    ) else (
        call :log_error ".env文件和.env.example文件都不存在"
        exit /b 1
    )
)

call :log_success "环境配置检查完成"
goto :eof

:create_directories
call :log_info "创建必要目录..."

if not exist "logs" mkdir logs
if not exist "uploads" mkdir uploads
if not exist "data\mysql" mkdir data\mysql
if not exist "data\redis" mkdir data\redis
if not exist "data\chroma" mkdir data\chroma
if not exist "monitoring\prometheus" mkdir monitoring\prometheus
if not exist "monitoring\grafana\dashboards" mkdir monitoring\grafana\dashboards
if not exist "monitoring\grafana\datasources" mkdir monitoring\grafana\datasources
if not exist "nginx\ssl" mkdir nginx\ssl

call :log_success "目录创建完成"
goto :eof

:build_images
call :log_info "构建Docker镜像..."

docker-compose build --no-cache
if errorlevel 1 (
    call :log_error "镜像构建失败"
    exit /b 1
)

call :log_success "镜像构建完成"
goto :eof

:start_services
call :log_info "启动服务..."

if "%ENV%"=="dev" (
    docker-compose up -d mysql redis backend frontend
) else if "%ENV%"=="staging" (
    docker-compose --profile vector-db up -d mysql redis backend frontend chroma
) else if "%ENV%"=="prod" (
    docker-compose --profile vector-db --profile monitoring up -d
) else (
    call :log_error "未知环境: %ENV%"
    exit /b 1
)

if errorlevel 1 (
    call :log_error "服务启动失败"
    exit /b 1
)

call :log_success "服务启动完成"
goto :eof

:deploy_up
call :create_directories
call :build_images
call :start_services

REM 等待服务启动
call :log_info "等待服务启动..."
timeout /t 10 /nobreak >nul

call :init_database
call :show_status
goto :eof

:deploy_down
call :log_info "停止服务..."

docker-compose down
if errorlevel 1 (
    call :log_error "服务停止失败"
    exit /b 1
)

call :log_success "服务停止完成"
goto :eof

:deploy_restart
call :log_info "重启服务..."

call :deploy_down
call :start_services
call :show_status
goto :eof

:show_logs
call :log_info "显示服务日志..."
docker-compose logs -f --tail=100
goto :eof

:show_status
call :log_info "服务状态:"
docker-compose ps

echo.
call :log_info "健康检查:"

REM 检查后端健康状态
curl -f http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    call :log_error "后端服务: 不健康"
) else (
    call :log_success "后端服务: 健康"
)

REM 检查前端健康状态
curl -f http://localhost:80/health >nul 2>&1
if errorlevel 1 (
    call :log_error "前端服务: 不健康"
) else (
    call :log_success "前端服务: 健康"
)

goto :eof

:init_database
call :log_info "初始化数据库..."

REM 等待MySQL启动
call :log_info "等待MySQL启动..."
:wait_mysql
docker-compose exec -T mysql mysqladmin ping -h localhost >nul 2>&1
if errorlevel 1 (
    timeout /t 2 /nobreak >nul
    goto wait_mysql
)

call :log_info "运行数据库迁移..."
docker-compose exec backend python -m alembic upgrade head
if errorlevel 1 (
    call :log_error "数据库迁移失败"
    exit /b 1
)

call :log_success "数据库初始化完成"
goto :eof

:cleanup
call :log_info "清理Docker资源..."

docker-compose down -v
docker image prune -f
docker volume prune -f

call :log_success "资源清理完成"
goto :eof

:show_usage
echo 使用方法: %0 [环境] [操作]
echo 环境: dev^|staging^|prod ^(默认: dev^)
echo 操作: up^|down^|restart^|logs^|status^|cleanup^|init-db
goto :eof