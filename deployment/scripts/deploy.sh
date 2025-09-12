#!/bin/bash

# 部署脚本 - 用于生产环境部署

set -e

echo "🚀 开始部署 ChatBot 平台..."

# 检查 Docker 和 Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 创建必要的目录
echo "📁 创建数据目录..."
mkdir -p data/{mysql,redis,qdrant,uploads,logs}

# 复制环境配置文件
if [ ! -f ".env" ]; then
    echo "📝 复制环境配置文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件设置必要的配置项"
fi

# 构建镜像
echo "🔨 构建 Docker 镜像..."
docker-compose build

# 启动服务
echo "🎯 启动服务..."
docker-compose up -d

# 等待数据库启动
echo "⏳ 等待数据库启动..."
sleep 30

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose ps

# 显示访问信息
echo ""
echo "✅ 部署完成！"
echo ""
echo "📱 Web 管理面板: http://localhost"
echo "🔗 API 文档: http://localhost/api/docs"
echo "📊 系统监控: docker-compose logs -f"
echo ""
echo "🔧 常用命令:"
echo "  启动服务: docker-compose up -d"
echo "  停止服务: docker-compose down"
echo "  查看日志: docker-compose logs -f [service_name]"
echo "  重启服务: docker-compose restart [service_name]"