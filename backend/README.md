# 聊天机器人平台后端

这是聊天机器人平台的后端服务，基于 FastAPI 构建。

## 目录结构

```
backend/
├── app/                    # 应用主体
│   ├── __init__.py
│   ├── main.py            # 应用入口
│   ├── config.py          # 配置管理
│   ├── api/               # API 路由
│   │   ├── __init__.py
│   │   ├── deps.py        # 依赖注入
│   │   ├── v1/            # API v1 版本
│   │   │   ├── __init__.py
│   │   │   ├── bots.py    # 机器人管理 API
│   │   │   ├── chat.py    # 对话 API
│   │   │   ├── models.py  # 模型管理 API
│   │   │   ├── knowledge.py # 知识库 API
│   │   │   ├── plugins.py # 插件管理 API
│   │   │   └── users.py   # 用户管理 API
│   │   └── websocket.py   # WebSocket 处理
│   ├── core/              # 核心功能
│   │   ├── __init__.py
│   │   ├── auth.py        # 认证授权
│   │   ├── security.py    # 安全模块
│   │   ├── database.py    # 数据库连接
│   │   ├── redis.py       # Redis 连接
│   │   ├── events.py      # 事件处理
│   │   └── exceptions.py  # 异常处理
│   ├── models/            # 数据模型
│   │   ├── __init__.py
│   │   ├── base.py        # 基础模型
│   │   ├── user.py        # 用户模型
│   │   ├── bot.py         # 机器人模型
│   │   ├── conversation.py # 对话模型
│   │   ├── message.py     # 消息模型
│   │   ├── knowledge.py   # 知识库模型
│   │   └── plugin.py      # 插件模型
│   ├── services/          # 业务服务
│   │   ├── __init__.py
│   │   ├── bot_service.py # 机器人服务
│   │   ├── chat_service.py # 对话服务
│   │   ├── model_service.py # 模型服务
│   │   ├── knowledge_service.py # 知识库服务
│   │   └── plugin_service.py # 插件服务
│   └── utils/             # 工具函数
│       ├── __init__.py
│       ├── logger.py      # 日志工具
│       ├── validators.py  # 验证器
│       └── helpers.py     # 助手函数
├── adapters/              # 平台适配器
│   ├── __init__.py
│   ├── base.py           # 基础适配器
│   ├── qq.py             # QQ 适配器
│   ├── wechat.py         # 微信适配器
│   ├── feishu.py         # 飞书适配器
│   └── dingtalk.py       # 钉钉适配器
├── agents/               # 智能体框架
│   ├── __init__.py
│   ├── react.py          # ReAct 框架
│   ├── memory.py         # 记忆模块
│   ├── tools.py          # 工具集
│   └── executor.py       # 执行器
├── knowledge/            # 知识库系统
│   ├── __init__.py
│   ├── processors/       # 处理器
│   │   ├── __init__.py
│   │   ├── text.py       # 文本处理
│   │   ├── image.py      # 图像处理
│   │   ├── audio.py      # 音频处理
│   │   └── video.py      # 视频处理
│   ├── vector_stores/    # 向量数据库
│   │   ├── __init__.py
│   │   ├── base.py       # 基础接口
│   │   ├── chroma.py     # Chroma 实现
│   │   ├── qdrant.py     # Qdrant 实现
│   │   └── faiss.py      # FAISS 实现
│   └── retrieval.py      # 检索引擎
├── plugins/              # 插件系统
│   ├── __init__.py
│   ├── manager.py        # 插件管理器
│   ├── loader.py         # 插件加载器
│   ├── base.py           # 插件基类
│   └── examples/         # 示例插件
└── tests/                # 测试用例
    ├── __init__.py
    ├── conftest.py       # 测试配置
    ├── test_api/         # API 测试
    ├── test_services/    # 服务测试
    └── test_adapters/    # 适配器测试
```

## 安装和运行

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 配置环境变量
```bash
cp ../.env.example .env
# 编辑 .env 文件，设置数据库连接等配置
```

3. 运行数据库迁移
```bash
alembic upgrade head
```

4. 启动开发服务器
```bash
python -m app.main
```

## API 文档

启动服务后访问 `http://localhost:8000/docs` 查看自动生成的 API 文档。