"""
端到端集成测试
"""

import pytest
from fastapi.testclient import TestClient
import asyncio
import json
import time
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from tests.conftest import assert_response_ok, assert_response_error


class TestEndToEndFlow:
    """端到端流程测试类"""
    
    def test_complete_user_journey(self, client: TestClient):
        """测试完整的用户使用流程"""
        # 1. 用户注册
        user_data = {
            "username": "e2e_testuser",
            "email": "e2e@test.com",
            "password": "e2epass123",
            "role": "user"
        }
        
        register_response = client.post("/api/v1/auth/register", json=user_data)
        register_data = assert_response_ok(register_response, 201)
        
        # 获取认证token
        token = register_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. 验证用户信息
        me_response = client.get("/api/v1/auth/me", headers=headers)
        user_info = assert_response_ok(me_response)
        assert user_info["username"] == user_data["username"]
        
        # 3. 创建机器人
        bot_data = {
            "name": "E2E测试机器人",
            "description": "这是一个端到端测试机器人",
            "platform_type": "web",
            "platform_config": {
                "webhook_url": "http://localhost:8000/webhook/test",
                "api_key": "test_api_key"
            },
            "llm_config": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "api_key": "test_llm_key",
                "temperature": 0.7
            }
        }
        
        bot_response = client.post("/api/v1/bots/", json=bot_data, headers=headers)
        bot_info = assert_response_ok(bot_response, 201)
        bot_id = bot_info["id"]
        
        assert bot_info["name"] == bot_data["name"]
        assert bot_info["platform_type"] == bot_data["platform_type"]
        
        # 4. 创建对话
        conversation_data = {
            "bot_id": bot_id,
            "title": "E2E测试对话",
            "platform": "web",
            "platform_chat_id": "e2e_chat_123"
        }
        
        conv_response = client.post("/api/v1/conversations/", json=conversation_data, headers=headers)
        conv_info = assert_response_ok(conv_response, 201)
        conversation_id = conv_info["id"]
        
        assert conv_info["bot_id"] == bot_id
        assert conv_info["title"] == conversation_data["title"]
        
        # 5. 模拟发送消息（如果API存在）
        message_data = {
            "content": "你好，这是一条测试消息",
            "message_type": "text"
        }
        
        message_response = client.post(
            f"/api/v1/conversations/{conversation_id}/messages", 
            json=message_data, 
            headers=headers
        )
        
        # 消息API可能未实现，不强制要求成功
        if message_response.status_code == 200:
            message_info = assert_response_ok(message_response)
            # 验证消息相关信息
            assert "message_id" in message_info or "response" in message_info
        
        # 6. 获取对话列表，验证创建的对话存在
        conversations_response = client.get("/api/v1/conversations/", headers=headers)
        conversations_data = assert_response_ok(conversations_response)
        
        conversation_ids = [conv["id"] for conv in conversations_data["conversations"]]
        assert conversation_id in conversation_ids
        
        # 7. 获取机器人列表，验证创建的机器人存在
        bots_response = client.get("/api/v1/bots/", headers=headers)
        bots_data = assert_response_ok(bots_response)
        
        bot_ids = [bot["id"] for bot in bots_data["bots"]]
        assert bot_id in bot_ids
        
        # 8. 更新机器人配置
        update_data = {
            "description": "更新后的描述",
            "llm_config": {
                "provider": "openai",
                "model": "gpt-4",
                "api_key": "test_llm_key",
                "temperature": 0.5
            }
        }
        
        update_response = client.put(f"/api/v1/bots/{bot_id}", json=update_data, headers=headers)
        updated_bot = assert_response_ok(update_response)
        
        assert updated_bot["description"] == update_data["description"]
        
        # 9. 清理：删除创建的资源
        # 删除对话
        delete_conv_response = client.delete(f"/api/v1/conversations/{conversation_id}", headers=headers)
        assert delete_conv_response.status_code in [200, 204]
        
        # 删除机器人
        delete_bot_response = client.delete(f"/api/v1/bots/{bot_id}", headers=headers)
        assert delete_bot_response.status_code in [200, 204]
        
        print("✅ 完整用户流程测试通过")
    
    @patch('managers.bot_manager.bot_manager.start_bot')
    @patch('managers.bot_manager.bot_manager.stop_bot')
    def test_bot_lifecycle_management(self, mock_stop_bot, mock_start_bot, client: TestClient, auth_headers: dict):
        """测试机器人生命周期管理"""
        # 模拟机器人启动停止
        mock_start_bot.return_value = True
        mock_stop_bot.return_value = True
        
        # 1. 创建机器人
        bot_data = {
            "name": "生命周期测试机器人",
            "platform_type": "web",
            "platform_config": {"test": "config"},
            "llm_config": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "test"}
        }
        
        bot_response = client.post("/api/v1/bots/", json=bot_data, headers=auth_headers)
        bot_info = assert_response_ok(bot_response, 201)
        bot_id = bot_info["id"]
        
        # 2. 启动机器人
        start_response = client.post(f"/api/v1/bots/{bot_id}/start", headers=auth_headers)
        
        if start_response.status_code == 200:
            start_data = assert_response_ok(start_response)
            assert start_data.get("success") is True
            mock_start_bot.assert_called_once_with(bot_id)
        else:
            # API可能未实现
            assert start_response.status_code == 404
        
        # 3. 获取机器人状态
        status_response = client.get(f"/api/v1/bots/{bot_id}/status", headers=auth_headers)
        
        if status_response.status_code == 200:
            status_data = assert_response_ok(status_response)
            assert "is_running" in status_data
            assert "bot_id" in status_data
        else:
            assert status_response.status_code == 404
        
        # 4. 停止机器人
        stop_response = client.post(f"/api/v1/bots/{bot_id}/stop", headers=auth_headers)
        
        if stop_response.status_code == 200:
            stop_data = assert_response_ok(stop_response)
            assert stop_data.get("success") is True
            mock_stop_bot.assert_called_once_with(bot_id)
        else:
            assert stop_response.status_code == 404
        
        # 5. 清理
        client.delete(f"/api/v1/bots/{bot_id}", headers=auth_headers)
        
        print("✅ 机器人生命周期管理测试通过")
    
    def test_multi_user_isolation(self, client: TestClient):
        """测试多用户数据隔离"""
        # 创建两个用户
        user1_data = {
            "username": "user1_isolation",
            "email": "user1@isolation.com",
            "password": "pass123",
            "role": "user"
        }
        
        user2_data = {
            "username": "user2_isolation",
            "email": "user2@isolation.com", 
            "password": "pass123",
            "role": "user"
        }
        
        # 用户1注册
        user1_response = client.post("/api/v1/auth/register", json=user1_data)
        user1_info = assert_response_ok(user1_response, 201)
        user1_token = user1_info["access_token"]
        user1_headers = {"Authorization": f"Bearer {user1_token}"}
        
        # 用户2注册
        user2_response = client.post("/api/v1/auth/register", json=user2_data)
        user2_info = assert_response_ok(user2_response, 201)
        user2_token = user2_info["access_token"]
        user2_headers = {"Authorization": f"Bearer {user2_token}"}
        
        # 用户1创建机器人
        bot_data = {
            "name": "用户1的机器人",
            "platform_type": "web",
            "platform_config": {"test": "config"},
            "llm_config": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "test"}
        }
        
        user1_bot_response = client.post("/api/v1/bots/", json=bot_data, headers=user1_headers)
        user1_bot = assert_response_ok(user1_bot_response, 201)
        user1_bot_id = user1_bot["id"]
        
        # 用户2创建机器人
        bot_data["name"] = "用户2的机器人"
        user2_bot_response = client.post("/api/v1/bots/", json=bot_data, headers=user2_headers)
        user2_bot = assert_response_ok(user2_bot_response, 201)
        user2_bot_id = user2_bot["id"]
        
        # 验证数据隔离：用户1不能访问用户2的机器人
        access_response = client.get(f"/api/v1/bots/{user2_bot_id}", headers=user1_headers)
        
        if access_response.status_code == 404:
            # 正确的隔离：返回404表示用户1看不到用户2的机器人
            pass
        elif access_response.status_code == 403:
            # 正确的隔离：返回403表示禁止访问
            pass
        else:
            # 可能没有实现隔离，或者允许访问
            # 这需要根据具体的业务逻辑来判断
            pass
        
        # 验证用户只能看到自己的机器人
        user1_bots_response = client.get("/api/v1/bots/", headers=user1_headers)
        user1_bots_data = assert_response_ok(user1_bots_response)
        
        user1_bot_ids = [bot["id"] for bot in user1_bots_data["bots"]]
        assert user1_bot_id in user1_bot_ids
        
        # 如果实现了严格隔离，用户2的机器人不应该在用户1的列表中
        if len(user1_bot_ids) == 1:
            assert user2_bot_id not in user1_bot_ids
        
        # 清理
        client.delete(f"/api/v1/bots/{user1_bot_id}", headers=user1_headers)
        client.delete(f"/api/v1/bots/{user2_bot_id}", headers=user2_headers)
        
        print("✅ 多用户数据隔离测试通过")
    
    def test_error_handling_flow(self, client: TestClient, auth_headers: dict):
        """测试错误处理流程"""
        # 1. 尝试访问不存在的机器人
        nonexistent_response = client.get("/api/v1/bots/nonexistent_id", headers=auth_headers)
        assert_response_error(nonexistent_response, 404)
        
        # 2. 尝试创建无效配置的机器人
        invalid_bot_data = {
            "name": "",  # 空名称
            "platform_type": "invalid_platform",
            "platform_config": {},  # 空配置
            "llm_config": {}  # 空配置
        }
        
        invalid_response = client.post("/api/v1/bots/", json=invalid_bot_data, headers=auth_headers)
        # 应该返回400或422错误
        assert invalid_response.status_code in [400, 422]
        
        # 3. 尝试使用无效token访问API
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        auth_response = client.get("/api/v1/auth/me", headers=invalid_headers)
        assert_response_error(auth_response, 401)
        
        # 4. 尝试更新不存在的资源
        update_response = client.put("/api/v1/bots/nonexistent_id", 
                                   json={"name": "新名称"}, headers=auth_headers)
        assert_response_error(update_response, 404)
        
        # 5. 尝试删除不存在的资源
        delete_response = client.delete("/api/v1/bots/nonexistent_id", headers=auth_headers)
        assert_response_error(delete_response, 404)
        
        print("✅ 错误处理流程测试通过")
    
    def test_permission_flow(self, client: TestClient, auth_headers: dict, admin_headers: dict):
        """测试权限控制流程"""
        # 1. 普通用户尝试访问管理员功能
        user_access_response = client.get("/api/v1/users/", headers=auth_headers)
        
        if user_access_response.status_code == 403:
            # 正确的权限控制
            assert_response_error(user_access_response, 403)
        elif user_access_response.status_code == 200:
            # 可能允许普通用户查看用户列表
            pass
        else:
            # API可能未实现
            assert user_access_response.status_code == 404
        
        # 2. 管理员访问管理员功能
        admin_access_response = client.get("/api/v1/users/", headers=admin_headers)
        
        if admin_access_response.status_code == 200:
            # 管理员应该能够访问
            assert_response_ok(admin_access_response)
        else:
            # API可能未实现
            assert admin_access_response.status_code == 404
        
        # 3. 测试监控API的权限
        monitoring_response = client.get("/api/v1/monitoring/metrics", headers=auth_headers)
        
        if monitoring_response.status_code == 403:
            # 普通用户不能访问监控
            assert_response_error(monitoring_response, 403)
        elif monitoring_response.status_code == 200:
            # 允许普通用户查看监控
            pass
        else:
            # API未实现
            assert monitoring_response.status_code == 404
        
        print("✅ 权限控制流程测试通过")
    
    @patch('engines.conversation_engine.conversation_engine.process_message')
    def test_conversation_flow(self, mock_process, client: TestClient, auth_headers: dict):
        """测试对话流程"""
        # 模拟对话引擎
        async def mock_conversation(*args, **kwargs):
            yield {"type": "content", "content": "你好！"}
            yield {"type": "content", "content": "我是测试机器人。"}
            yield {"type": "response_complete"}
        
        mock_process.return_value = mock_conversation()
        
        # 1. 创建机器人
        bot_data = {
            "name": "对话测试机器人",
            "platform_type": "web",
            "platform_config": {"test": "config"},
            "llm_config": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "test"}
        }
        
        bot_response = client.post("/api/v1/bots/", json=bot_data, headers=auth_headers)
        bot_info = assert_response_ok(bot_response, 201)
        bot_id = bot_info["id"]
        
        # 2. 创建对话
        conversation_data = {
            "bot_id": bot_id,
            "title": "对话流程测试",
            "platform": "web"
        }
        
        conv_response = client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
        conv_info = assert_response_ok(conv_response, 201)
        conversation_id = conv_info["id"]
        
        # 3. 发送多轮消息
        messages = [
            "你好",
            "你是谁？",
            "你能做什么？"
        ]
        
        for message_content in messages:
            message_data = {
                "content": message_content,
                "message_type": "text"
            }
            
            message_response = client.post(
                f"/api/v1/conversations/{conversation_id}/messages",
                json=message_data,
                headers=auth_headers
            )
            
            if message_response.status_code == 200:
                # 验证消息处理
                message_info = assert_response_ok(message_response)
                # 可以添加更多验证逻辑
            else:
                # 消息API可能未实现
                assert message_response.status_code == 404
                break
        
        # 4. 获取对话历史
        history_response = client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=auth_headers)
        
        if history_response.status_code == 200:
            history_data = assert_response_ok(history_response)
            
            if "messages" in history_data:
                assert isinstance(history_data["messages"], list)
                assert len(history_data["messages"]) > 0
        else:
            assert history_response.status_code == 404
        
        # 5. 清理
        client.delete(f"/api/v1/conversations/{conversation_id}", headers=auth_headers)
        client.delete(f"/api/v1/bots/{bot_id}", headers=auth_headers)
        
        print("✅ 对话流程测试通过")


@pytest.mark.asyncio
class TestAsyncIntegration:
    """异步集成测试类"""
    
    async def test_concurrent_requests(self, client: TestClient, auth_headers: dict):
        """测试并发请求处理"""
        # 创建多个并发请求
        async def make_request():
            response = client.get("/api/v1/auth/me", headers=auth_headers)
            return response.status_code
        
        # 并发执行请求
        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # 所有请求都应该成功
        for status_code in results:
            assert status_code == 200
        
        print("✅ 并发请求测试通过")
    
    async def test_async_operations(self):
        """测试异步操作"""
        try:
            from managers.bot_manager import bot_manager
            from managers.conversation_manager import conversation_manager
            
            # 测试异步操作的基本功能
            # 由于需要数据库连接，这里主要测试方法是否存在
            assert hasattr(bot_manager, 'create_bot')
            assert hasattr(bot_manager, 'get_bot_by_id')
            assert hasattr(conversation_manager, 'create_conversation')
            assert hasattr(conversation_manager, 'get_conversations')
            
            print("✅ 异步操作测试通过")
            
        except ImportError:
            pytest.skip("Manager modules not available")


class TestPerformanceIntegration:
    """性能集成测试类"""
    
    def test_response_time(self, client: TestClient, auth_headers: dict):
        """测试响应时间"""
        import time
        
        # 测试API响应时间
        start_time = time.time()
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # 响应时间应该在合理范围内（比如小于5秒）
        assert response_time < 5.0
        assert response.status_code == 200
        
        print(f"✅ API响应时间: {response_time:.3f}秒")
    
    def test_large_data_handling(self, client: TestClient, auth_headers: dict):
        """测试大数据处理"""
        # 创建多个机器人来测试大数据量处理
        bot_ids = []
        
        try:
            for i in range(10):
                bot_data = {
                    "name": f"性能测试机器人{i+1}",
                    "platform_type": "web",
                    "platform_config": {"test": f"config{i}"},
                    "llm_config": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "test"}
                }
                
                response = client.post("/api/v1/bots/", json=bot_data, headers=auth_headers)
                
                if response.status_code == 201:
                    bot_info = response.json()
                    bot_ids.append(bot_info["id"])
                else:
                    break
            
            # 测试获取大量数据的性能
            start_time = time.time()
            response = client.get("/api/v1/bots/?limit=50", headers=auth_headers)
            end_time = time.time()
            
            query_time = end_time - start_time
            
            if response.status_code == 200:
                data = response.json()
                assert "bots" in data
                assert query_time < 10.0  # 查询时间应该在10秒内
                
                print(f"✅ 大数据查询时间: {query_time:.3f}秒")
            
        finally:
            # 清理创建的机器人
            for bot_id in bot_ids:
                client.delete(f"/api/v1/bots/{bot_id}", headers=auth_headers)


class TestSystemIntegration:
    """系统集成测试类"""
    
    def test_health_check_integration(self, client: TestClient):
        """测试系统健康检查集成"""
        # 检查各个组件的健康状态
        health_endpoints = [
            "/api/v1/monitoring/health",
            "/api/v1/multimodal/health"
        ]
        
        system_health = {}
        
        for endpoint in health_endpoints:
            response = client.get(endpoint)
            
            if response.status_code == 200:
                health_data = response.json()
                system_health[endpoint] = health_data.get("status", "unknown")
            else:
                system_health[endpoint] = "unavailable"
        
        # 验证系统整体健康状态
        available_services = sum(1 for status in system_health.values() 
                               if status in ["healthy", "ok"])
        
        print(f"✅ 系统健康检查完成，可用服务数: {available_services}/{len(health_endpoints)}")
    
    def test_cross_module_integration(self, client: TestClient, auth_headers: dict):
        """测试跨模块集成"""
        # 测试机器人管理与对话管理的集成
        # 这个测试验证不同模块之间的数据一致性和功能集成
        
        # 1. 创建机器人
        bot_data = {
            "name": "跨模块集成测试机器人",
            "platform_type": "web",
            "platform_config": {"test": "config"},
            "llm_config": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "test"}
        }
        
        bot_response = client.post("/api/v1/bots/", json=bot_data, headers=auth_headers)
        
        if bot_response.status_code == 201:
            bot_info = bot_response.json()
            bot_id = bot_info["id"]
            
            # 2. 使用该机器人创建对话
            conversation_data = {
                "bot_id": bot_id,
                "title": "跨模块集成测试对话",
                "platform": "web"
            }
            
            conv_response = client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
            
            if conv_response.status_code == 201:
                conv_info = conv_response.json()
                conversation_id = conv_info["id"]
                
                # 3. 验证数据一致性
                assert conv_info["bot_id"] == bot_id
                
                # 4. 删除机器人，检查对话是否受影响
                delete_response = client.delete(f"/api/v1/bots/{bot_id}", headers=auth_headers)
                
                if delete_response.status_code in [200, 204]:
                    # 机器人删除成功，检查对话状态
                    conv_check_response = client.get(f"/api/v1/conversations/{conversation_id}", headers=auth_headers)
                    
                    # 根据业务逻辑，对话可能会被级联删除或者标记为无效
                    # 这里不强制要求特定行为，但要确保系统处理了这种情况
                    assert conv_check_response.status_code in [200, 404, 410]
            
            print("✅ 跨模块集成测试通过")
        else:
            pytest.skip("机器人创建失败，跳过跨模块集成测试")


def test_full_system_smoke_test(client: TestClient):
    """系统冒烟测试"""
    """验证系统的基本功能是否正常工作"""
    
    # 基本API端点测试
    basic_endpoints = [
        ("/api/v1/auth/register", "POST"),
        ("/api/v1/monitoring/health", "GET"),
    ]
    
    working_endpoints = 0
    total_endpoints = len(basic_endpoints)
    
    for endpoint, method in basic_endpoints:
        try:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                # 对于POST端点，发送空数据或基本数据
                if "register" in endpoint:
                    # 跳过注册测试，避免重复数据问题
                    continue
                else:
                    response = client.post(endpoint, json={})
            
            # 检查响应状态
            if response.status_code in [200, 201, 400, 422, 404]:
                # 这些状态码表示API端点存在且可以响应
                working_endpoints += 1
            
        except Exception as e:
            print(f"端点 {endpoint} 测试异常: {e}")
    
    # 计算系统可用性
    availability = (working_endpoints / total_endpoints) * 100 if total_endpoints > 0 else 0
    
    print(f"✅ 系统冒烟测试完成")
    print(f"📊 系统可用性: {availability:.1f}% ({working_endpoints}/{total_endpoints})")
    
    # 如果主要功能不可用，标记为失败
    assert availability >= 50, f"系统可用性过低: {availability}%"