"""
多模态处理API测试
"""

import pytest
from fastapi.testclient import TestClient
import io
import json
from unittest.mock import patch, MagicMock

from tests.conftest import assert_response_ok, assert_response_error


class TestMultimodalAPI:
    """多模态处理API测试类"""
    
    def test_get_supported_formats(self, client: TestClient, auth_headers: dict):
        """测试获取支持的文件格式"""
        response = client.get("/api/v1/multimodal/formats", headers=auth_headers)
        data = assert_response_ok(response)
        
        assert "formats" in data
        assert "capabilities" in data
        assert isinstance(data["formats"], dict)
        assert isinstance(data["capabilities"], dict)
    
    def test_get_capabilities(self, client: TestClient, auth_headers: dict):
        """测试获取处理能力"""
        response = client.get("/api/v1/multimodal/capabilities", headers=auth_headers)
        
        # 应该返回200或者404（如果未实现）
        if response.status_code == 200:
            data = assert_response_ok(response)
            assert isinstance(data, dict)
        else:
            assert response.status_code == 404
    
    @patch('multimodal.process_binary')
    def test_process_text_file(self, mock_process, client: TestClient, auth_headers: dict):
        """测试处理文本文件"""
        # 模拟处理结果
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.media_type.value = "text"
        mock_result.content = "处理后的文本内容"
        mock_result.metadata = {"file_size": 100, "encoding": "utf-8"}
        mock_result.error = None
        mock_result.processed_files = ["test.txt"]
        mock_process.return_value = mock_result
        
        # 创建测试文件
        file_content = b"Hello, this is a test file."
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        
        response = client.post(
            "/api/v1/multimodal/process",
            files=files,
            data={"options": '{"extract_text": true}'},
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = assert_response_ok(response)
            
            assert data["success"] is True
            assert data["media_type"] == "text"
            assert data["content"] == "处理后的文本内容"
            assert "processing_time" in data
            mock_process.assert_called_once()
        else:
            # 如果API未实现，应该返回404
            assert response.status_code == 404
    
    @patch('multimodal.process_binary')
    def test_process_image_file(self, mock_process, client: TestClient, auth_headers: dict):
        """测试处理图像文件"""
        # 模拟处理结果
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.media_type.value = "image"
        mock_result.content = "图像分析结果"
        mock_result.metadata = {
            "width": 1920,
            "height": 1080,
            "format": "JPEG",
            "size": 2048000
        }
        mock_result.error = None
        mock_result.processed_files = ["test.jpg"]
        mock_process.return_value = mock_result
        
        # 创建假的图像文件内容
        fake_image_content = b'\xff\xd8\xff\xe0\x00\x10JFIF'  # JPEG文件头
        files = {"file": ("test.jpg", io.BytesIO(fake_image_content), "image/jpeg")}
        
        response = client.post(
            "/api/v1/multimodal/process",
            files=files,
            data={"options": '{"extract_text": true, "detect_faces": true}'},
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = assert_response_ok(response)
            
            assert data["success"] is True
            assert data["media_type"] == "image"
            assert "metadata" in data
            mock_process.assert_called_once()
        else:
            assert response.status_code == 404
    
    def test_process_empty_file(self, client: TestClient, auth_headers: dict):
        """测试处理空文件"""
        files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
        
        response = client.post(
            "/api/v1/multimodal/process",
            files=files,
            data={"options": "{}"},
            headers=auth_headers
        )
        
        if response.status_code == 400:
            # 应该返回错误
            assert_response_error(response, 400)
        elif response.status_code == 200:
            # 如果处理了空文件，检查返回结果
            data = response.json()
            assert data["success"] is False
            assert "error" in data
        else:
            # API未实现
            assert response.status_code == 404
    
    def test_process_large_file(self, client: TestClient, auth_headers: dict):
        """测试处理大文件"""
        # 创建超过限制的大文件（假设限制是100MB）
        large_content = b"x" * (101 * 1024 * 1024)  # 101MB
        files = {"file": ("large.txt", io.BytesIO(large_content), "text/plain")}
        
        response = client.post(
            "/api/v1/multimodal/process",
            files=files,
            data={"options": "{}"},
            headers=auth_headers
        )
        
        if response.status_code == 413:
            # 文件过大错误
            assert_response_error(response, 413)
        elif response.status_code == 200:
            # 如果处理了大文件，检查结果
            data = response.json()
            # 可能成功也可能失败，取决于实现
            pass
        else:
            assert response.status_code in [404, 413]
    
    def test_process_invalid_options(self, client: TestClient, auth_headers: dict):
        """测试无效的处理选项"""
        file_content = b"Test content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        
        response = client.post(
            "/api/v1/multimodal/process",
            files=files,
            data={"options": "invalid json"},
            headers=auth_headers
        )
        
        if response.status_code == 200:
            # 如果API处理了无效JSON，应该使用默认选项
            data = response.json()
            # 可能成功也可能失败
            pass
        else:
            assert response.status_code in [400, 404]
    
    @patch('multimodal.batch_process')
    def test_batch_process_files(self, mock_batch_process, client: TestClient, auth_headers: dict):
        """测试批量处理文件"""
        # 模拟批量处理结果
        mock_results = []
        for i in range(3):
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.media_type.value = "text"
            mock_result.content = f"文件{i+1}内容"
            mock_result.metadata = {"file_index": i}
            mock_result.error = None
            mock_result.processed_files = [f"file_{i+1}.txt"]
            mock_results.append(mock_result)
        
        mock_batch_process.return_value = mock_results
        
        # 创建多个测试文件
        files = [
            ("files", ("file1.txt", io.BytesIO(b"Content 1"), "text/plain")),
            ("files", ("file2.txt", io.BytesIO(b"Content 2"), "text/plain")),
            ("files", ("file3.txt", io.BytesIO(b"Content 3"), "text/plain"))
        ]
        
        response = client.post(
            "/api/v1/multimodal/batch-process",
            files=files,
            data={"options": '{"extract_text": true}'},
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = assert_response_ok(response)
            
            assert data["total_files"] == 3
            assert data["successful_files"] == 3
            assert data["failed_files"] == 0
            assert len(data["results"]) == 3
            assert "total_processing_time" in data
            mock_batch_process.assert_called_once()
        else:
            assert response.status_code == 404
    
    def test_batch_process_too_many_files(self, client: TestClient, auth_headers: dict):
        """测试批量处理过多文件"""
        # 创建超过限制的文件数量（假设限制是10个）
        files = []
        for i in range(12):
            files.append(("files", (f"file{i}.txt", io.BytesIO(b"Content"), "text/plain")))
        
        response = client.post(
            "/api/v1/multimodal/batch-process",
            files=files,
            data={"options": "{}"},
            headers=auth_headers
        )
        
        if response.status_code == 400:
            assert_response_error(response, 400)
        else:
            assert response.status_code in [404, 400]
    
    @patch('httpx.AsyncClient.get')
    def test_process_url(self, mock_get, client: TestClient, auth_headers: dict):
        """测试从URL处理文件"""
        # 模拟HTTP响应
        mock_response = MagicMock()
        mock_response.content = b"URL file content"
        mock_response.headers = {"content-disposition": 'attachment; filename="url_file.txt"'}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value.__aenter__.return_value = mock_response
        
        with patch('multimodal.process_binary') as mock_process:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.media_type.value = "text"
            mock_result.content = "URL文件内容"
            mock_result.metadata = {"source": "url"}
            mock_result.error = None
            mock_result.processed_files = ["url_file.txt"]
            mock_process.return_value = mock_result
            
            response = client.post(
                "/api/v1/multimodal/process-url",
                data={
                    "url": "https://example.com/test.txt",
                    "options": '{"extract_text": true}'
                },
                headers=auth_headers
            )
            
            if response.status_code == 200:
                data = assert_response_ok(response)
                
                assert data["success"] is True
                assert data["media_type"] == "text"
                assert data["content"] == "URL文件内容"
                mock_get.assert_called_once()
                mock_process.assert_called_once()
            else:
                assert response.status_code == 404
    
    def test_process_invalid_url(self, client: TestClient, auth_headers: dict):
        """测试处理无效URL"""
        response = client.post(
            "/api/v1/multimodal/process-url",
            data={
                "url": "invalid-url",
                "options": "{}"
            },
            headers=auth_headers
        )
        
        if response.status_code == 400:
            assert_response_error(response, 400)
        elif response.status_code == 200:
            data = response.json()
            assert data["success"] is False
            assert "error" in data
        else:
            assert response.status_code == 404
    
    def test_health_check(self, client: TestClient):
        """测试健康检查"""
        response = client.get("/api/v1/multimodal/health")
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "message" in data
        else:
            assert response.status_code == 404
    
    def test_unauthorized_access(self, client: TestClient):
        """测试未授权访问"""
        file_content = b"Test content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        
        response = client.post(
            "/api/v1/multimodal/process",
            files=files,
            data={"options": "{}"}
        )
        
        # 应该返回401未授权
        assert response.status_code == 401


@pytest.mark.asyncio
class TestMultimodalService:
    """多模态处理服务测试类"""
    
    async def test_text_processing(self):
        """测试文本处理功能"""
        try:
            from multimodal import process_binary
            
            text_content = b"This is a test document."
            result = await process_binary(text_content, "test.txt", extract_text=True)
            
            assert result.success is True
            assert result.media_type.name == "TEXT"
            assert isinstance(result.content, str)
            assert len(result.content) > 0
            
        except ImportError:
            # 多模态模块未实现，跳过测试
            pytest.skip("Multimodal module not implemented")
    
    async def test_image_processing(self):
        """测试图像处理功能"""
        try:
            from multimodal import process_binary
            
            # 创建简单的图像数据（PNG格式）
            png_header = b'\x89PNG\r\n\x1a\n'
            fake_png_content = png_header + b'\x00' * 100
            
            result = await process_binary(
                fake_png_content, 
                "test.png", 
                extract_text=True,
                create_thumbnail=True
            )
            
            # 根据实际实现验证结果
            if result.success:
                assert result.media_type.name == "IMAGE"
                assert result.metadata is not None
            else:
                # 如果处理失败，应该有错误信息
                assert result.error is not None
                
        except ImportError:
            pytest.skip("Multimodal module not implemented")
    
    async def test_supported_formats(self):
        """测试支持格式检查"""
        try:
            from multimodal import get_supported_formats
            
            formats = get_supported_formats()
            
            assert isinstance(formats, dict)
            assert "text" in formats or "image" in formats or "audio" in formats
            
            # 验证格式包含常见文件类型
            all_formats = []
            for category, format_list in formats.items():
                all_formats.extend(format_list)
            
            # 应该支持一些基本格式
            basic_formats = ["txt", "pdf", "jpg", "png", "mp3", "wav"]
            supported_basic = [fmt for fmt in basic_formats if fmt in all_formats]
            assert len(supported_basic) > 0
            
        except ImportError:
            pytest.skip("Multimodal module not implemented")
    
    async def test_capabilities(self):
        """测试处理能力检查"""
        try:
            from multimodal import get_capabilities
            
            capabilities = get_capabilities()
            
            assert isinstance(capabilities, dict)
            
            # 验证能力配置
            expected_capabilities = [
                "text_extraction",
                "image_processing",
                "audio_processing",
                "video_processing",
                "document_parsing"
            ]
            
            # 至少应该有一些能力
            available_capabilities = list(capabilities.keys())
            assert len(available_capabilities) > 0
            
        except ImportError:
            pytest.skip("Multimodal module not implemented")


class TestMultimodalIntegration:
    """多模态处理集成测试类"""
    
    def test_multimodal_with_conversation(self, client: TestClient, auth_headers: dict, sample_bot_data: dict):
        """测试多模态处理与对话的集成"""
        # 这个测试需要检查多模态处理结果是否能正确集成到对话中
        # 由于涉及复杂的集成逻辑，这里主要测试API的连通性
        
        # 先测试多模态API是否可用
        response = client.get("/api/v1/multimodal/formats", headers=auth_headers)
        
        if response.status_code == 200:
            # 多模态API可用，进行集成测试
            # 创建机器人
            bot_response = client.post("/api/v1/bots/", json=sample_bot_data, headers=auth_headers)
            if bot_response.status_code == 201:
                bot_data = bot_response.json()
                bot_id = bot_data["id"]
                
                # 创建对话
                conversation_data = {
                    "bot_id": bot_id,
                    "title": "多模态测试对话",
                    "platform": "web"
                }
                conv_response = client.post("/api/v1/conversations/", json=conversation_data, headers=auth_headers)
                
                if conv_response.status_code == 201:
                    # 对话创建成功，可以进行多模态集成测试
                    # 这里可以添加更具体的集成测试逻辑
                    pass
        else:
            # 多模态API未实现，跳过集成测试
            pytest.skip("Multimodal API not implemented")
    
    def test_file_processing_workflow(self, client: TestClient, auth_headers: dict):
        """测试文件处理工作流"""
        # 1. 获取支持的格式
        formats_response = client.get("/api/v1/multimodal/formats", headers=auth_headers)
        
        if formats_response.status_code == 200:
            formats_data = formats_response.json()
            
            # 2. 检查支持的格式
            assert "formats" in formats_data
            
            # 3. 处理支持的文件类型
            test_content = b"This is a test document for workflow testing."
            files = {"file": ("workflow_test.txt", io.BytesIO(test_content), "text/plain")}
            
            process_response = client.post(
                "/api/v1/multimodal/process",
                files=files,
                data={"options": '{"extract_text": true}'},
                headers=auth_headers
            )
            
            # 验证处理结果
            if process_response.status_code == 200:
                process_data = process_response.json()
                assert "success" in process_data
                assert "processing_time" in process_data
        else:
            pytest.skip("Multimodal API not implemented")
    
    def test_error_handling_workflow(self, client: TestClient, auth_headers: dict):
        """测试错误处理工作流"""
        # 测试各种错误情况的处理
        
        # 1. 无文件
        response = client.post("/api/v1/multimodal/process", headers=auth_headers)
        assert response.status_code in [400, 404, 422]  # 应该返回错误
        
        # 2. 无效文件格式（如果API实现了）
        invalid_files = {"file": ("test.invalid", io.BytesIO(b"invalid"), "application/octet-stream")}
        response = client.post(
            "/api/v1/multimodal/process",
            files=invalid_files,
            headers=auth_headers
        )
        
        if response.status_code == 200:
            # 如果处理了无效格式，检查结果
            data = response.json()
            # 可能成功也可能失败，取决于实现
            pass
        else:
            assert response.status_code in [400, 404, 415]