# 开源大语言模型原生即时通信机器人开发平台

## 项目概述

这是一个功能完备的开源大语言模型原生即时通信机器人开发平台，提供开箱即用的 IM 机器人开发体验，支持 Agent、RAG、MCP 等多种 LLM 应用功能，适配国内主流即时通信平台。

## 核心特性

- 💬 **大模型对话与 Agent**：支持多种大模型、多轮对话、工具调用、多模态、流式输出
- 🤖 **多平台支持**：QQ、QQ频道、企业微信、个人微信、飞书、钉钉
- 🛠️ **高稳定性与功能完备**：访问控制、限速、敏感词过滤、多流水线配置
- 🧩 **插件扩展**：事件驱动、组件扩展、MCP 协议适配
- 😻 **Web 管理面板**：浏览器管理实例，动态配置，模型切换

## 技术栈

- **后端框架**：Python FastAPI
- **前端框架**：Vue 3 + TypeScript + Element Plus
- **数据库**：MySQL + Redis
- **消息队列**：Redis Pub/Sub
- **容器化**：Docker + Docker Compose
- **AI框架**：LangChain + Dify 适配器

## 项目结构

```
ChatAgent/
├── backend/                 # 后端服务
│   ├── app/                # 应用主体
│   │   ├── api/           # API 路由
│   │   ├── core/          # 核心功能
│   │   ├── models/        # 数据模型
│   │   ├── services/      # 业务服务
│   │   └── utils/         # 工具函数
│   ├── adapters/          # 平台适配器
│   ├── agents/            # 智能体框架
│   ├── knowledge/         # 知识库系统
│   ├── plugins/           # 插件系统
│   └── tests/             # 测试用例
├── frontend/               # 前端管理面板
│   ├── src/               # 源代码
│   │   ├── components/    # Vue 组件
│   │   ├── views/         # 页面视图
│   │   ├── stores/        # 状态管理
│   │   └── utils/         # 工具函数
│   └── public/            # 静态资源
├── deployment/            # 部署配置
│   ├── docker/           # Docker 文件
│   ├── nginx/            # Nginx 配置
│   └── scripts/          # 部署脚本
├── docs/                  # 项目文档
└── tests/                 # 集成测试
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- Redis 7+
- Docker & Docker Compose

### 本地开发

1. 克隆项目
```bash
git clone <repository-url>
cd ChatAgent
```

2. 后端设置
```bash
cd backend
pip install -r requirements.txt
python -m app.main
```

3. 前端设置
```bash
cd frontend
npm install
npm run dev
```

4. 使用 Docker Compose
```bash
docker-compose up -d
```

## 贡献指南

欢迎参与项目开发！请参考 [贡献指南](docs/CONTRIBUTING.md) 了解详细信息。

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。