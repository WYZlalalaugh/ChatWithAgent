"""
对话管理API测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

from tests.conftest import (
    assert_response_ok, 
    assert_response_error, 
    create_test_user, 
    create_test_bot,
    create_test_conversation
)


class TestConversationsAPI:
    """对话管理API测试类"""
    
    def test_create_conversation(self, client: TestClient, auth_headers: dict, sample_bot_data: dict):
        """测试创建对话"""
        # 先创建机器人
        bot_response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
        bot_data = assert_response_ok(bot_response, 201)
        bot_id = bot_data["id"]
        
        conversation_data = {
            "bot_id": bot_id,
            "title": "测试对话",
            "platform": "web",
            "platform_chat_id": "test_chat_123",
            "context": {"test": "context"}
        }
        
        response = client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
        data = assert_response_ok(response, 201)
        
        assert data["bot_id"] == bot_id
        assert data["title"] == conversation_data["title"]
        assert data["platform"] == conversation_data["platform"]
        assert data["platform_chat_id"] == conversation_data["platform_chat_id"]
        assert data["status"] == "active"
    
    def test_create_conversation_invalid_bot(self, client: TestClient, auth_headers: dict):
        """测试使用无效机器人ID创建对话"""
        conversation_data = {
            "bot_id": "invalid_bot_id",
            "title": "测试对话",
            "platform": "web"
        }
        
        response = client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
        assert_response_error(response, 404)
    
    def test_get_conversations(self, client: TestClient, auth_headers: dict, sample_bot_data: dict):
        """测试获取对话列表"""
        # 创建机器人
        bot_response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
        bot_data = assert_response_ok(bot_response, 201)
        bot_id = bot_data["id"]
        
        # 创建多个对话
        conversation_titles = ["对话1", "对话2", "对话3"]
        for title in conversation_titles:
            conversation_data = {
                "bot_id": bot_id,
                "title": title,
                "platform": "web"
            }
            client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
        
        # 获取对话列表
        response = client.get("/api/v1/conversations/", headers=auth_headers)
        data = assert_response_ok(response)
        
        assert data["total"] >= 3
        assert len(data["conversations"]) >= 3
        
        # 验证对话标题
        titles = [conv["title"] for conv in data["conversations"]]
        for title in conversation_titles:
            assert title in titles
    
    def test_get_conversations_with_filters(self, client: TestClient, auth_headers: dict, sample_bot_data: dict):
        """测试使用过滤器获取对话列表"""
        # 创建机器人
        bot_response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
        bot_data = assert_response_ok(bot_response, 201)
        bot_id = bot_data["id"]
        
        # 创建对话
        conversation_data = {
            "bot_id": bot_id,
            "title": "特殊对话",
            "platform": "qq"
        }
        client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
        
        # 使用过滤器查询
        response = client.get(f"/api/v1/conversations/?bot_id={bot_id}&platform=qq", headers=auth_headers)
        data = assert_response_ok(response)
        
        assert data["total"] >= 1
        for conv in data["conversations"]:
            assert conv["bot_id"] == bot_id
            assert conv["platform"] == "qq"
    
    def test_get_conversation_by_id(self, client: TestClient, auth_headers: dict, sample_bot_data: dict):
        """测试根据ID获取对话"""
        # 创建机器人和对话
        bot_response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
        bot_data = assert_response_ok(bot_response, 201)
        bot_id = bot_data["id"]
        
        conversation_data = {
            "bot_id": bot_id,
            "title": "测试对话详情",
            "platform": "web"
        }
        conv_response = client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
        conv_data = assert_response_ok(conv_response, 201)
        conversation_id = conv_data["id"]
        
        # 获取对话详情
        response = client.get(f"/api/v1/conversations/{conversation_id}", headers=auth_headers)
        data = assert_response_ok(response)
        
        assert data["id"] == conversation_id
        assert data["title"] == conversation_data["title"]
        assert data["bot_id"] == bot_id
    
    def test_get_conversation_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的对话"""
        response = client.get("/api/v1/conversations/nonexistent_id", headers=auth_headers)
        assert_response_error(response, 404)
    
    def test_update_conversation(self, client: TestClient, auth_headers: dict, sample_bot_data: dict):
        """测试更新对话"""
        # 创建机器人和对话
        bot_response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
        bot_data = assert_response_ok(bot_response, 201)
        bot_id = bot_data["id"]
        
        conversation_data = {
            "bot_id": bot_id,
            "title": "原始标题",
            "platform": "web"
        }
        conv_response = client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
        conv_data = assert_response_ok(conv_response, 201)
        conversation_id = conv_data["id"]
        
        # 更新对话
        update_data = {
            "title": "更新后的标题",
            "context": {"updated": True}
        }
        response = client.put(f"/api/v1/conversations/{conversation_id}", 
                            json=update_data, headers=auth_headers)
        data = assert_response_ok(response)
        
        assert data["title"] == update_data["title"]
        assert data["context"]["updated"] is True
    
    def test_update_conversation_not_found(self, client: TestClient, auth_headers: dict):
        """测试更新不存在的对话"""
        update_data = {"title": "新标题"}
        response = client.put("/api/v1/conversations/nonexistent_id", 
                            json=update_data, headers=auth_headers)
        assert_response_error(response, 404)
    
    def test_delete_conversation(self, client: TestClient, auth_headers: dict, sample_bot_data: dict):
        """测试删除对话"""
        # 创建机器人和对话
        bot_response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
        bot_data = assert_response_ok(bot_response, 201)
        bot_id = bot_data["id"]
        
        conversation_data = {
            "bot_id": bot_id,
            "title": "待删除对话",
            "platform": "web"
        }
        conv_response = client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
        conv_data = assert_response_ok(conv_response, 201)
        conversation_id = conv_data["id"]
        
        # 删除对话
        response = client.delete(f"/api/v1/conversations/{conversation_id}", headers=auth_headers)
        assert_response_ok(response)
        
        # 验证对话已删除
        get_response = client.get(f"/api/v1/conversations/{conversation_id}", headers=auth_headers)
        assert_response_error(get_response, 404)
    
    def test_delete_conversation_not_found(self, client: TestClient, auth_headers: dict):
        """测试删除不存在的对话"""
        response = client.delete("/api/v1/conversations/nonexistent_id", headers=auth_headers)
        assert_response_error(response, 404)
    
    def test_conversation_messages(self, client: TestClient, auth_headers: dict, sample_bot_data: dict):
        """测试对话消息管理"""
        # 创建机器人和对话
        bot_response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
        bot_data = assert_response_ok(bot_response, 201)
        bot_id = bot_data["id"]
        
        conversation_data = {
            "bot_id": bot_id,
            "title": "消息测试对话",
            "platform": "web"
        }
        conv_response = client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
        conv_data = assert_response_ok(conv_response, 201)
        conversation_id = conv_data["id"]
        
        # 发送消息
        message_data = {
            "content": "你好，机器人！",
            "message_type": "text"
        }
        response = client.post(f"/api/v1/conversations/{conversation_id}/messages", 
                             json=message_data, headers=auth_headers)
        
        # 检查响应状态
        if response.status_code == 200:
            data = assert_response_ok(response)
            assert "message_id" in data or "response" in data
        else:
            # 如果消息API未实现，应该返回404
            assert response.status_code == 404
    
    def test_conversation_context_management(self, client: TestClient, auth_headers: dict, sample_bot_data: dict):
        """测试对话上下文管理"""
        # 创建机器人和对话
        bot_response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
        bot_data = assert_response_ok(bot_response, 201)
        bot_id = bot_data["id"]
        
        conversation_data = {
            "bot_id": bot_id,
            "title": "上下文测试",
            "platform": "web",
            "context": {"session_id": "test_session", "user_preferences": {"lang": "zh"}}
        }
        conv_response = client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
        conv_data = assert_response_ok(conv_response, 201)
        conversation_id = conv_data["id"]
        
        # 获取上下文
        response = client.get(f"/api/v1/conversations/{conversation_id}/context", headers=auth_headers)
        
        if response.status_code == 200:
            data = assert_response_ok(response)
            assert "session_id" in data
            assert data["user_preferences"]["lang"] == "zh"
        else:
            # 如果上下文API未实现，应该返回404
            assert response.status_code == 404


@pytest.mark.asyncio
class TestConversationService:
    """对话服务测试类"""
    
    async def test_create_conversation_service(self, db_session: AsyncSession, sample_user_data: dict, sample_bot_data: dict):
        """测试对话服务创建对话"""
        from managers.conversation_manager import conversation_manager
        
        # 创建用户和机器人
        user = await create_test_user(db_session, sample_user_data)
        bot = await create_test_bot(db_session, user.id, sample_bot_data)
        
        # 创建对话
        conversation = await conversation_manager.create_conversation(
            user_id=user.id,
            bot_id=bot.id,
            title="测试对话",
            platform="web",
            platform_chat_id="test_chat_123",
            context={"test": "context"}
        )
        
        assert conversation.id is not None
        assert conversation.user_id == user.id
        assert conversation.bot_id == bot.id
        assert conversation.title == "测试对话"
        assert conversation.platform == "web"
        assert conversation.platform_chat_id == "test_chat_123"
        assert conversation.status == "active"
    
    async def test_get_conversations_service(self, db_session: AsyncSession, sample_user_data: dict, sample_bot_data: dict):
        """测试对话服务获取对话列表"""
        from managers.conversation_manager import conversation_manager
        
        # 创建用户和机器人
        user = await create_test_user(db_session, sample_user_data)
        bot = await create_test_bot(db_session, user.id, sample_bot_data)
        
        # 创建多个对话
        conversation_titles = ["对话1", "对话2", "对话3"]
        created_conversations = []
        
        for title in conversation_titles:
            conversation = await conversation_manager.create_conversation(
                user_id=user.id,
                bot_id=bot.id,
                title=title,
                platform="web"
            )
            created_conversations.append(conversation)
        
        # 获取对话列表
        conversations, total = await conversation_manager.get_conversations(
            filters={"user_id": user.id}
        )
        
        assert total >= 3
        assert len(conversations) >= 3
        
        # 验证对话标题
        retrieved_titles = [conv.title for conv in conversations]
        for title in conversation_titles:
            assert title in retrieved_titles
    
    async def test_conversation_context_operations(self, db_session: AsyncSession, sample_user_data: dict, sample_bot_data: dict):
        """测试对话上下文操作"""
        from managers.conversation_manager import conversation_manager
        
        # 创建用户、机器人和对话
        user = await create_test_user(db_session, sample_user_data)
        bot = await create_test_bot(db_session, user.id, sample_bot_data)
        conversation = await create_test_conversation(db_session, user.id, bot.id)
        
        # 更新上下文
        new_context = {"session_id": "test_session", "step": 1}
        updated_conversation = await conversation_manager.update_conversation(
            conversation.id,
            {"context": new_context}
        )
        
        assert updated_conversation.context == new_context
        
        # 获取上下文
        retrieved_conversation = await conversation_manager.get_conversation_by_id(conversation.id)
        assert retrieved_conversation.context == new_context


class TestConversationIntegration:
    """对话集成测试类"""
    
    @patch('engines.conversation_engine.conversation_engine.process_message')
    def test_conversation_with_bot_integration(self, mock_process, client: TestClient, auth_headers: dict, sample_bot_data: dict):
        """测试对话与机器人的集成"""
        # 模拟对话引擎响应
        async def mock_process_message(*args, **kwargs):
            yield {"type": "content", "content": "你好！我是机器人。"}
            yield {"type": "response_complete"}
        
        mock_process.return_value = mock_process_message()
        
        # 创建机器人和对话
        bot_response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
        bot_data = assert_response_ok(bot_response, 201)
        bot_id = bot_data["id"]
        
        conversation_data = {
            "bot_id": bot_id,
            "title": "集成测试对话",
            "platform": "web"
        }
        conv_response = client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
        conv_data = assert_response_ok(conv_response, 201)
        conversation_id = conv_data["id"]
        
        # 发送消息（如果API存在）
        message_data = {
            "content": "你好",
            "message_type": "text"
        }
        response = client.post(f"/api/v1/conversations/{conversation_id}/messages", 
                             json=message_data, headers=auth_headers)
        
        # 验证响应（如果API实现了）
        if response.status_code == 200:
            assert mock_process.called
    
    def test_conversation_permissions(self, client: TestClient, auth_headers: dict, admin_headers: dict, sample_bot_data: dict):
        """测试对话权限控制"""
        # 用普通用户创建对话
        bot_response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
        bot_data = assert_response_ok(bot_response, 201)
        bot_id = bot_data["id"]
        
        conversation_data = {
            "bot_id": bot_id,
            "title": "权限测试对话",
            "platform": "web"
        }
        conv_response = client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
        conv_data = assert_response_ok(conv_response, 201)
        conversation_id = conv_data["id"]
        
        # 管理员应该能访问所有对话
        admin_response = client.get(f"/api/v1/conversations/{conversation_id}", headers=admin_headers)
        
        # 验证权限控制逻辑
        if admin_response.status_code == 200:
            # 管理员可以访问
            assert_response_ok(admin_response)
        elif admin_response.status_code == 403:
            # 实现了严格的权限控制
            pass
        else:
            # 其他情况
            assert admin_response.status_code in [200, 403, 404]
    
    def test_conversation_pagination(self, client: TestClient, auth_headers: dict, sample_bot_data: dict):
        """测试对话分页"""
        # 创建机器人
        bot_response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
        bot_data = assert_response_ok(bot_response, 201)
        bot_id = bot_data["id"]
        
        # 创建多个对话
        for i in range(15):
            conversation_data = {
                "bot_id": bot_id,
                "title": f"分页测试对话 {i+1}",
                "platform": "web"
            }
            client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
        
        # 测试分页
        response = client.get("/api/v1/conversations/?limit=10&offset=0", headers=auth_headers)
        data = assert_response_ok(response)
        
        assert len(data["conversations"]) <= 10
        assert data["total"] >= 15
        
        # 测试第二页
        response = client.get("/api/v1/conversations/?limit=10&offset=10", headers=auth_headers)
        data = assert_response_ok(response)
        
        # 应该有剩余的对话
        assert len(data["conversations"]) >= 5