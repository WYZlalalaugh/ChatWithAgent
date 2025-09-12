# ChatAgent 快速开始指南

欢迎使用 ChatAgent！本指南将帮助您快速搭建和运行您的第一个智能聊天机器人。

## 📋 环境要求

### 基础环境
- **Python**: 3.8+ 
- **Node.js**: 16+ (用于前端)
- **Docker**: 20.10+ (推荐)
- **Git**: 2.0+

### 数据库
- **MySQL**: 8.0+ 或 **PostgreSQL**: 12+
- **Redis**: 6.0+
- **向量数据库**: Chroma/Qdrant/FAISS (可选)

## 🚀 快速部署 (Docker 方式)

### 1. 克隆项目

```bash
git clone https://github.com/chatagent/chatagent.git
cd chatagent
```

### 2. 配置环境变量

复制并编辑环境配置文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入必要的配置：

```env
# 基础配置
APP_NAME=ChatAgent
APP_ENV=development
SECRET_KEY=your-super-secret-key-here

# 数据库配置
DATABASE_URL=mysql://user:password@localhost:3306/chatagent
REDIS_URL=redis://localhost:6379/0

# LLM 配置 (至少配置一个)
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1

# 可选：其他 LLM 提供商
ANTHROPIC_API_KEY=your-anthropic-key
ZHIPU_API_KEY=your-zhipu-key

# 向量数据库配置 (可选)
VECTOR_STORE_TYPE=chroma
CHROMA_HOST=localhost
CHROMA_PORT=8000

# 安全配置
JWT_SECRET_KEY=your-jwt-secret-key
JWT_EXPIRE_HOURS=24

# 平台配置 (可选)
QQ_BOT_APP_ID=your-qq-app-id
QQ_BOT_TOKEN=your-qq-token
WECHAT_APP_ID=your-wechat-app-id
WECHAT_APP_SECRET=your-wechat-secret
```

### 3. 启动服务

使用 Docker Compose 一键启动所有服务：

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
docker-compose exec backend python -m alembic upgrade head

# 创建初始管理员用户 (可选)
docker-compose exec backend python scripts/create_admin.py
```

### 5. 访问系统

- **前端管理界面**: http://localhost:3000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

默认管理员账号：
- 用户名: `admin`
- 密码: `admin123`

## 🛠️ 本地开发部署

如果您想要进行开发或自定义，可以选择本地部署方式。

### 1. 后端设置

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux  
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export DATABASE_URL="mysql://user:password@localhost:3306/chatagent"
export REDIS_URL="redis://localhost:6379/0"
export OPENAI_API_KEY="your-openai-api-key"

# 运行数据库迁移
alembic upgrade head

# 启动后端服务
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 前端设置

```bash
# 新开终端，进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 3. 启动数据库服务

#### MySQL
```bash
# 使用 Docker 快速启动 MySQL
docker run -d \
  --name chatagent-mysql \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=chatagent \
  -p 3306:3306 \
  mysql:8.0
```

#### Redis
```bash
# 使用 Docker 快速启动 Redis
docker run -d \
  --name chatagent-redis \
  -p 6379:6379 \
  redis:7-alpine
```

## 🤖 创建您的第一个机器人

### 1. 登录系统

访问 http://localhost:3000，使用管理员账号登录。

### 2. 创建机器人

点击"机器人管理" → "创建机器人"，填写以下信息：

- **机器人名称**: "我的第一个机器人"
- **描述**: "这是一个测试机器人"
- **平台类型**: "Web"
- **LLM 配置**:
  - 提供商: OpenAI
  - 模型: gpt-3.5-turbo
  - 温度: 0.7
  - 系统提示: "你是一个友好的助手，能够回答各种问题。"

### 3. 启动机器人

创建完成后，点击"启动机器人"按钮。

### 4. 开始对话

进入"聊天"页面，选择您刚创建的机器人，开始对话！

## 🔌 API 快速使用

### 1. 获取访问令牌

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

保存返回的 `access_token`。

### 2. 创建机器人

```bash
curl -X POST "http://localhost:8000/api/v1/bots/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API机器人",
    "description": "通过API创建的机器人",
    "platform_type": "web",
    "platform_config": {
      "webhook_url": "https://your-domain.com/webhook"
    },
    "llm_config": {
      "provider": "openai",
      "model": "gpt-3.5-turbo",
      "temperature": 0.7
    }
  }'
```

### 3. 发送消息

```bash
curl -X POST "http://localhost:8000/api/v1/conversations/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bot_id": "YOUR_BOT_ID",
    "title": "API对话",
    "platform": "web"
  }'

# 在对话中发送消息
curl -X POST "http://localhost:8000/api/v1/conversations/CONVERSATION_ID/messages" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "你好，你能做什么？",
    "message_type": "text"
  }'
```

## 🧩 集成平台机器人

### QQ 机器人集成

1. **申请 QQ 机器人**
   - 访问 [QQ 开放平台](https://q.qq.com/)
   - 创建应用并获取 App ID 和 Token

2. **配置环境变量**
   ```env
   QQ_BOT_APP_ID=your-qq-app-id
   QQ_BOT_TOKEN=your-qq-token
   ```

3. **创建 QQ 机器人**
   ```json
   {
     "name": "QQ机器人",
     "platform_type": "qq",
     "platform_config": {
       "app_id": "your-qq-app-id",
       "token": "your-qq-token",
       "secret": "your-qq-secret"
     },
     "llm_config": {
       "provider": "openai",
       "model": "gpt-3.5-turbo"
     }
   }
   ```

### 微信机器人集成

1. **申请微信公众号**
   - 访问 [微信公众平台](https://mp.weixin.qq.com/)
   - 获取 AppID 和 AppSecret

2. **配置环境变量**
   ```env
   WECHAT_APP_ID=your-wechat-app-id
   WECHAT_APP_SECRET=your-wechat-secret
   ```

3. **创建微信机器人**
   ```json
   {
     "name": "微信机器人",
     "platform_type": "wechat",
     "platform_config": {
       "app_id": "your-wechat-app-id",
       "app_secret": "your-wechat-secret",
       "webhook_url": "https://your-domain.com/webhook/wechat"
     }
   }
   ```

## 📚 添加知识库

### 1. 创建知识库

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/bases" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "产品知识库",
    "description": "包含产品相关文档",
    "vector_store_type": "chroma",
    "embedding_model": "text-embedding-ada-002"
  }'
```

### 2. 上传文档

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge/bases/KB_ID/documents" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@document.pdf" \
  -F 'metadata={"title":"产品手册","version":"1.0"}'
```

### 3. 关联到机器人

在创建机器人时，添加知识库 ID：

```json
{
  "name": "知识库机器人",
  "knowledge_base_ids": ["KB_ID"],
  "llm_config": {
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "system_prompt": "你是一个产品助手，请基于知识库内容回答用户问题。"
  }
}
```

## 🔧 常用配置

### LLM 提供商配置

#### OpenAI
```json
{
  "provider": "openai",
  "model": "gpt-3.5-turbo",
  "api_key": "sk-your-key",
  "base_url": "https://api.openai.com/v1",
  "temperature": 0.7,
  "max_tokens": 2000
}
```

#### Azure OpenAI
```json
{
  "provider": "azure",
  "model": "gpt-35-turbo",
  "api_key": "your-azure-key",
  "base_url": "https://your-resource.openai.azure.com/",
  "api_version": "2023-12-01-preview"
}
```

#### Anthropic Claude
```json
{
  "provider": "anthropic",
  "model": "claude-3-sonnet-20240229",
  "api_key": "your-anthropic-key",
  "max_tokens": 4000
}
```

#### 本地 LLM (Ollama)
```json
{
  "provider": "ollama",
  "model": "llama2",
  "base_url": "http://localhost:11434"
}
```

### 向量数据库配置

#### Chroma
```env
VECTOR_STORE_TYPE=chroma
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

#### Qdrant
```env
VECTOR_STORE_TYPE=qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=your-api-key
```

#### Pinecone
```env
VECTOR_STORE_TYPE=pinecone
PINECONE_API_KEY=your-api-key
PINECONE_ENVIRONMENT=us-west1-gcp
```

## 🔍 故障排除

### 常见问题

#### 1. 数据库连接失败
```
错误: Could not connect to database
解决: 检查数据库是否启动，连接字符串是否正确
```

#### 2. Redis 连接失败
```
错误: Redis connection failed
解决: 确保 Redis 服务运行，检查 REDIS_URL 配置
```

#### 3. LLM API 调用失败
```
错误: OpenAI API error
解决: 检查 API 密钥是否正确，是否有足够的配额
```

#### 4. 机器人启动失败
```
错误: Bot failed to start
解决: 检查平台配置是否正确，API 密钥是否有效
```

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 查看实时日志
tail -f logs/app.log
```

### 健康检查

```bash
# 检查后端健康状态
curl http://localhost:8000/health

# 检查各个组件状态
curl http://localhost:8000/api/v1/monitoring/health
```

## 📈 性能优化

### 1. 数据库优化

```sql
-- 添加索引
CREATE INDEX idx_conversations_bot_id ON conversations(bot_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
```

### 2. Redis 缓存

```python
# 启用对话上下文缓存
CONVERSATION_CACHE_TTL = 3600  # 1小时

# 启用 LLM 响应缓存
LLM_RESPONSE_CACHE_TTL = 86400  # 24小时
```

### 3. 负载均衡

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    image: chatagent/backend
    deploy:
      replicas: 3
    depends_on:
      - database
      - redis
```

## 🔒 安全最佳实践

### 1. 环境变量安全

```bash
# 使用强密码
openssl rand -base64 32

# 设置文件权限
chmod 600 .env
```

### 2. API 安全

```python
# 启用 HTTPS
USE_TLS = True
TLS_CERT_PATH = "/path/to/cert.pem"
TLS_KEY_PATH = "/path/to/key.pem"

# 设置 CORS
ALLOWED_ORIGINS = ["https://your-domain.com"]

# 启用限流
RATE_LIMIT_PER_MINUTE = 100
```

### 3. 数据库安全

```sql
-- 创建专用数据库用户
CREATE USER 'chatagent'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON chatagent.* TO 'chatagent'@'localhost';
```

## 📱 移动端集成

### React Native 示例

```javascript
import { ChatAgentClient } from 'chatagent-react-native';

const client = new ChatAgentClient({
  baseURL: 'https://your-api-domain.com/api/v1',
  accessToken: 'your-access-token'
});

// 发送消息
const sendMessage = async (conversationId, content) => {
  try {
    const response = await client.conversations.sendMessage(
      conversationId,
      content
    );
    return response.botResponse.content;
  } catch (error) {
    console.error('发送消息失败:', error);
  }
};
```

### Flutter 示例

```dart
import 'package:chatagent_flutter/chatagent_flutter.dart';

final client = ChatAgentClient(
  baseUrl: 'https://your-api-domain.com/api/v1',
  accessToken: 'your-access-token',
);

// 发送消息
Future<String> sendMessage(String conversationId, String content) async {
  try {
    final response = await client.conversations.sendMessage(
      conversationId,
      content,
    );
    return response.botResponse.content;
  } catch (e) {
    print('发送消息失败: $e');
    return '';
  }
}
```

## 🎯 下一步

恭喜！您已经成功搭建了 ChatAgent 平台。接下来您可以：

1. **探索高级功能**
   - 配置多个 LLM 提供商
   - 设置知识库检索
   - 开发自定义插件

2. **集成更多平台**
   - 钉钉机器人
   - 飞书机器人
   - Telegram 机器人

3. **优化和监控**
   - 设置监控告警
   - 优化对话性能
   - 分析用户行为

4. **开发扩展**
   - 自定义适配器
   - 开发插件
   - 集成第三方服务

## 📖 相关文档

- [API 文档](./API.md)
- [插件开发指南](./plugin-development.md)
- [部署指南](./deployment.md)
- [故障排除](./troubleshooting.md)

## 💡 获取帮助

- [GitHub Issues](https://github.com/chatagent/chatagent/issues)
- [讨论社区](https://github.com/chatagent/chatagent/discussions)
- [官方文档](https://docs.chatagent.dev)

---

如果您在使用过程中遇到任何问题，欢迎提交 Issue 或参与社区讨论！