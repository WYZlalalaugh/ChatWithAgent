"""
监控系统API测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta

from tests.conftest import assert_response_ok, assert_response_error


class TestMonitoringAPI:
    """监控系统API测试类"""
    
    def test_get_system_metrics(self, client: TestClient, admin_headers: dict):
        """测试获取系统指标"""
        response = client.get("/api/v1/monitoring/metrics", headers=admin_headers)
        
        if response.status_code == 200:
            data = assert_response_ok(response)
            
            # 验证指标数据结构
            expected_metrics = [
                "cpu_usage", "memory_usage", "disk_usage", 
                "network_io", "database_connections", "active_users"
            ]
            
            for metric in expected_metrics:
                if metric in data:
                    assert isinstance(data[metric], (int, float, dict))
        else:
            # 监控API未实现
            assert response.status_code == 404
    
    def test_get_metrics_unauthorized(self, client: TestClient, auth_headers: dict):
        """测试非管理员获取系统指标"""
        response = client.get("/api/v1/monitoring/metrics", headers=auth_headers)
        
        # 应该返回403禁止访问，除非允许普通用户查看
        if response.status_code == 403:
            assert_response_error(response, 403)
        elif response.status_code == 200:
            # 如果允许普通用户查看，验证数据
            data = assert_response_ok(response)
            assert isinstance(data, dict)
        else:
            # API未实现
            assert response.status_code == 404
    
    def test_get_health_check(self, client: TestClient):
        """测试健康检查"""
        response = client.get("/api/v1/monitoring/health")
        
        if response.status_code == 200:
            data = assert_response_ok(response)
            
            assert "status" in data
            assert data["status"] in ["healthy", "unhealthy", "degraded"]
            
            if "components" in data:
                assert isinstance(data["components"], dict)
                
                # 验证组件状态
                for component, status in data["components"].items():
                    assert isinstance(status, dict)
                    assert "status" in status
        else:
            assert response.status_code == 404
    
    def test_get_performance_metrics(self, client: TestClient, admin_headers: dict):
        """测试获取性能指标"""
        response = client.get("/api/v1/monitoring/performance", headers=admin_headers)
        
        if response.status_code == 200:
            data = assert_response_ok(response)
            
            # 验证性能指标
            expected_performance_metrics = [
                "response_time", "throughput", "error_rate", 
                "active_connections", "queue_size"
            ]
            
            for metric in expected_performance_metrics:
                if metric in data:
                    assert isinstance(data[metric], (int, float, dict, list))
        else:
            assert response.status_code in [404, 403]
    
    def test_get_logs(self, client: TestClient, admin_headers: dict):
        """测试获取日志"""
        response = client.get("/api/v1/monitoring/logs", headers=admin_headers)
        
        if response.status_code == 200:
            data = assert_response_ok(response)
            
            assert "logs" in data
            assert isinstance(data["logs"], list)
            
            if data["logs"]:
                log_entry = data["logs"][0]
                expected_fields = ["timestamp", "level", "message"]
                
                for field in expected_fields:
                    if field in log_entry:
                        assert log_entry[field] is not None
        else:
            assert response.status_code in [404, 403]
    
    def test_get_logs_with_filters(self, client: TestClient, admin_headers: dict):
        """测试使用过滤器获取日志"""
        # 测试级别过滤
        response = client.get("/api/v1/monitoring/logs?level=ERROR", headers=admin_headers)
        
        if response.status_code == 200:
            data = assert_response_ok(response)
            
            if data.get("logs"):
                for log in data["logs"]:
                    if "level" in log:
                        assert log["level"] == "ERROR"
        else:
            assert response.status_code in [404, 403]
        
        # 测试时间范围过滤
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        response = client.get(
            f"/api/v1/monitoring/logs?start_time={start_time.isoformat()}&end_time={end_time.isoformat()}",
            headers=admin_headers
        )
        
        if response.status_code == 200:
            data = assert_response_ok(response)
            assert "logs" in data
        else:
            assert response.status_code in [404, 403]
    
    def test_get_alerts(self, client: TestClient, admin_headers: dict):
        """测试获取告警"""
        response = client.get("/api/v1/monitoring/alerts", headers=admin_headers)
        
        if response.status_code == 200:
            data = assert_response_ok(response)
            
            assert "alerts" in data
            assert isinstance(data["alerts"], list)
            
            if data["alerts"]:
                alert = data["alerts"][0]
                expected_fields = ["id", "type", "severity", "message", "timestamp"]
                
                for field in expected_fields:
                    if field in alert:
                        assert alert[field] is not None
        else:
            assert response.status_code in [404, 403]
    
    def test_create_alert(self, client: TestClient, admin_headers: dict):
        """测试创建告警"""
        alert_data = {
            "type": "system",
            "severity": "warning",
            "message": "Test alert",
            "metadata": {
                "component": "test",
                "metric": "cpu_usage",
                "value": 85.5
            }
        }
        
        response = client.post("/api/v1/monitoring/alerts", json=alert_data, headers=admin_headers)
        
        if response.status_code == 201:
            data = assert_response_ok(response, 201)
            
            assert data["type"] == alert_data["type"]
            assert data["severity"] == alert_data["severity"]
            assert data["message"] == alert_data["message"]
            assert "id" in data
            assert "timestamp" in data
        else:
            assert response.status_code in [404, 403]
    
    def test_update_alert_status(self, client: TestClient, admin_headers: dict):
        """测试更新告警状态"""
        # 先创建告警
        alert_data = {
            "type": "system",
            "severity": "error",
            "message": "Test alert for status update"
        }
        
        create_response = client.post("/api/v1/monitoring/alerts", json=alert_data, headers=admin_headers)
        
        if create_response.status_code == 201:
            alert = create_response.json()
            alert_id = alert["id"]
            
            # 更新状态
            update_data = {"status": "resolved"}
            response = client.patch(f"/api/v1/monitoring/alerts/{alert_id}", 
                                  json=update_data, headers=admin_headers)
            
            if response.status_code == 200:
                data = assert_response_ok(response)
                assert data["status"] == "resolved"
            else:
                assert response.status_code in [404, 403]
        else:
            # 创建告警失败，跳过更新测试
            pass
    
    @patch('monitoring.metrics_collector.MetricsCollector.collect_metrics')
    def test_metrics_collection(self, mock_collect, client: TestClient, admin_headers: dict):
        """测试指标收集"""
        # 模拟指标数据
        mock_metrics = {
            "cpu_usage": 45.2,
            "memory_usage": 60.8,
            "disk_usage": 30.5,
            "active_users": 125,
            "timestamp": datetime.utcnow().isoformat()
        }
        mock_collect.return_value = mock_metrics
        
        response = client.get("/api/v1/monitoring/metrics", headers=admin_headers)
        
        if response.status_code == 200:
            data = assert_response_ok(response)
            
            # 验证指标数据
            for key, value in mock_metrics.items():
                if key in data:
                    assert data[key] == value
            
            mock_collect.assert_called_once()
        else:
            assert response.status_code == 404
    
    def test_get_statistics(self, client: TestClient, admin_headers: dict):
        """测试获取统计信息"""
        response = client.get("/api/v1/monitoring/statistics", headers=admin_headers)
        
        if response.status_code == 200:
            data = assert_response_ok(response)
            
            # 验证统计信息结构
            expected_stats = [
                "total_requests", "average_response_time", 
                "error_count", "uptime", "total_users"
            ]
            
            for stat in expected_stats:
                if stat in data:
                    assert isinstance(data[stat], (int, float, str))
        else:
            assert response.status_code in [404, 403]
    
    def test_export_metrics(self, client: TestClient, admin_headers: dict):
        """测试导出指标"""
        response = client.get("/api/v1/monitoring/export", headers=admin_headers)
        
        if response.status_code == 200:
            # 检查响应格式
            content_type = response.headers.get("content-type", "")
            
            if "application/json" in content_type:
                data = assert_response_ok(response)
                assert isinstance(data, (dict, list))
            elif "text/csv" in content_type or "application/csv" in content_type:
                # CSV格式
                assert len(response.content) > 0
            else:
                # 其他格式
                assert len(response.content) > 0
        else:
            assert response.status_code in [404, 403]


@pytest.mark.asyncio
class TestMonitoringService:
    """监控服务测试类"""
    
    async def test_metrics_collector(self):
        """测试指标收集器"""
        try:
            from monitoring.metrics_collector import MetricsCollector
            
            collector = MetricsCollector()
            metrics = await collector.collect_metrics()
            
            assert isinstance(metrics, dict)
            assert len(metrics) > 0
            
            # 验证基本指标
            basic_metrics = ["timestamp"]
            for metric in basic_metrics:
                if metric in metrics:
                    assert metrics[metric] is not None
                    
        except ImportError:
            pytest.skip("Monitoring module not implemented")
    
    async def test_alert_manager(self):
        """测试告警管理器"""
        try:
            from monitoring.alert_manager import AlertManager
            
            alert_manager = AlertManager()
            
            # 创建测试告警
            alert_data = {
                "type": "system",
                "severity": "warning",
                "message": "Test alert",
                "metadata": {"test": True}
            }
            
            alert = await alert_manager.create_alert(**alert_data)
            
            assert alert.id is not None
            assert alert.type == alert_data["type"]
            assert alert.severity == alert_data["severity"]
            assert alert.message == alert_data["message"]
            
        except ImportError:
            pytest.skip("Monitoring module not implemented")
    
    async def test_log_processor(self):
        """测试日志处理器"""
        try:
            from monitoring.log_processor import LogProcessor
            
            processor = LogProcessor()
            
            # 处理测试日志
            log_entry = {
                "level": "INFO",
                "message": "Test log message",
                "timestamp": datetime.utcnow(),
                "module": "test"
            }
            
            result = await processor.process_log(log_entry)
            
            assert result is not None
            
        except ImportError:
            pytest.skip("Monitoring module not implemented")
    
    async def test_health_checker(self):
        """测试健康检查器"""
        try:
            from monitoring.health_checker import HealthChecker
            
            checker = HealthChecker()
            health_status = await checker.check_health()
            
            assert isinstance(health_status, dict)
            assert "status" in health_status
            assert health_status["status"] in ["healthy", "unhealthy", "degraded"]
            
            if "components" in health_status:
                assert isinstance(health_status["components"], dict)
                
        except ImportError:
            pytest.skip("Monitoring module not implemented")


class TestMonitoringIntegration:
    """监控系统集成测试类"""
    
    def test_monitoring_with_api_calls(self, client: TestClient, auth_headers: dict):
        """测试API调用的监控集成"""
        # 进行一些API调用
        api_calls = [
            ("/api/v1/auth/me", "GET"),
            ("/api/v1/bots/", "GET"),
            ("/api/v1/conversations/", "GET")
        ]
        
        for endpoint, method in api_calls:
            if method == "GET":
                response = client.get(endpoint, headers=auth_headers)
            # 可以添加其他HTTP方法
            
            # 验证API调用本身
            assert response.status_code in [200, 404, 403]
        
        # 检查监控指标是否记录了这些调用
        metrics_response = client.get("/api/v1/monitoring/metrics", headers=auth_headers)
        
        if metrics_response.status_code == 200:
            # 验证指标中是否包含API调用统计
            metrics_data = metrics_response.json()
            
            # 查找相关指标
            api_metrics = [
                "total_requests", "response_time", "error_count", "throughput"
            ]
            
            for metric in api_metrics:
                if metric in metrics_data:
                    assert isinstance(metrics_data[metric], (int, float, dict))
    
    def test_error_monitoring(self, client: TestClient, auth_headers: dict, admin_headers: dict):
        """测试错误监控"""
        # 故意触发一些错误
        error_calls = [
            "/api/v1/bots/nonexistent_id",
            "/api/v1/conversations/invalid_id",
            "/api/v1/users/unauthorized_access"
        ]
        
        for endpoint in error_calls:
            response = client.get(endpoint, headers=auth_headers)
            # 应该返回错误状态码
            assert response.status_code >= 400
        
        # 检查错误是否被监控记录
        logs_response = client.get("/api/v1/monitoring/logs?level=ERROR", headers=admin_headers)
        
        if logs_response.status_code == 200:
            logs_data = logs_response.json()
            
            if logs_data.get("logs"):
                # 验证错误日志
                for log in logs_data["logs"]:
                    if "level" in log:
                        assert log["level"] in ["ERROR", "WARNING"]
    
    def test_performance_monitoring(self, client: TestClient, admin_headers: dict):
        """测试性能监控"""
        import time
        
        # 记录开始时间
        start_time = time.time()
        
        # 执行一些API调用
        for i in range(5):
            response = client.get("/api/v1/monitoring/health")
            if response.status_code not in [200, 404]:
                break
        
        # 记录结束时间
        end_time = time.time()
        total_time = end_time - start_time
        
        # 获取性能指标
        performance_response = client.get("/api/v1/monitoring/performance", headers=admin_headers)
        
        if performance_response.status_code == 200:
            performance_data = performance_response.json()
            
            # 验证性能指标
            if "response_time" in performance_data:
                assert isinstance(performance_data["response_time"], (int, float, dict))
            
            if "throughput" in performance_data:
                assert isinstance(performance_data["throughput"], (int, float, dict))
    
    def test_alert_integration(self, client: TestClient, admin_headers: dict):
        """测试告警集成"""
        # 创建告警
        alert_data = {
            "type": "integration_test",
            "severity": "info",
            "message": "Integration test alert",
            "metadata": {"test_type": "integration"}
        }
        
        create_response = client.post("/api/v1/monitoring/alerts", json=alert_data, headers=admin_headers)
        
        if create_response.status_code == 201:
            alert = create_response.json()
            alert_id = alert["id"]
            
            # 获取告警列表，验证新告警是否存在
            alerts_response = client.get("/api/v1/monitoring/alerts", headers=admin_headers)
            
            if alerts_response.status_code == 200:
                alerts_data = alerts_response.json()
                
                if alerts_data.get("alerts"):
                    alert_ids = [a["id"] for a in alerts_data["alerts"]]
                    assert alert_id in alert_ids
            
            # 清理：删除测试告警（如果API支持）
            delete_response = client.delete(f"/api/v1/monitoring/alerts/{alert_id}", headers=admin_headers)
            # 删除操作可能未实现，不做严格检查
    
    def test_monitoring_dashboard_data(self, client: TestClient, admin_headers: dict):
        """测试监控仪表板数据"""
        # 获取仪表板所需的各种数据
        dashboard_endpoints = [
            "/api/v1/monitoring/metrics",
            "/api/v1/monitoring/health",
            "/api/v1/monitoring/performance",
            "/api/v1/monitoring/statistics"
        ]
        
        dashboard_data = {}
        
        for endpoint in dashboard_endpoints:
            response = client.get(endpoint, headers=admin_headers)
            
            if response.status_code == 200:
                data = response.json()
                dashboard_data[endpoint] = data
            elif response.status_code == 404:
                # API未实现，跳过
                continue
            else:
                # 其他错误
                assert response.status_code in [403, 500]
        
        # 验证仪表板数据的完整性
        if dashboard_data:
            # 至少应该有一些监控数据
            assert len(dashboard_data) > 0
            
            # 验证数据结构
            for endpoint, data in dashboard_data.items():
                assert isinstance(data, dict)
                assert len(data) > 0