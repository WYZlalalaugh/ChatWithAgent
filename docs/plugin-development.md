# ChatAgent 插件开发指南

ChatAgent 提供了强大的插件系统，允许开发者扩展机器人的功能。本指南将详细介绍如何开发、测试和发布插件。

## 📋 目录

- [插件系统概述](#插件系统概述)
- [开发环境设置](#开发环境设置)
- [创建第一个插件](#创建第一个插件)
- [插件API参考](#插件api参考)
- [测试和调试](#测试和调试)
- [插件发布](#插件发布)
- [最佳实践](#最佳实践)

## 🔍 插件系统概述

### 插件架构

ChatAgent 插件系统基于事件驱动架构，支持以下特性：

- **工具调用**: 为 LLM 提供外部工具能力
- **消息处理**: 拦截和处理消息
- **数据存储**: 插件私有数据存储
- **API 集成**: 与外部服务集成

### 插件类型

1. **工具插件**: 为 LLM 提供函数调用能力
2. **处理器插件**: 处理消息和事件
3. **集成插件**: 与第三方服务集成

## 🛠️ 开发环境设置

### 插件目录结构

```
plugins/my-plugin/
├── plugin.py          # 插件主文件
├── config.json        # 插件配置
├── requirements.txt   # Python 依赖
├── README.md          # 插件文档
└── tests/             # 测试文件
    └── test_plugin.py
```

### 基础配置文件

创建 `config.json`:

```json
{
    "id": "my-plugin",
    "name": "我的插件",
    "version": "1.0.0",
    "description": "这是一个示例插件",
    "author": "Your Name",
    "license": "MIT",
    "config_schema": {
        "api_key": {
            "type": "string",
            "required": true,
            "description": "API密钥"
        }
    },
    "permissions": ["network", "storage", "llm_tools"]
}
```

## 🚀 创建第一个插件

### 天气查询插件示例

创建 `plugin.py`:

```python
"""天气查询插件"""

import asyncio
import logging
from typing import Dict, Any, Optional
import httpx

from plugins.base import BasePlugin, PluginError
from plugins.decorators import tool, event_handler
from plugins.types import ToolCall, ToolResult, Message, PluginConfig


class WeatherPlugin(BasePlugin):
    """天气查询插件"""
    
    def __init__(self, config: PluginConfig):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.timeout = config.get("timeout", 30)
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """初始化插件"""
        if not self.api_key:
            raise PluginError("Weather API key is required")
        
        # 测试 API 连接
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/weather",
                    params={"q": "Beijing", "appid": self.api_key}
                )
                response.raise_for_status()
                return True
        except Exception as e:
            raise PluginError(f"Weather API connection failed: {e}")
    
    @tool(
        name="get_weather",
        description="获取指定城市的当前天气信息",
        parameters={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，例如：北京、上海"
                }
            },
            "required": ["city"]
        }
    )
    async def get_weather(self, call: ToolCall) -> ToolResult:
        """获取天气信息"""
        try:
            city = call.parameters.get("city")
            if not city:
                return ToolResult(success=False, error="城市名称不能为空")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/weather",
                    params={
                        "q": city,
                        "appid": self.api_key,
                        "units": "metric",
                        "lang": "zh_cn"
                    }
                )
                
                if response.status_code == 404:
                    return ToolResult(
                        success=False,
                        error=f"未找到城市 '{city}' 的天气信息"
                    )
                
                response.raise_for_status()
                data = response.json()
                
                # 格式化天气信息
                weather_info = self._format_weather_data(data)
                
                return ToolResult(
                    success=True,
                    data=weather_info,
                    display_text=self._format_weather_display(weather_info)
                )
                
        except Exception as e:
            self.logger.error(f"Weather query failed: {e}")
            return ToolResult(
                success=False,
                error=f"获取天气信息失败: {str(e)}"
            )
    
    @event_handler("message_received")
    async def on_message_received(self, message: Message) -> Optional[Message]:
        """处理接收到的消息"""
        content = message.content.lower()
        
        # 检测天气查询意图
        weather_keywords = ["天气", "weather", "温度"]
        if any(keyword in content for keyword in weather_keywords):
            # 记录天气查询统计
            await self.increment_counter("weather_queries")
        
        return message
    
    def _format_weather_data(self, data: Dict) -> Dict:
        """格式化天气数据"""
        return {
            "city": data["name"],
            "country": data["sys"]["country"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "weather": data["weather"][0]["description"]
        }
    
    def _format_weather_display(self, weather: Dict) -> str:
        """格式化天气显示文本"""
        return f"""
🌤️ {weather['city']}, {weather['country']} 当前天气

🌡️ 温度: {weather['temperature']}°C (体感 {weather['feels_like']}°C)
☁️ 天气: {weather['weather']}
💧 湿度: {weather['humidity']}%
        """.strip()


def create_plugin(config: PluginConfig) -> WeatherPlugin:
    """创建插件实例"""
    return WeatherPlugin(config)
```

## 📚 插件API参考

### 基础插件类

```python
from plugins.base import BasePlugin

class MyPlugin(BasePlugin):
    async def initialize(self) -> bool:
        """插件初始化，返回True表示成功"""
        pass
    
    async def cleanup(self):
        """插件清理，释放资源"""
        pass
```

### 工具装饰器

```python
from plugins.decorators import tool

@tool(
    name="tool_name",
    description="工具描述",
    parameters={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "参数描述"}
        },
        "required": ["param1"]
    }
)
async def my_tool(self, call: ToolCall) -> ToolResult:
    return ToolResult(success=True, data={"result": "success"})
```

### 事件处理器

```python
from plugins.decorators import event_handler

@event_handler("message_received")
async def on_message(self, message: Message) -> Optional[Message]:
    return message

@event_handler("conversation_started")
async def on_conversation_start(self, conversation_id: str, context: Dict):
    pass
```

### 数据存储

```python
# 存储插件数据
await self.set_data("key", "value")

# 获取插件数据
value = await self.get_data("key", default_value)

# 删除插件数据
await self.delete_data("key")

# 统计和指标
await self.increment_counter("api_calls")
await self.record_metric("response_time", 0.5)
```

## 🧪 测试和调试

### 单元测试示例

```python
import pytest
from unittest.mock import AsyncMock, patch
from my_plugin.plugin import WeatherPlugin

@pytest.mark.asyncio
async def test_get_weather_success():
    """测试天气查询成功"""
    config = {"api_key": "test_api_key"}
    plugin = WeatherPlugin(config)
    
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Beijing",
            "sys": {"country": "CN"},
            "main": {"temp": 25, "feels_like": 27, "humidity": 60},
            "weather": [{"description": "晴天"}]
        }
        mock_get.return_value.__aenter__.return_value = mock_response
        
        call = ToolCall(name="get_weather", parameters={"city": "Beijing"})
        result = await plugin.get_weather(call)
        
        assert result.success is True
        assert "Beijing" in result.display_text
```

## 📦 插件发布

### 1. 打包插件

```python
import zipfile
from pathlib import Path

def package_plugin():
    plugin_dir = Path(__file__).parent
    package_name = "my-plugin-1.0.0.zip"
    
    with zipfile.ZipFile(package_name, 'w') as zipf:
        files = ["plugin.py", "config.json", "requirements.txt", "README.md"]
        for file in files:
            if (plugin_dir / file).exists():
                zipf.write(plugin_dir / file, file)
```

### 2. 发布到插件市场

```bash
# 安装CLI工具
pip install chatagent-cli

# 登录并发布
chatagent-cli login
chatagent-cli publish my-plugin-1.0.0.zip
```

## 💡 最佳实践

### 1. 代码质量

- 使用类型提示
- 添加详细的文档字符串
- 实施适当的错误处理
- 编写全面的测试

### 2. 性能优化

- 使用异步操作
- 实施缓存机制
- 设置合理的超时
- 优化API调用频率

### 3. 安全考虑

- 验证输入参数
- 使用安全的API调用
- 保护敏感信息
- 实施访问控制

### 4. 用户体验

- 提供清晰的错误消息
- 支持多语言
- 优化响应时间
- 提供详细的帮助文档

## 📖 示例插件

查看更多插件示例：

- [计算器插件](./examples/calculator-plugin/)
- [翻译插件](./examples/translator-plugin/)
- [数据库查询插件](./examples/database-plugin/)
- [邮件发送插件](./examples/email-plugin/)

## 🆘 获取帮助

- [API 文档](./API.md)
- [GitHub Issues](https://github.com/chatagent/chatagent/issues)
- [开发者社区](https://github.com/chatagent/chatagent/discussions)
- [插件市场](https://plugins.chatagent.dev)

---

通过遵循本指南，您可以开发出功能强大、用户友好的 ChatAgent 插件。祝您开发愉快！