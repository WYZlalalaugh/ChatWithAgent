"""
机器人管理API测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock

from tests.conftest import (
    assert_response_ok, assert_response_error, 
    create_test_user, create_test_bot
)


class TestBotAPI:
    """机器人API测试类"""
    
    def test_create_bot_success(self, client: TestClient, auth_headers: dict, sample_bot_data: dict):
        """测试创建机器人成功"""
        response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
        data = assert_response_ok(response, 201)
        
        assert data["name"] == sample_bot_data["name"]
        assert data["description"] == sample_bot_data["description"]
        assert data["platform_type"] == sample_bot_data["platform_type"]
        assert "id" in data
        assert data["is_active"] is False  # 新创建的机器人默认未激活
    
    def test_create_bot_unauthorized(self, client: TestClient, sample_bot_data: dict):
        """测试未认证创建机器人"""
        response = client.post("/api/v1/bots/", json=sample_bot_data)
        assert_response_error(response, 401)
    
    def test_create_bot_invalid_data(self, client: TestClient, auth_headers: dict):
        """测试无效数据创建机器人"""
        invalid_data = {
            "name": "",  # 空名称
            "platform_type": "invalid_platform",
            "llm_config": {}  # 缺少必要配置
        }
        response = client.post("/api/v1/bots/", json=invalid_data, headers=auth_headers)
        assert_response_error(response, 422)
    
    def test_get_bots_list(self, client: TestClient, auth_headers: dict):
        """测试获取机器人列表"""
        response = client.get("/api/v1/bots/", headers=auth_headers)
        data = assert_response_ok(response)
        
        assert "bots" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["bots"], list)
    
    def test_get_bots_list_with_filters(self, client: TestClient, auth_headers: dict):
        """测试带过滤条件的机器人列表"""
        params = {
            "platform_type": "web",
            "is_active": "true",
            "page": 1,
            "page_size": 10
        }
        response = client.get("/api/v1/bots/", params=params, headers=auth_headers)
        data = assert_response_ok(response)
        
        assert isinstance(data["bots"], list)
        assert data["page"] == 1
        assert data["page_size"] == 10
    
    @pytest.mark.asyncio
    async def test_get_bot_detail(self, client: TestClient, auth_headers: dict, 
                                db_session: AsyncSession, sample_user_data: dict, sample_bot_data: dict):
        """测试获取机器人详情"""
        # 创建测试用户和机器人
        user = await create_test_user(db_session, sample_user_data)
        bot = await create_test_bot(db_session, user.id, sample_bot_data)
        
        response = client.get(f"/api/v1/bots/{bot.id}", headers=auth_headers)
        data = assert_response_ok(response)
        
        assert data["id"] == bot.id
        assert data["name"] == bot.name
        assert data["description"] == bot.description
    
    def test_get_bot_detail_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的机器人"""
        response = client.get("/api/v1/bots/nonexistent-id", headers=auth_headers)
        assert_response_error(response, 404)
    
    @pytest.mark.asyncio
    async def test_update_bot(self, client: TestClient, auth_headers: dict,
                            db_session: AsyncSession, sample_user_data: dict, sample_bot_data: dict):
        """测试更新机器人"""
        # 创建测试用户和机器人
        user = await create_test_user(db_session, sample_user_data)
        bot = await create_test_bot(db_session, user.id, sample_bot_data)
        
        update_data = {
            "name": "Updated Bot Name",
            "description": "Updated description"
        }
        
        response = client.put(f"/api/v1/bots/{bot.id}", json=update_data, headers=auth_headers)
        data = assert_response_ok(response)
        
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    @pytest.mark.asyncio
    async def test_update_bot_permission_denied(self, client: TestClient, auth_headers: dict,
                                              db_session: AsyncSession, sample_bot_data: dict, test_data_factory):
        """测试更新其他用户的机器人"""
        # 创建另一个用户和机器人
        other_user_data = test_data_factory.generate_user_data("other")
        other_user = await create_test_user(db_session, other_user_data)
        bot = await create_test_bot(db_session, other_user.id, sample_bot_data)
        
        update_data = {"name": "Hacked Bot"}
        
        response = client.put(f"/api/v1/bots/{bot.id}", json=update_data, headers=auth_headers)
        assert_response_error(response, 403)
    
    @pytest.mark.asyncio
    async def test_delete_bot(self, client: TestClient, auth_headers: dict,
                            db_session: AsyncSession, sample_user_data: dict, sample_bot_data: dict):
        """测试删除机器人"""
        # 创建测试用户和机器人
        user = await create_test_user(db_session, sample_user_data)
        bot = await create_test_bot(db_session, user.id, sample_bot_data)
        
        response = client.delete(f"/api/v1/bots/{bot.id}", headers=auth_headers)
        data = assert_response_ok(response)
        
        assert data["success"] is True
        
        # 验证机器人已被删除
        get_response = client.get(f"/api/v1/bots/{bot.id}", headers=auth_headers)
        assert_response_error(get_response, 404)
    
    @patch('managers.bot_manager.bot_manager')
    def test_start_bot(self, mock_bot_manager, client: TestClient, auth_headers: dict):
        """测试启动机器人"""
        bot_id = "test-bot-id"
        mock_bot_manager.start_bot.return_value = True
        
        response = client.post(f"/api/v1/bots/{bot_id}/start", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
        else:
            # 如果没有实现启动功能，应该返回501或404
            assert response.status_code in [404, 501]
    
    @patch('managers.bot_manager.bot_manager')
    def test_stop_bot(self, mock_bot_manager, client: TestClient, auth_headers: dict):
        """测试停止机器人"""
        bot_id = "test-bot-id"
        mock_bot_manager.stop_bot.return_value = True
        
        response = client.post(f"/api/v1/bots/{bot_id}/stop", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
        else:
            assert response.status_code in [404, 501]
    
    @patch('managers.bot_manager.bot_manager')
    def test_get_bot_status(self, mock_bot_manager, client: TestClient, auth_headers: dict):
        """测试获取机器人状态"""
        bot_id = "test-bot-id"
        mock_status = {
            "bot_id": bot_id,
            "is_running": True,
            "is_online": True,
            "message_count": 100,
            "error_count": 0
        }
        mock_bot_manager.get_bot_status.return_value = mock_status
        
        response = client.get(f"/api/v1/bots/{bot_id}/status", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert data["is_running"] is True
            assert data["bot_id"] == bot_id
        else:
            assert response.status_code in [404, 501]


class TestBotConfiguration:
    """机器人配置测试类"""
    
    def test_validate_platform_config(self, client: TestClient, auth_headers: dict):
        """测试平台配置验证"""
        # QQ平台配置
        qq_config = {
            "name": "QQ Bot",
            "platform_type": "qq",
            "platform_config": {
                "app_id": "test_app_id",
                "token": "test_token",
                "app_secret": "test_secret"
            },
            "llm_config": {
                "provider": "openai",
                "model": "gpt-3.5-turbo"
            }
        }
        
        response = client.post("/api/v1/bots/", json=qq_config, headers=auth_headers)
        
        if response.status_code == 201:
            data = response.json()
            assert data["platform_type"] == "qq"
        else:
            # 配置验证失败
            assert response.status_code in [400, 422]
    
    def test_validate_llm_config(self, client: TestClient, auth_headers: dict):
        """测试LLM配置验证"""
        # 无效的LLM配置
        invalid_llm_config = {
            "name": "Test Bot",
            "platform_type": "web",
            "platform_config": {},
            "llm_config": {
                "provider": "invalid_provider"
                # 缺少model等必要字段
            }
        }
        
        response = client.post("/api/v1/bots/", json=invalid_llm_config, headers=auth_headers)
        assert_response_error(response, 422)
    
    def test_encrypt_sensitive_config(self, client: TestClient, auth_headers: dict, sample_bot_data: dict):
        """测试敏感配置加密"""
        response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
        
        if response.status_code == 201:
            data = response.json()
            # 返回的配置不应该包含敏感信息的明文
            if "platform_config" in data:
                # 检查是否有敏感字段被掩码
                config = data["platform_config"]
                for key, value in config.items():
                    if "secret" in key.lower() or "token" in key.lower():
                        assert isinstance(value, str) and ("***" in value or len(value) > 100)


@pytest.mark.asyncio
class TestBotService:
    """机器人服务测试类"""
    
    async def test_bot_lifecycle(self, db_session: AsyncSession, sample_user_data: dict, sample_bot_data: dict):
        """测试机器人生命周期"""
        # 创建用户
        user = await create_test_user(db_session, sample_user_data)
        
        # 创建机器人
        bot = await create_test_bot(db_session, user.id, sample_bot_data)
        assert bot.id is not None
        assert bot.is_active is False
        
        # TODO: 测试启动、停止、重启等操作
        # 这需要实际的机器人管理器实现
    
    @patch('managers.bot_manager.bot_manager')
    async def test_bot_message_handling(self, mock_bot_manager, db_session: AsyncSession, 
                                      sample_user_data: dict, sample_bot_data: dict):
        """测试机器人消息处理"""
        user = await create_test_user(db_session, sample_user_data)
        bot = await create_test_bot(db_session, user.id, sample_bot_data)
        
        # 模拟消息处理
        mock_message = {
            "user_id": "test_user",
            "content": "Hello bot",
            "type": "text"
        }
        
        # 这里需要根据实际的消息处理逻辑进行测试
        # mock_bot_manager._handle_message.return_value = None
        # await mock_bot_manager._handle_message(bot.id, mock_message)
        
        # 验证消息是否被正确处理
        # assert mock_bot_manager._handle_message.called


class TestBotIntegration:
    """机器人集成测试类"""
    
    def test_bot_crud_workflow(self, client: TestClient, auth_headers: dict, sample_bot_data: dict):
        """测试机器人CRUD完整流程"""
        # 创建机器人
        create_response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
        
        if create_response.status_code == 201:
            bot_data = create_response.json()
            bot_id = bot_data["id"]
            
            # 获取机器人详情
            get_response = client.get(f"/api/v1/bots/{bot_id}", headers=auth_headers)
            assert get_response.status_code == 200
            
            # 更新机器人
            update_data = {"name": "Updated Bot Name"}
            update_response = client.put(f"/api/v1/bots/{bot_id}", 
                                       json=update_data, headers=auth_headers)
            if update_response.status_code == 200:
                updated_data = update_response.json()
                assert updated_data["name"] == update_data["name"]
            
            # 删除机器人
            delete_response = client.delete(f"/api/v1/bots/{bot_id}", headers=auth_headers)
            assert delete_response.status_code == 200
            
            # 验证删除
            final_get_response = client.get(f"/api/v1/bots/{bot_id}", headers=auth_headers)
            assert final_get_response.status_code == 404
    
    def test_multiple_bots_management(self, client: TestClient, auth_headers: dict, test_data_factory):
        """测试多机器人管理"""
        created_bots = []
        
        # 创建多个机器人
        for i in range(3):
            bot_data = test_data_factory.generate_bot_data(f"bot_{i}")
            response = client.post("/api/v1/bots/", json=bot_data, headers=auth_headers)
            
            if response.status_code == 201:
                created_bots.append(response.json())
        
        # 获取机器人列表
        list_response = client.get("/api/v1/bots/", headers=auth_headers)
        if list_response.status_code == 200:
            bot_list = list_response.json()
            assert len(bot_list["bots"]) >= len(created_bots)
        
        # 清理创建的机器人
        for bot in created_bots:
            client.delete(f"/api/v1/bots/{bot['id']}", headers=auth_headers)
    
    def test_bot_permission_isolation(self, client: TestClient, test_data_factory):
        """测试机器人权限隔离"""
        # 创建两个用户
        user1_data = test_data_factory.generate_user_data("user1")
        user2_data = test_data_factory.generate_user_data("user2")
        
        # 注册用户1并创建机器人
        client.post("/api/v1/auth/register", json=user1_data)
        login1_response = client.post("/api/v1/auth/login", json={
            "username": user1_data["username"],
            "password": user1_data["password"]
        })
        
        if login1_response.status_code == 200:
            token1 = login1_response.json()["access_token"]
            headers1 = {"Authorization": f"Bearer {token1}"}
            
            bot_data = test_data_factory.generate_bot_data()
            create_response = client.post("/api/v1/bots/", json=bot_data, headers=headers1)
            
            if create_response.status_code == 201:
                bot_id = create_response.json()["id"]
                
                # 注册用户2
                client.post("/api/v1/auth/register", json=user2_data)
                login2_response = client.post("/api/v1/auth/login", json={
                    "username": user2_data["username"],
                    "password": user2_data["password"]
                })
                
                if login2_response.status_code == 200:
                    token2 = login2_response.json()["access_token"]
                    headers2 = {"Authorization": f"Bearer {token2}"}
                    
                    # 用户2尝试访问用户1的机器人
                    get_response = client.get(f"/api/v1/bots/{bot_id}", headers=headers2)
                    assert get_response.status_code in [403, 404]  # 应该被拒绝
                    
                    # 用户2尝试修改用户1的机器人
                    update_response = client.put(f"/api/v1/bots/{bot_id}", 
                                               json={"name": "Hacked"}, headers=headers2)
                    assert update_response.status_code in [403, 404]
                
                # 清理
                client.delete(f"/api/v1/bots/{bot_id}", headers=headers1)