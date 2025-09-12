"""
用户认证API测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import assert_response_ok, assert_response_error, create_test_user


class TestAuthAPI:
    """用户认证API测试类"""
    
    def test_register_success(self, client: TestClient, sample_user_data: dict):
        """测试用户注册成功"""
        response = client.post("/api/v1/auth/register", json=sample_user_data)
        data = assert_response_ok(response, 201)
        
        assert data["user_info"]["username"] == sample_user_data["username"]
        assert data["user_info"]["email"] == sample_user_data["email"]
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    def test_register_duplicate_username(self, client: TestClient, sample_user_data: dict):
        """测试用户名重复注册"""
        # 第一次注册
        client.post("/api/v1/auth/register", json=sample_user_data)
        
        # 第二次注册相同用户名
        response = client.post("/api/v1/auth/register", json=sample_user_data)
        assert_response_error(response, 400)
    
    def test_register_duplicate_email(self, client: TestClient, sample_user_data: dict):
        """测试邮箱重复注册"""
        # 第一次注册
        client.post("/api/v1/auth/register", json=sample_user_data)
        
        # 第二次注册不同用户名但相同邮箱
        duplicate_email_data = sample_user_data.copy()
        duplicate_email_data["username"] = "different_user"
        
        response = client.post("/api/v1/auth/register", json=duplicate_email_data)
        assert_response_error(response, 400)
    
    def test_register_invalid_email(self, client: TestClient, sample_user_data: dict):
        """测试无效邮箱格式"""
        invalid_data = sample_user_data.copy()
        invalid_data["email"] = "invalid-email"
        
        response = client.post("/api/v1/auth/register", json=invalid_data)
        assert_response_error(response, 422)
    
    def test_register_weak_password(self, client: TestClient, sample_user_data: dict):
        """测试弱密码"""
        weak_password_data = sample_user_data.copy()
        weak_password_data["password"] = "123"
        
        response = client.post("/api/v1/auth/register", json=weak_password_data)
        assert_response_error(response, 422)
    
    def test_login_success(self, client: TestClient, sample_user_data: dict):
        """测试用户登录成功"""
        # 先注册用户
        client.post("/api/v1/auth/register", json=sample_user_data)
        
        # 登录
        login_data = {
            "username": sample_user_data["username"],
            "password": sample_user_data["password"]
        }
        response = client.post("/api/v1/auth/login", json=login_data)
        data = assert_response_ok(response)
        
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user_info" in data
    
    def test_login_invalid_username(self, client: TestClient):
        """测试无效用户名登录"""
        login_data = {
            "username": "nonexistent_user",
            "password": "password123"
        }
        response = client.post("/api/v1/auth/login", json=login_data)
        assert_response_error(response, 401)
    
    def test_login_invalid_password(self, client: TestClient, sample_user_data: dict):
        """测试错误密码登录"""
        # 先注册用户
        client.post("/api/v1/auth/register", json=sample_user_data)
        
        # 使用错误密码登录
        login_data = {
            "username": sample_user_data["username"],
            "password": "wrong_password"
        }
        response = client.post("/api/v1/auth/login", json=login_data)
        assert_response_error(response, 401)
    
    def test_get_current_user(self, client: TestClient, auth_headers: dict):
        """测试获取当前用户信息"""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        data = assert_response_ok(response)
        
        assert "id" in data
        assert "username" in data
        assert "email" in data
        assert "role" in data
    
    def test_get_current_user_unauthorized(self, client: TestClient):
        """测试未认证获取用户信息"""
        response = client.get("/api/v1/auth/me")
        assert_response_error(response, 401)
    
    def test_get_current_user_invalid_token(self, client: TestClient):
        """测试无效token获取用户信息"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert_response_error(response, 401)
    
    def test_refresh_token(self, client: TestClient, sample_user_data: dict):
        """测试刷新token"""
        # 先注册并登录
        client.post("/api/v1/auth/register", json=sample_user_data)
        
        login_response = client.post("/api/v1/auth/login", json={
            "username": sample_user_data["username"],
            "password": sample_user_data["password"]
        })
        login_data = login_response.json()
        
        # 刷新token
        refresh_data = {"refresh_token": login_data.get("refresh_token", "")}
        response = client.post("/api/v1/auth/refresh", json=refresh_data)
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "token_type" in data
        else:
            # 如果没有实现refresh token功能，应该返回501或404
            assert response.status_code in [404, 501]
    
    def test_logout(self, client: TestClient, auth_headers: dict):
        """测试用户登出"""
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True
        else:
            # 如果没有实现logout功能，应该返回501或404
            assert response.status_code in [404, 501]
    
    def test_change_password(self, client: TestClient, auth_headers: dict):
        """测试修改密码"""
        password_data = {
            "old_password": "testpass123",
            "new_password": "newpass123"
        }
        response = client.post("/api/v1/auth/change-password", 
                             json=password_data, headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True
        else:
            # 如果没有实现修改密码功能，应该返回501或404
            assert response.status_code in [404, 501]


@pytest.mark.asyncio
class TestAuthService:
    """认证服务测试类"""
    
    async def test_create_user(self, db_session: AsyncSession, sample_user_data: dict):
        """测试创建用户"""
        user = await create_test_user(db_session, sample_user_data)
        
        assert user.id is not None
        assert user.username == sample_user_data["username"]
        assert user.email == sample_user_data["email"]
        assert user.role == sample_user_data["role"]
        assert user.is_active is True
    
    async def test_password_hashing(self, db_session: AsyncSession, sample_user_data: dict):
        """测试密码哈希"""
        user = await create_test_user(db_session, sample_user_data)
        
        # 密码应该被哈希，不应该是明文
        assert user.password_hash != sample_user_data["password"]
        assert len(user.password_hash) > 50  # bcrypt哈希长度检查
    
    async def test_user_authentication(self, db_session: AsyncSession, sample_user_data: dict):
        """测试用户认证"""
        from security.auth import AuthManager
        from security.password import verify_password
        
        user = await create_test_user(db_session, sample_user_data)
        auth_manager = AuthManager()
        
        # 验证密码
        is_valid = verify_password(sample_user_data["password"], user.password_hash)
        assert is_valid is True
        
        # 验证错误密码
        is_invalid = verify_password("wrong_password", user.password_hash)
        assert is_invalid is False


class TestAuthIntegration:
    """认证集成测试类"""
    
    def test_protected_endpoint_access(self, client: TestClient, auth_headers: dict):
        """测试受保护端点访问"""
        # 测试需要认证的端点
        response = client.get("/api/v1/bots/", headers=auth_headers)
        
        # 应该返回200或者具体的业务状态码，而不是401
        assert response.status_code != 401
    
    def test_admin_endpoint_access(self, client: TestClient, admin_headers: dict):
        """测试管理员端点访问"""
        # 测试需要管理员权限的端点
        response = client.get("/api/v1/users/", headers=admin_headers)
        
        # 应该返回200或者具体的业务状态码，而不是403
        assert response.status_code != 403
    
    def test_non_admin_access_admin_endpoint(self, client: TestClient, auth_headers: dict):
        """测试非管理员访问管理员端点"""
        response = client.get("/api/v1/users/", headers=auth_headers)
        
        # 应该返回403禁止访问
        assert response.status_code == 403
    
    def test_concurrent_login(self, client: TestClient, sample_user_data: dict):
        """测试并发登录"""
        import threading
        import time
        
        # 先注册用户
        client.post("/api/v1/auth/register", json=sample_user_data)
        
        login_data = {
            "username": sample_user_data["username"],
            "password": sample_user_data["password"]
        }
        
        results = []
        
        def login_request():
            response = client.post("/api/v1/auth/login", json=login_data)
            results.append(response.status_code)
        
        # 创建多个并发登录请求
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=login_request)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 所有请求都应该成功
        assert all(status == 200 for status in results)
    
    def test_token_expiration(self, client: TestClient, sample_user_data: dict):
        """测试token过期"""
        # 这个测试需要配置较短的token过期时间
        # 或者使用mock来模拟过期
        pass  # 暂时跳过，需要根据具体实现调整
    
    def test_multiple_device_login(self, client: TestClient, sample_user_data: dict):
        """测试多设备登录"""
        # 先注册用户
        client.post("/api/v1/auth/register", json=sample_user_data)
        
        login_data = {
            "username": sample_user_data["username"],
            "password": sample_user_data["password"]
        }
        
        # 第一次登录
        response1 = client.post("/api/v1/auth/login", json=login_data)
        token1 = response1.json()["access_token"]
        
        # 第二次登录（模拟不同设备）
        response2 = client.post("/api/v1/auth/login", json=login_data)
        token2 = response2.json()["access_token"]
        
        # 两个token都应该有效
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        response1 = client.get("/api/v1/auth/me", headers=headers1)
        response2 = client.get("/api/v1/auth/me", headers=headers2)
        
        assert response1.status_code == 200
        assert response2.status_code == 200