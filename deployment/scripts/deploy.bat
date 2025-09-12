@echo off
setlocal enabledelayedexpansion

echo 🚀 开始部署 ChatBot 平台...

:: 检查 Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 未安装，请先安装 Docker Desktop
    pause
    exit /b 1
)

:: 检查 Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose 未安装，请先安装 Docker Compose
    pause
    exit /b 1
)

:: 创建必要的目录
echo 📁 创建数据目录...
if not exist "data" mkdir data
if not exist "data\mysql" mkdir data\mysql
if not exist "data\redis" mkdir data\redis
if not exist "data\qdrant" mkdir data\qdrant
if not exist "data\uploads" mkdir data\uploads
if not exist "data\logs" mkdir data\logs

:: 复制环境配置文件
if not exist ".env" (
    echo 📝 复制环境配置文件...
    copy .env.example .env
    echo ⚠️  请编辑 .env 文件设置必要的配置项
)

:: 构建镜像
echo 🔨 构建 Docker 镜像...
docker-compose build

:: 启动服务
echo 🎯 启动服务...
docker-compose up -d

:: 等待数据库启动
echo ⏳ 等待数据库启动...
timeout /t 30 /nobreak >nul

:: 检查服务状态
echo 📊 检查服务状态...
docker-compose ps

:: 显示访问信息
echo.
echo ✅ 部署完成！
echo.
echo 📱 Web 管理面板: http://localhost
echo 🔗 API 文档: http://localhost/api/docs
echo 📊 系统监控: docker-compose logs -f
echo.
echo 🔧 常用命令:
echo   启动服务: docker-compose up -d
echo   停止服务: docker-compose down
echo   查看日志: docker-compose logs -f [service_name]
echo   重启服务: docker-compose restart [service_name]
echo.
pause