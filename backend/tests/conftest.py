"""
测试配置和工具
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock

from app.database import Base, get_db_session
from app.main import app
from app.config import settings


# 测试数据库URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# 创建测试引擎
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True
)

# 创建测试会话
TestSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """测试数据库会话fixture"""
    # 创建所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 创建会话
    async with TestSessionLocal() as session:
        yield session
    
    # 清理数据库
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client(db_session: AsyncSession) -> Generator[TestClient, None, None]:
    """测试客户端fixture"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """临时目录fixture"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_redis():
    """Mock Redis客户端"""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = False
    mock_redis.expire.return_value = True
    mock_redis.keys.return_value = []
    mock_redis.zadd.return_value = 1
    mock_redis.zrange.return_value = []
    mock_redis.zcard.return_value = 0
    return mock_redis


@pytest.fixture
def mock_llm_client():
    """Mock LLM客户端"""
    mock_client = AsyncMock()
    mock_client.chat_completion.return_value = {
        "content": "Mock response",
        "model": "mock-model",
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15
        }
    }
    return mock_client


@pytest.fixture
def mock_vector_store():
    """Mock向量存储"""
    mock_store = AsyncMock()
    mock_store.add_documents.return_value = ["doc1", "doc2"]
    mock_store.similarity_search.return_value = [
        {
            "content": "Mock document content",
            "metadata": {"source": "test.txt"},
            "score": 0.95
        }
    ]
    mock_store.delete.return_value = True
    return mock_store


@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "username": "testuser",
        "nickname": "Test User",
        "email": "test@example.com",
        "password": "testpass123",
        "role": "user"
    }


@pytest.fixture
def sample_bot_data():
    """示例机器人数据"""
    return {
        "name": "Test Bot",
        "description": "A test bot",
        "platform_type": "web",
        "platform_config": {
            "webhook_url": "https://example.com/webhook"
        },
        "llm_config": {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 2000
        }
    }


@pytest.fixture
def sample_conversation_data():
    """示例对话数据"""
    return {
        "title": "Test Conversation",
        "platform": "web",
        "platform_chat_id": "test_chat_123",
        "context": {}
    }


@pytest.fixture
def sample_message_data():
    """示例消息数据"""
    return {
        "content": "Hello, this is a test message",
        "message_type": "text",
        "sender_type": "user",
        "metadata": {}
    }


@pytest.fixture
def auth_headers(client: TestClient, sample_user_data: dict):
    """认证头fixture"""
    # 创建测试用户并登录
    client.post("/api/v1/auth/register", json=sample_user_data)
    
    login_response = client.post("/api/v1/auth/login", json={
        "username": sample_user_data["username"],
        "password": sample_user_data["password"]
    })
    
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client: TestClient):
    """管理员认证头fixture"""
    admin_data = {
        "username": "admin",
        "nickname": "Admin User",
        "email": "admin@example.com",
        "password": "admin123",
        "role": "admin"
    }
    
    client.post("/api/v1/auth/register", json=admin_data)
    
    login_response = client.post("/api/v1/auth/login", json={
        "username": admin_data["username"],
        "password": admin_data["password"]
    })
    
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class AsyncMockManager:
    """异步Mock管理器"""
    
    def __init__(self):
        self.mocks = {}
    
    def add_mock(self, name: str, mock_obj):
        """添加Mock对象"""
        self.mocks[name] = mock_obj
    
    def get_mock(self, name: str):
        """获取Mock对象"""
        return self.mocks.get(name)
    
    async def reset_all(self):
        """重置所有Mock"""
        for mock_obj in self.mocks.values():
            if hasattr(mock_obj, 'reset_mock'):
                mock_obj.reset_mock()


@pytest.fixture
def mock_manager():
    """Mock管理器fixture"""
    return AsyncMockManager()


# 测试工具函数
def assert_response_ok(response, status_code=200):
    """断言响应成功"""
    assert response.status_code == status_code
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.text


def assert_response_error(response, status_code=400):
    """断言响应错误"""
    assert response.status_code == status_code
    if response.headers.get("content-type", "").startswith("application/json"):
        error_data = response.json()
        assert "detail" in error_data or "error" in error_data
        return error_data
    return response.text


async def create_test_user(db_session: AsyncSession, user_data: dict):
    """创建测试用户"""
    from app.models.database import User
    from security.password import hash_password
    
    user = User(
        username=user_data["username"],
        nickname=user_data["nickname"],
        email=user_data["email"],
        password_hash=hash_password(user_data["password"]),
        role=user_data.get("role", "user")
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


async def create_test_bot(db_session: AsyncSession, user_id: str, bot_data: dict):
    """创建测试机器人"""
    from app.models.database import Bot
    
    bot = Bot(
        name=bot_data["name"],
        description=bot_data["description"],
        user_id=user_id,
        platform_type=bot_data["platform_type"],
        platform_config=bot_data["platform_config"],
        llm_config=bot_data["llm_config"]
    )
    
    db_session.add(bot)
    await db_session.commit()
    await db_session.refresh(bot)
    
    return bot


async def create_test_conversation(db_session: AsyncSession, user_id: str, bot_id: str):
    """创建测试对话"""
    from app.models.database import Conversation
    from datetime import datetime
    
    conversation = Conversation(
        user_id=user_id,
        bot_id=bot_id,
        title="测试对话",
        platform="web",
        platform_chat_id="test_chat_123",
        status="active",
        context={"test": "context"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)
    
    return conversation


# Mock工具类
class MockLLMClient:
    """Mock LLM客户端"""
    
    def __init__(self):
        self.call_count = 0
        self.responses = [
            "这是一个测试响应。",
            "你好！我是测试机器人。",
            "我可以帮助你进行测试。"
        ]
    
    async def generate_response(self, messages, **kwargs):
        """生成响应"""
        self.call_count += 1
        response_index = (self.call_count - 1) % len(self.responses)
        return self.responses[response_index]
    
    async def generate_stream(self, messages, **kwargs):
        """生成流式响应"""
        self.call_count += 1
        response_index = (self.call_count - 1) % len(self.responses)
        response = self.responses[response_index]
        
        # 模拟流式输出
        for word in response.split():
            yield {"type": "content", "content": word + " "}
            await asyncio.sleep(0.01)  # 模拟延迟
        
        yield {"type": "response_complete"}


class MockPlatformAdapter:
    """Mock平台适配器"""
    
    def __init__(self):
        self.connected = False
        self.message_handler = None
        self.sent_messages = []
    
    async def initialize(self, config):
        """初始化"""
        return True
    
    async def start(self):
        """启动"""
        self.connected = True
    
    async def stop(self):
        """停止"""
        self.connected = False
    
    async def is_connected(self):
        """检查连接状态"""
        return self.connected
    
    async def send_message(self, user_id, content, message_type="text"):
        """发送消息"""
        message = {
            "user_id": user_id,
            "content": content,
            "message_type": message_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.sent_messages.append(message)
        return True
    
    async def set_message_handler(self, handler):
        """设置消息处理器"""
        self.message_handler = handler
    
    async def validate_config(self, config):
        """验证配置"""
        return True
    
    async def simulate_incoming_message(self, user_id, content):
        """模拟接收消息"""
        if self.message_handler:
            message = {
                "user_id": user_id,
                "content": content,
                "message_type": "text",
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.message_handler(message)


class MockVectorDatabase:
    """Mock向量数据库"""
    
    def __init__(self):
        self.documents = {}
        self.collections = {}
    
    async def create_collection(self, name, **kwargs):
        """创建集合"""
        self.collections[name] = {"documents": {}, "metadata": kwargs}
        return True
    
    async def add_documents(self, collection_name, documents, embeddings=None, metadatas=None):
        """添加文档"""
        if collection_name not in self.collections:
            await self.create_collection(collection_name)
        
        collection = self.collections[collection_name]
        
        for i, doc in enumerate(documents):
            doc_id = f"doc_{len(collection['documents'])}"
            collection["documents"][doc_id] = {
                "content": doc,
                "embedding": embeddings[i] if embeddings else [0.1] * 384,
                "metadata": metadatas[i] if metadatas else {}
            }
        
        return True
    
    async def search(self, collection_name, query_embedding, top_k=5, **kwargs):
        """搜索文档"""
        if collection_name not in self.collections:
            return []
        
        collection = self.collections[collection_name]
        documents = list(collection["documents"].values())
        
        # 简单模拟搜索结果
        results = []
        for i, doc in enumerate(documents[:top_k]):
            results.append({
                "content": doc["content"],
                "metadata": doc["metadata"], 
                "score": 0.9 - i * 0.1  # 模拟相似度分数
            })
        
        return results
    
    async def delete_collection(self, name):
        """删除集合"""
        if name in self.collections:
            del self.collections[name]
        return True


class MockRedisClient:
    """Mock Redis客户端"""
    
    def __init__(self):
        self.data = {}
        self.lists = {}
        self.sets = {}
    
    async def get(self, key):
        """获取值"""
        return self.data.get(key)
    
    async def set(self, key, value, ex=None):
        """设置值"""
        self.data[key] = value
        return True
    
    async def delete(self, key):
        """删除键"""
        if key in self.data:
            del self.data[key]
        return True
    
    async def lpush(self, key, *values):
        """列表左推"""
        if key not in self.lists:
            self.lists[key] = []
        
        for value in values:
            self.lists[key].insert(0, value)
        
        return len(self.lists[key])
    
    async def rpop(self, key):
        """列表右弹"""
        if key in self.lists and self.lists[key]:
            return self.lists[key].pop()
        return None
    
    async def sadd(self, key, *values):
        """集合添加"""
        if key not in self.sets:
            self.sets[key] = set()
        
        added = 0
        for value in values:
            if value not in self.sets[key]:
                self.sets[key].add(value)
                added += 1
        
        return added
    
    async def sismember(self, key, value):
        """检查集合成员"""
        return value in self.sets.get(key, set())


# 测试工具函数
def create_mock_file_upload(filename: str, content: bytes, content_type: str = "text/plain"):
    """创建Mock文件上传"""
    import io
    return (filename, io.BytesIO(content), content_type)


def generate_test_data(data_type: str, count: int = 1):
    """生成测试数据"""
    import random
    import string
    
    def random_string(length=10):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    if data_type == "users":
        return [
            {
                "username": f"user_{random_string(6)}",
                "email": f"test_{random_string(6)}@example.com",
                "password": "testpass123",
                "role": random.choice(["user", "admin"])
            }
            for _ in range(count)
        ]
    
    elif data_type == "bots":
        return [
            {
                "name": f"测试机器人_{random_string(6)}",
                "description": f"这是一个测试机器人 {random_string(10)}",
                "platform_type": random.choice(["web", "qq", "wechat", "feishu"]),
                "platform_config": {
                    "api_key": random_string(32),
                    "webhook_url": f"https://example.com/webhook/{random_string(10)}"
                },
                "llm_config": {
                    "provider": random.choice(["openai", "anthropic", "local"]),
                    "model": random.choice(["gpt-3.5-turbo", "gpt-4", "claude-3"]),
                    "api_key": random_string(32),
                    "temperature": random.uniform(0.1, 1.0)
                }
            }
            for _ in range(count)
        ]
    
    elif data_type == "conversations":
        return [
            {
                "title": f"测试对话_{random_string(6)}",
                "platform": random.choice(["web", "qq", "wechat"]),
                "platform_chat_id": f"chat_{random_string(10)}",
                "context": {
                    "session_id": random_string(16),
                    "user_preferences": {
                        "language": random.choice(["zh", "en"]),
                        "theme": random.choice(["light", "dark"])
                    }
                }
            }
            for _ in range(count)
        ]
    
    elif data_type == "messages":
        return [
            {
                "content": f"这是测试消息内容 {random_string(20)}",
                "message_type": random.choice(["text", "image", "audio"]),
                "sender_type": random.choice(["user", "bot"]),
                "metadata": {
                    "test_id": random_string(16),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            for _ in range(count)
        ]
    
    else:
        raise ValueError(f"Unsupported data type: {data_type}")


# 性能测试工具
class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.metrics = {}
    
    def start(self):
        """开始监控"""
        self.start_time = time.time()
    
    def stop(self):
        """停止监控"""
        self.end_time = time.time()
    
    def get_duration(self):
        """获取持续时间"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    def add_metric(self, name, value):
        """添加指标"""
        self.metrics[name] = value
    
    def get_metrics(self):
        """获取所有指标"""
        metrics = self.metrics.copy()
        duration = self.get_duration()
        if duration:
            metrics["duration"] = duration
        return metrics


# 数据库测试工具
class DatabaseTestHelper:
    """数据库测试助手"""
    
    @staticmethod
    async def cleanup_test_data(db_session: AsyncSession, table_models: list):
        """清理测试数据"""
        for model in table_models:
            try:
                # 删除测试相关的数据
                await db_session.execute(
                    model.__table__.delete().where(
                        model.name.like('%测试%') | 
                        model.name.like('%test%') |
                        model.name.like('%Test%')
                    )
                )
                await db_session.commit()
            except Exception as e:
                print(f"清理表 {model.__tablename__} 失败: {e}")
                await db_session.rollback()
    
    @staticmethod
    async def count_records(db_session: AsyncSession, model):
        """统计记录数"""
        result = await db_session.execute(
            select(func.count(model.id))
        )
        return result.scalar()
    
    @staticmethod
    async def verify_data_integrity(db_session: AsyncSession, model, record_id):
        """验证数据完整性"""
        result = await db_session.execute(
            select(model).where(model.id == record_id)
        )
        record = result.scalar_one_or_none()
        return record is not None


async def create_test_conversation(db_session: AsyncSession, user_id: str, bot_id: str, conversation_data: dict):
    """创建测试对话"""
    from app.models.database import Conversation
    
    conversation = Conversation(
        title=conversation_data["title"],
        user_id=user_id,
        bot_id=bot_id,
        platform=conversation_data["platform"],
        platform_chat_id=conversation_data["platform_chat_id"],
        context=conversation_data["context"]
    )
    
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)
    
    return conversation


async def create_test_message(db_session: AsyncSession, conversation_id: str, sender_id: str, message_data: dict):
    """创建测试消息"""
    from app.models.database import Message
    
    message = Message(
        conversation_id=conversation_id,
        content=message_data["content"],
        message_type=message_data["message_type"],
        sender_type=message_data["sender_type"],
        sender_id=sender_id,
        metadata=message_data["metadata"]
    )
    
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)
    
    return message


# 性能测试工具
class PerformanceTimer:
    """性能计时器"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """开始计时"""
        import time
        self.start_time = time.time()
    
    def stop(self):
        """停止计时"""
        import time
        self.end_time = time.time()
    
    @property
    def duration(self):
        """获取持续时间"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    def assert_faster_than(self, max_duration: float):
        """断言执行时间小于最大时长"""
        assert self.duration is not None, "Timer not stopped"
        assert self.duration < max_duration, f"Execution took {self.duration}s, expected < {max_duration}s"


@pytest.fixture
def performance_timer():
    """性能计时器fixture"""
    return PerformanceTimer()


# 并发测试工具
async def run_concurrent_tasks(tasks, max_concurrent=10):
    """运行并发任务"""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def limited_task(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(*[limited_task(task) for task in tasks])


# 数据生成工具
class TestDataFactory:
    """测试数据工厂"""
    
    @staticmethod
    def generate_user_data(username_suffix=""):
        """生成用户数据"""
        import uuid
        suffix = username_suffix or str(uuid.uuid4())[:8]
        return {
            "username": f"user_{suffix}",
            "nickname": f"User {suffix}",
            "email": f"user_{suffix}@example.com",
            "password": "testpass123",
            "role": "user"
        }
    
    @staticmethod
    def generate_bot_data(name_suffix=""):
        """生成机器人数据"""
        import uuid
        suffix = name_suffix or str(uuid.uuid4())[:8]
        return {
            "name": f"Bot {suffix}",
            "description": f"Test bot {suffix}",
            "platform_type": "web",
            "platform_config": {
                "webhook_url": f"https://example.com/webhook/{suffix}"
            },
            "llm_config": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 2000
            }
        }
    
    @staticmethod
    def generate_conversation_data(title_suffix=""):
        """生成对话数据"""
        import uuid
        suffix = title_suffix or str(uuid.uuid4())[:8]
        return {
            "title": f"Conversation {suffix}",
            "platform": "web",
            "platform_chat_id": f"chat_{suffix}",
            "context": {}
        }


@pytest.fixture
def test_data_factory():
    """测试数据工厂fixture"""
    return TestDataFactory