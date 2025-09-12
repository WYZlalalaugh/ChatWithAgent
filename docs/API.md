# ChatAgent API 文档

## 概述

ChatAgent 是一个开源的大语言模型原生即时通信机器人开发平台，提供完整的 RESTful API 和 WebSocket 接口，支持多平台机器人开发、智能对话、知识库管理等功能。

## 基础信息

- **API 版本**: v1
- **基础 URL**: `http://localhost:8000/api/v1`
- **认证方式**: JWT Bearer Token
- **数据格式**: JSON
- **字符编码**: UTF-8

## 认证

### 用户注册

```http
POST /api/v1/auth/register
Content-Type: application/json

{
    "username": "user123",
    "nickname": "用户昵称",
    "email": "user@example.com",
    "password": "password123",
    "role": "user"
}
```

**响应示例:**
```json
{
    "success": true,
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user_info": {
        "id": "user_id_123",
        "username": "user123",
        "nickname": "用户昵称",
        "email": "user@example.com",
        "role": "user",
        "created_at": "2024-01-01T00:00:00Z"
    }
}
```

### 用户登录

```http
POST /api/v1/auth/login
Content-Type: application/json

{
    "username": "user123",
    "password": "password123"
}
```

**响应示例:**
```json
{
    "success": true,
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user_info": {
        "id": "user_id_123",
        "username": "user123",
        "nickname": "用户昵称",
        "email": "user@example.com",
        "role": "user"
    }
}
```

### 获取当前用户信息

```http
GET /api/v1/auth/me
Authorization: Bearer {access_token}
```

**响应示例:**
```json
{
    "id": "user_id_123",
    "username": "user123",
    "nickname": "用户昵称",
    "email": "user@example.com",
    "role": "user",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

## 机器人管理

### 创建机器人

```http
POST /api/v1/bots/
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "name": "我的聊天机器人",
    "description": "这是一个智能聊天机器人",
    "avatar_url": "https://example.com/avatar.jpg",
    "platform_type": "web",
    "platform_config": {
        "webhook_url": "https://your-domain.com/webhook",
        "api_key": "platform_api_key"
    },
    "llm_config": {
        "provider": "openai",
        "model": "gpt-3.5-turbo",
        "api_key": "your_openai_api_key",
        "temperature": 0.7,
        "max_tokens": 2000,
        "system_prompt": "你是一个有帮助的助手"
    },
    "knowledge_base_ids": ["kb_id_1", "kb_id_2"],
    "plugins": ["weather", "calculator"]
}
```

**响应示例:**
```json
{
    "id": "bot_id_123",
    "name": "我的聊天机器人",
    "description": "这是一个智能聊天机器人",
    "avatar_url": "https://example.com/avatar.jpg",
    "user_id": "user_id_123",
    "platform_type": "web",
    "is_active": false,
    "knowledge_base_ids": ["kb_id_1", "kb_id_2"],
    "plugins": ["weather", "calculator"],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

### 获取机器人列表

```http
GET /api/v1/bots/?limit=20&offset=0&search=关键词&platform_type=web&is_active=true
Authorization: Bearer {access_token}
```

**响应示例:**
```json
{
    "bots": [
        {
            "id": "bot_id_123",
            "name": "我的聊天机器人",
            "description": "这是一个智能聊天机器人",
            "avatar_url": "https://example.com/avatar.jpg",
            "platform_type": "web",
            "is_active": false,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    ],
    "total": 1,
    "limit": 20,
    "offset": 0
}
```

### 获取单个机器人详情

```http
GET /api/v1/bots/{bot_id}
Authorization: Bearer {access_token}
```

### 更新机器人

```http
PUT /api/v1/bots/{bot_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "name": "更新后的机器人名称",
    "description": "更新后的描述",
    "llm_config": {
        "provider": "openai",
        "model": "gpt-4",
        "temperature": 0.5
    }
}
```

### 删除机器人

```http
DELETE /api/v1/bots/{bot_id}
Authorization: Bearer {access_token}
```

### 启动机器人

```http
POST /api/v1/bots/{bot_id}/start
Authorization: Bearer {access_token}
```

**响应示例:**
```json
{
    "success": true,
    "message": "机器人启动成功",
    "bot_id": "bot_id_123"
}
```

### 停止机器人

```http
POST /api/v1/bots/{bot_id}/stop
Authorization: Bearer {access_token}
```

### 获取机器人状态

```http
GET /api/v1/bots/{bot_id}/status
Authorization: Bearer {access_token}
```

**响应示例:**
```json
{
    "bot_id": "bot_id_123",
    "is_running": true,
    "is_online": true,
    "start_time": "2024-01-01T00:00:00Z",
    "message_count": 150,
    "error_count": 2,
    "last_activity": "2024-01-01T12:30:00Z"
}
```

## 对话管理

### 创建对话

```http
POST /api/v1/conversations/
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "bot_id": "bot_id_123",
    "title": "与用户的对话",
    "platform": "web",
    "platform_chat_id": "chat_123",
    "context": {
        "user_preferences": {
            "language": "zh",
            "theme": "light"
        }
    }
}
```

**响应示例:**
```json
{
    "id": "conv_id_123",
    "user_id": "user_id_123",
    "bot_id": "bot_id_123",
    "title": "与用户的对话",
    "platform": "web",
    "platform_chat_id": "chat_123",
    "status": "active",
    "context": {
        "user_preferences": {
            "language": "zh",
            "theme": "light"
        }
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

### 获取对话列表

```http
GET /api/v1/conversations/?limit=20&offset=0&bot_id=bot_id_123&status=active
Authorization: Bearer {access_token}
```

**响应示例:**
```json
{
    "conversations": [
        {
            "id": "conv_id_123",
            "bot_id": "bot_id_123",
            "title": "与用户的对话",
            "platform": "web",
            "status": "active",
            "message_count": 25,
            "created_at": "2024-01-01T00:00:00Z",
            "last_message_at": "2024-01-01T12:30:00Z"
        }
    ],
    "total": 1,
    "limit": 20,
    "offset": 0
}
```

### 发送消息

```http
POST /api/v1/conversations/{conversation_id}/messages
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "content": "你好，你能做什么？",
    "message_type": "text",
    "metadata": {
        "client_id": "web_client_123"
    }
}
```

**响应示例:**
```json
{
    "user_message": {
        "id": "msg_id_456",
        "conversation_id": "conv_id_123",
        "content": "你好，你能做什么？",
        "message_type": "text",
        "sender_type": "user",
        "created_at": "2024-01-01T12:30:00Z"
    },
    "bot_response": {
        "id": "msg_id_789",
        "conversation_id": "conv_id_123",
        "content": "你好！我是一个智能助手，我可以帮助你回答问题、提供信息和进行对话。",
        "message_type": "text",
        "sender_type": "bot",
        "created_at": "2024-01-01T12:30:01Z"
    }
}
```

### 获取对话消息历史

```http
GET /api/v1/conversations/{conversation_id}/messages?limit=50&offset=0
Authorization: Bearer {access_token}
```

**响应示例:**
```json
{
    "messages": [
        {
            "id": "msg_id_456",
            "conversation_id": "conv_id_123",
            "content": "你好，你能做什么？",
            "message_type": "text",
            "sender_type": "user",
            "sender_id": "user_id_123",
            "created_at": "2024-01-01T12:30:00Z"
        },
        {
            "id": "msg_id_789",
            "conversation_id": "conv_id_123",
            "content": "你好！我是一个智能助手...",
            "message_type": "text",
            "sender_type": "bot",
            "sender_id": "bot_id_123",
            "created_at": "2024-01-01T12:30:01Z"
        }
    ],
    "total": 2,
    "limit": 50,
    "offset": 0
}
```

## WebSocket 实时通信

### 连接 WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/conversations/{conversation_id}?token={access_token}');

ws.onopen = function(event) {
    console.log('WebSocket 连接已建立');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('收到消息:', data);
};

ws.onerror = function(error) {
    console.error('WebSocket 错误:', error);
};
```

### 发送消息

```javascript
const message = {
    type: 'user_message',
    content: '你好，这是一条测试消息',
    message_type: 'text'
};

ws.send(JSON.stringify(message));
```

### 接收消息格式

```json
{
    "type": "bot_response",
    "message_id": "msg_id_789",
    "conversation_id": "conv_id_123",
    "content": "你好！这是机器人的回复",
    "message_type": "text",
    "timestamp": "2024-01-01T12:30:01Z"
}
```

### 流式响应

```json
{
    "type": "stream_chunk",
    "conversation_id": "conv_id_123",
    "chunk_id": 1,
    "content": "这是",
    "is_final": false
}
```

```json
{
    "type": "stream_complete",
    "conversation_id": "conv_id_123",
    "message_id": "msg_id_789",
    "full_content": "这是完整的回复内容"
}
```

## 多模态处理

### 处理文件

```http
POST /api/v1/multimodal/process
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

file: [二进制文件数据]
options: {
    "extract_text": true,
    "extract_images": false,
    "transcribe": true,
    "detect_faces": false,
    "resize": [800, 600],
    "compress": true
}
```

**响应示例:**
```json
{
    "success": true,
    "media_type": "image",
    "content": "图像中包含的文本内容...",
    "metadata": {
        "width": 1920,
        "height": 1080,
        "format": "JPEG",
        "size": 2048000,
        "faces_detected": 2
    },
    "processed_files": ["thumbnail.jpg", "processed.jpg"],
    "processing_time": 2.5
}
```

### 批量处理文件

```http
POST /api/v1/multimodal/batch-process
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

files: [多个文件]
options: {"extract_text": true}
```

### 获取支持的格式

```http
GET /api/v1/multimodal/formats
Authorization: Bearer {access_token}
```

**响应示例:**
```json
{
    "formats": {
        "image": ["jpg", "jpeg", "png", "gif", "bmp", "webp"],
        "audio": ["mp3", "wav", "flac", "m4a", "ogg"],
        "video": ["mp4", "avi", "mov", "mkv", "webm"],
        "document": ["pdf", "docx", "txt", "md", "rtf"],
        "spreadsheet": ["xlsx", "csv", "xls"]
    },
    "capabilities": {
        "text_extraction": true,
        "image_processing": true,
        "audio_transcription": true,
        "video_analysis": true,
        "face_detection": true,
        "object_detection": false
    }
}
```

## 知识库管理

### 创建知识库

```http
POST /api/v1/knowledge/bases
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "name": "产品知识库",
    "description": "包含产品相关的所有文档",
    "vector_store_type": "chroma",
    "embedding_model": "text-embedding-ada-002",
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "metadata": {
        "category": "product",
        "language": "zh"
    }
}
```

### 添加文档到知识库

```http
POST /api/v1/knowledge/bases/{base_id}/documents
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

file: [文档文件]
metadata: {
    "title": "产品使用手册",
    "author": "技术团队",
    "version": "1.0"
}
```

### 搜索知识库

```http
POST /api/v1/knowledge/bases/{base_id}/search
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "query": "如何配置机器人？",
    "top_k": 5,
    "score_threshold": 0.7,
    "filters": {
        "category": "configuration"
    }
}
```

**响应示例:**
```json
{
    "results": [
        {
            "content": "机器人配置步骤：1. 创建机器人...",
            "metadata": {
                "title": "配置指南",
                "page": 15,
                "source": "manual.pdf"
            },
            "score": 0.95
        }
    ],
    "total": 5,
    "query_time": 0.15
}
```

## 插件管理

### 获取可用插件

```http
GET /api/v1/plugins/available
Authorization: Bearer {access_token}
```

**响应示例:**
```json
{
    "plugins": [
        {
            "id": "weather",
            "name": "天气查询",
            "description": "获取实时天气信息",
            "version": "1.0.0",
            "author": "ChatAgent Team",
            "category": "utility",
            "config_schema": {
                "api_key": {
                    "type": "string",
                    "required": true,
                    "description": "天气API密钥"
                }
            }
        }
    ]
}
```

### 为机器人安装插件

```http
POST /api/v1/bots/{bot_id}/plugins/{plugin_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "config": {
        "api_key": "your_weather_api_key",
        "default_location": "北京"
    },
    "enabled": true
}
```

## 监控和日志

### 获取系统指标

```http
GET /api/v1/monitoring/metrics
Authorization: Bearer {access_token}
```

**响应示例:**
```json
{
    "cpu_usage": 45.2,
    "memory_usage": 68.5,
    "disk_usage": 30.1,
    "active_connections": 125,
    "total_requests": 15420,
    "error_rate": 0.02,
    "average_response_time": 150,
    "timestamp": "2024-01-01T12:30:00Z"
}
```

### 获取日志

```http
GET /api/v1/monitoring/logs?level=ERROR&start_time=2024-01-01T00:00:00Z&limit=100
Authorization: Bearer {access_token}
```

**响应示例:**
```json
{
    "logs": [
        {
            "timestamp": "2024-01-01T12:30:00Z",
            "level": "ERROR",
            "message": "Failed to process message",
            "module": "conversation_engine",
            "details": {
                "error_code": "PROCESSING_ERROR",
                "conversation_id": "conv_id_123"
            }
        }
    ],
    "total": 15,
    "limit": 100
}
```

## 错误处理

### 标准错误响应格式

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "请求参数验证失败",
        "details": {
            "field": "email",
            "reason": "无效的邮箱格式"
        }
    },
    "timestamp": "2024-01-01T12:30:00Z",
    "request_id": "req_123456789"
}
```

### 常见错误码

| 错误码 | HTTP状态码 | 描述 |
|--------|------------|------|
| `VALIDATION_ERROR` | 400 | 请求参数验证失败 |
| `UNAUTHORIZED` | 401 | 未授权访问 |
| `FORBIDDEN` | 403 | 禁止访问 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `DUPLICATE_RESOURCE` | 409 | 资源已存在 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求频率超限 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

## 限流和配额

### 请求限制

- 普通用户：100 请求/分钟
- 高级用户：1000 请求/分钟
- 企业用户：10000 请求/分钟

### 响应头

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## SDK 示例

### Python SDK

```python
from chatagent import ChatAgentClient

# 初始化客户端
client = ChatAgentClient(
    base_url="http://localhost:8000/api/v1",
    access_token="your_access_token"
)

# 创建机器人
bot = client.bots.create({
    "name": "我的机器人",
    "platform_type": "web",
    "llm_config": {
        "provider": "openai",
        "model": "gpt-3.5-turbo"
    }
})

# 创建对话
conversation = client.conversations.create({
    "bot_id": bot["id"],
    "title": "测试对话"
})

# 发送消息
response = client.conversations.send_message(
    conversation["id"],
    "你好，你能做什么？"
)

print(response["bot_response"]["content"])
```

### JavaScript SDK

```javascript
import { ChatAgentClient } from 'chatagent-js';

const client = new ChatAgentClient({
    baseURL: 'http://localhost:8000/api/v1',
    accessToken: 'your_access_token'
});

// 创建机器人
const bot = await client.bots.create({
    name: '我的机器人',
    platformType: 'web',
    llmConfig: {
        provider: 'openai',
        model: 'gpt-3.5-turbo'
    }
});

// 创建对话
const conversation = await client.conversations.create({
    botId: bot.id,
    title: '测试对话'
});

// 发送消息
const response = await client.conversations.sendMessage(
    conversation.id,
    '你好，你能做什么？'
);

console.log(response.botResponse.content);
```

## 最佳实践

### 1. 认证和安全

- 始终使用 HTTPS 在生产环境中
- 定期轮换 API 密钥
- 实施适当的访问控制
- 验证所有输入数据

### 2. 性能优化

- 使用分页来处理大数据集
- 实施客户端缓存
- 使用 WebSocket 进行实时通信
- 监控 API 响应时间

### 3. 错误处理

- 实施重试机制
- 记录错误以便调试
- 向用户提供有意义的错误消息
- 使用断路器模式防止级联故障

### 4. 机器人配置

- 为不同场景配置不同的系统提示
- 使用知识库提供特定领域的信息
- 合理设置 LLM 参数（温度、最大令牌数等）
- 定期监控机器人性能

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 基础 API 功能
- 机器人管理
- 对话系统
- 多模态处理

### v1.1.0 (计划中)
- 增强的插件系统
- 更多平台适配器
- 改进的监控功能
- 性能优化

## 支持

如果您在使用 API 时遇到问题，请：

1. 查看本文档的相关部分
2. 检查错误响应中的详细信息
3. 访问我们的 GitHub 仓库提交 Issue
4. 联系技术支持团队

---

更多详细信息和最新更新，请访问我们的 [GitHub 仓库](https://github.com/chatagent/chatagent)。