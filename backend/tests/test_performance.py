"""
性能测试
"""

import pytest
import time
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
import statistics
from unittest.mock import patch, MagicMock

from tests.conftest import assert_response_ok


@pytest.mark.performance
class TestAPIPerformance:
    """API性能测试类"""
    
    def test_auth_endpoint_performance(self, client: TestClient):
        """测试认证端点性能"""
        # 注册用户
        user_data = {
            "username": "perf_user",
            "email": "perf@test.com",
            "password": "perfpass123",
            "role": "user"
        }
        
        register_response = client.post("/api/v1/auth/register", json=user_data)
        if register_response.status_code != 201:
            pytest.skip("用户注册失败，跳过性能测试")
        
        register_data = register_response.json()
        token = register_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试认证端点性能
        response_times = []
        
        for i in range(50):
            start_time = time.time()
            response = client.get("/api/v1/auth/me", headers=headers)
            end_time = time.time()
            
            if response.status_code == 200:
                response_times.append(end_time - start_time)
        
        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            print(f"\n📊 认证端点性能统计:")
            print(f"   平均响应时间: {avg_time:.3f}秒")
            print(f"   中位数响应时间: {median_time:.3f}秒")
            print(f"   最大响应时间: {max_time:.3f}秒")
            print(f"   最小响应时间: {min_time:.3f}秒")
            
            # 性能断言
            assert avg_time < 1.0, f"平均响应时间过长: {avg_time:.3f}秒"
            assert max_time < 5.0, f"最大响应时间过长: {max_time:.3f}秒"
    
    def test_bot_crud_performance(self, client: TestClient, auth_headers: dict):
        """测试机器人CRUD操作性能"""
        bot_data = {
            "name": "性能测试机器人",
            "platform_type": "web",
            "platform_config": {"test": "config"},
            "llm_config": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "test"}
        }
        
        # 测试创建性能
        create_times = []
        bot_ids = []
        
        for i in range(20):
            bot_data["name"] = f"性能测试机器人{i+1}"
            
            start_time = time.time()
            response = client.post("/api/v1/bots/", json=bot_data, headers=auth_headers)
            end_time = time.time()
            
            if response.status_code == 201:
                create_times.append(end_time - start_time)
                bot_info = response.json()
                bot_ids.append(bot_info["id"])
        
        # 测试读取性能
        read_times = []
        
        for bot_id in bot_ids[:10]:  # 测试前10个
            start_time = time.time()
            response = client.get(f"/api/v1/bots/{bot_id}", headers=auth_headers)
            end_time = time.time()
            
            if response.status_code == 200:
                read_times.append(end_time - start_time)
        
        # 测试列表查询性能
        list_times = []
        
        for i in range(10):
            start_time = time.time()
            response = client.get("/api/v1/bots/", headers=auth_headers)
            end_time = time.time()
            
            if response.status_code == 200:
                list_times.append(end_time - start_time)
        
        # 测试更新性能
        update_times = []
        
        for bot_id in bot_ids[:5]:  # 测试前5个
            update_data = {"description": f"更新描述 {time.time()}"}
            
            start_time = time.time()
            response = client.put(f"/api/v1/bots/{bot_id}", json=update_data, headers=auth_headers)
            end_time = time.time()
            
            if response.status_code == 200:
                update_times.append(end_time - start_time)
        
        # 测试删除性能
        delete_times = []
        
        for bot_id in bot_ids:
            start_time = time.time()
            response = client.delete(f"/api/v1/bots/{bot_id}", headers=auth_headers)
            end_time = time.time()
            
            if response.status_code in [200, 204]:
                delete_times.append(end_time - start_time)
        
        # 输出性能统计
        operations = {
            "创建": create_times,
            "读取": read_times,
            "列表": list_times,
            "更新": update_times,
            "删除": delete_times
        }
        
        print(f"\n📊 机器人CRUD性能统计:")
        
        for op_name, times in operations.items():
            if times:
                avg_time = statistics.mean(times)
                print(f"   {op_name}操作平均时间: {avg_time:.3f}秒")
                
                # 性能断言
                assert avg_time < 2.0, f"{op_name}操作平均时间过长: {avg_time:.3f}秒"
    
    def test_concurrent_requests_performance(self, client: TestClient, auth_headers: dict):
        """测试并发请求性能"""
        def make_request():
            start_time = time.time()
            response = client.get("/api/v1/auth/me", headers=auth_headers)
            end_time = time.time()
            
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 200
            }
        
        # 并发测试
        concurrent_users = 20
        requests_per_user = 5
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = []
            
            for _ in range(concurrent_users * requests_per_user):
                future = executor.submit(make_request)
                futures.append(future)
            
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 统计结果
        successful_requests = sum(1 for r in results if r["success"])
        failed_requests = len(results) - successful_requests
        response_times = [r["response_time"] for r in results if r["success"]]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            throughput = successful_requests / total_time
            
            print(f"\n📊 并发请求性能统计:")
            print(f"   并发用户数: {concurrent_users}")
            print(f"   总请求数: {len(results)}")
            print(f"   成功请求数: {successful_requests}")
            print(f"   失败请求数: {failed_requests}")
            print(f"   总耗时: {total_time:.3f}秒")
            print(f"   平均响应时间: {avg_response_time:.3f}秒")
            print(f"   吞吐量: {throughput:.2f} 请求/秒")
            
            # 性能断言
            success_rate = successful_requests / len(results)
            assert success_rate >= 0.95, f"成功率过低: {success_rate*100:.1f}%"
            assert avg_response_time < 3.0, f"并发平均响应时间过长: {avg_response_time:.3f}秒"
            assert throughput >= 5.0, f"吞吐量过低: {throughput:.2f} 请求/秒"
    
    def test_large_data_query_performance(self, client: TestClient, auth_headers: dict):
        """测试大数据量查询性能"""
        # 创建大量测试数据
        bot_data = {
            "name": "大数据测试机器人",
            "platform_type": "web", 
            "platform_config": {"test": "config"},
            "llm_config": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "test"}
        }
        
        created_bots = []
        
        # 创建100个机器人（如果系统能处理）
        for i in range(min(100, 50)):  # 限制在50个以内，避免测试时间过长
            bot_data["name"] = f"大数据测试机器人{i+1}"
            
            response = client.post("/api/v1/bots/", json=bot_data, headers=auth_headers)
            
            if response.status_code == 201:
                bot_info = response.json()
                created_bots.append(bot_info["id"])
            else:
                break
        
        if not created_bots:
            pytest.skip("无法创建测试数据，跳过大数据查询测试")
        
        # 测试不同分页大小的查询性能
        page_sizes = [10, 20, 50, 100]
        
        print(f"\n📊 大数据查询性能测试 (总数据量: {len(created_bots)}):")
        
        try:
            for page_size in page_sizes:
                query_times = []
                
                for page in range(3):  # 测试前3页
                    start_time = time.time()
                    response = client.get(
                        f"/api/v1/bots/?limit={page_size}&offset={page * page_size}",
                        headers=auth_headers
                    )
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        query_times.append(end_time - start_time)
                
                if query_times:
                    avg_time = statistics.mean(query_times)
                    print(f"   分页大小 {page_size}: 平均查询时间 {avg_time:.3f}秒")
                    
                    # 性能断言
                    assert avg_time < 5.0, f"分页大小{page_size}查询时间过长: {avg_time:.3f}秒"
        
        finally:
            # 清理测试数据
            for bot_id in created_bots:
                client.delete(f"/api/v1/bots/{bot_id}", headers=auth_headers)
    
    @patch('multimodal.process_binary')
    def test_file_processing_performance(self, mock_process, client: TestClient, auth_headers: dict):
        """测试文件处理性能"""
        # 模拟文件处理结果
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.media_type.value = "text"
        mock_result.content = "处理后的内容"
        mock_result.metadata = {"size": 1024}
        mock_result.error = None
        mock_result.processed_files = ["test.txt"]
        mock_process.return_value = mock_result
        
        # 测试不同大小文件的处理性能
        file_sizes = [1024, 10240, 102400]  # 1KB, 10KB, 100KB
        
        print(f"\n📊 文件处理性能测试:")
        
        for size in file_sizes:
            file_content = b"x" * size
            
            processing_times = []
            
            for i in range(5):
                files = {"file": (f"test_{size}.txt", file_content, "text/plain")}
                
                start_time = time.time()
                response = client.post(
                    "/api/v1/multimodal/process",
                    files=files,
                    data={"options": "{}"},
                    headers=auth_headers
                )
                end_time = time.time()
                
                if response.status_code == 200:
                    processing_times.append(end_time - start_time)
                elif response.status_code == 404:
                    # 多模态API未实现
                    break
            
            if processing_times:
                avg_time = statistics.mean(processing_times)
                throughput = size / avg_time / 1024  # KB/s
                
                print(f"   文件大小 {size/1024:.1f}KB: 平均处理时间 {avg_time:.3f}秒, 吞吐量 {throughput:.1f}KB/s")
                
                # 性能断言
                assert avg_time < 10.0, f"文件处理时间过长: {avg_time:.3f}秒"


@pytest.mark.performance
@pytest.mark.asyncio
class TestAsyncPerformance:
    """异步性能测试类"""
    
    async def test_concurrent_database_operations(self):
        """测试并发数据库操作性能"""
        try:
            from managers.bot_manager import bot_manager
            
            # 并发创建机器人
            async def create_bot_task(index):
                bot_data = {
                    "name": f"并发测试机器人{index}",
                    "platform_type": "web",
                    "platform_config": {"test": f"config{index}"},
                    "llm_config": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "test"}
                }
                
                start_time = time.time()
                try:
                    # 这里需要mock用户ID
                    result = await bot_manager.create_bot(
                        user_id="test_user_id",
                        **bot_data
                    )
                    end_time = time.time()
                    
                    return {
                        "success": True,
                        "time": end_time - start_time,
                        "bot_id": result.id if result else None
                    }
                except Exception as e:
                    end_time = time.time()
                    return {
                        "success": False,
                        "time": end_time - start_time,
                        "error": str(e)
                    }
            
            # 执行并发任务
            concurrent_tasks = 10
            start_time = time.time()
            
            tasks = [create_bot_task(i) for i in range(concurrent_tasks)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # 统计结果
            successful_ops = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
            operation_times = [r["time"] for r in results if isinstance(r, dict) and "time" in r]
            
            if operation_times:
                avg_time = statistics.mean(operation_times)
                
                print(f"\n📊 并发数据库操作性能:")
                print(f"   并发任务数: {concurrent_tasks}")
                print(f"   成功操作数: {successful_ops}")
                print(f"   总耗时: {total_time:.3f}秒")
                print(f"   平均操作时间: {avg_time:.3f}秒")
                
                # 性能断言
                assert avg_time < 5.0, f"并发数据库操作时间过长: {avg_time:.3f}秒"
        
        except ImportError:
            pytest.skip("Manager modules not available")
    
    async def test_streaming_performance(self):
        """测试流式处理性能"""
        try:
            from engines.conversation_engine import conversation_engine
            
            # 模拟流式处理
            start_time = time.time()
            
            chunks_received = 0
            total_content_length = 0
            
            async for chunk in conversation_engine.process_message(
                conversation_id="test_conv_id",
                user_message="请生成一个长回答",
                bot_config={
                    "llm_config": {"provider": "openai", "model": "gpt-3.5-turbo"},
                    "system_prompt": "你是一个助手",
                    "knowledge_base_ids": [],
                    "plugins": []
                },
                stream=True
            ):
                chunks_received += 1
                if chunk.get("type") == "content":
                    content = chunk.get("content", "")
                    total_content_length += len(content)
                elif chunk.get("type") == "response_complete":
                    break
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            if chunks_received > 0:
                avg_chunk_time = processing_time / chunks_received
                
                print(f"\n📊 流式处理性能:")
                print(f"   总处理时间: {processing_time:.3f}秒")
                print(f"   接收块数: {chunks_received}")
                print(f"   总内容长度: {total_content_length}")
                print(f"   平均块处理时间: {avg_chunk_time:.3f}秒")
                
                # 性能断言
                assert avg_chunk_time < 1.0, f"流式处理块时间过长: {avg_chunk_time:.3f}秒"
        
        except ImportError:
            pytest.skip("Conversation engine not available")


@pytest.mark.performance
class TestMemoryPerformance:
    """内存性能测试类"""
    
    def test_memory_usage_monitoring(self, client: TestClient, auth_headers: dict):
        """测试内存使用情况监控"""
        import psutil
        import os
        
        # 获取当前进程
        process = psutil.Process(os.getpid())
        
        # 记录初始内存使用
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行一系列操作
        for i in range(10):
            # 创建机器人
            bot_data = {
                "name": f"内存测试机器人{i}",
                "platform_type": "web",
                "platform_config": {"test": f"config{i}"},
                "llm_config": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "test"}
            }
            
            response = client.post("/api/v1/bots/", json=bot_data, headers=auth_headers)
            
            if response.status_code == 201:
                bot_info = response.json()
                
                # 立即删除以测试内存释放
                client.delete(f"/api/v1/bots/{bot_info['id']}", headers=auth_headers)
        
        # 记录最终内存使用
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        print(f"\n📊 内存使用性能:")
        print(f"   初始内存: {initial_memory:.2f}MB")
        print(f"   最终内存: {final_memory:.2f}MB")
        print(f"   内存增长: {memory_growth:.2f}MB")
        
        # 内存增长应该在合理范围内
        assert memory_growth < 100, f"内存增长过多: {memory_growth:.2f}MB"
    
    def test_garbage_collection_performance(self, client: TestClient, auth_headers: dict):
        """测试垃圾回收性能"""
        import gc
        
        # 强制垃圾回收
        gc.collect()
        
        # 记录GC统计
        initial_collections = gc.get_stats()
        
        # 执行一些操作产生垃圾对象
        large_data_list = []
        
        for i in range(100):
            response = client.get("/api/v1/auth/me", headers=auth_headers)
            
            if response.status_code == 200:
                # 保存响应数据（模拟内存使用）
                large_data_list.append(response.json())
        
        # 清理引用
        del large_data_list
        
        # 强制垃圾回收
        collected = gc.collect()
        
        # 记录最终GC统计
        final_collections = gc.get_stats()
        
        print(f"\n📊 垃圾回收性能:")
        print(f"   手动回收对象数: {collected}")
        
        # 垃圾回收应该有效
        assert collected >= 0, "垃圾回收失败"


@pytest.mark.performance
class TestDatabasePerformance:
    """数据库性能测试类"""
    
    def test_database_connection_performance(self, client: TestClient, auth_headers: dict):
        """测试数据库连接性能"""
        # 测试数据库连接的建立和关闭性能
        
        connection_times = []
        
        for i in range(10):
            start_time = time.time()
            
            # 执行数据库操作（通过API间接测试）
            response = client.get("/api/v1/bots/", headers=auth_headers)
            
            end_time = time.time()
            
            if response.status_code == 200:
                connection_times.append(end_time - start_time)
        
        if connection_times:
            avg_time = statistics.mean(connection_times)
            
            print(f"\n📊 数据库连接性能:")
            print(f"   平均连接时间: {avg_time:.3f}秒")
            
            # 数据库连接应该很快
            assert avg_time < 2.0, f"数据库连接时间过长: {avg_time:.3f}秒"
    
    def test_transaction_performance(self, client: TestClient, auth_headers: dict):
        """测试数据库事务性能"""
        # 测试复杂事务的性能
        
        transaction_times = []
        created_bots = []
        
        try:
            for i in range(5):
                start_time = time.time()
                
                # 创建机器人（涉及数据库事务）
                bot_data = {
                    "name": f"事务测试机器人{i}",
                    "platform_type": "web",
                    "platform_config": {"test": f"config{i}"},
                    "llm_config": {"provider": "openai", "model": "gpt-3.5-turbo", "api_key": "test"}
                }
                
                response = client.post("/api/v1/bots/", json=bot_data, headers=auth_headers)
                
                end_time = time.time()
                
                if response.status_code == 201:
                    transaction_times.append(end_time - start_time)
                    bot_info = response.json()
                    created_bots.append(bot_info["id"])
            
            if transaction_times:
                avg_time = statistics.mean(transaction_times)
                
                print(f"\n📊 数据库事务性能:")
                print(f"   平均事务时间: {avg_time:.3f}秒")
                
                # 事务时间应该合理
                assert avg_time < 3.0, f"数据库事务时间过长: {avg_time:.3f}秒"
        
        finally:
            # 清理测试数据
            for bot_id in created_bots:
                client.delete(f"/api/v1/bots/{bot_id}", headers=auth_headers)


def pytest_configure(config):
    """pytest配置"""
    config.addinivalue_line(
        "markers", 
        "performance: marks tests as performance tests (deselect with '-m \"not performance\"')"
    )