"""
大语言模型服务集成
"""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from enum import Enum
from loguru import logger

from app.models.plugin import Model
from app.config import settings


class ModelType(str, Enum):
    """模型类型枚举"""
    CHAT = "chat"
    EMBEDDING = "embedding"
    IMAGE = "image"
    AUDIO = "audio"


class ModelProvider(str, Enum):
    """模型提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    GOOGLE = "google"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"


class ModelResponse:
    """模型响应"""
    
    def __init__(
        self,
        content: str = "",
        model: str = "",
        usage: Optional[Dict[str, int]] = None,
        finish_reason: str = "stop",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.content = content
        self.model = model
        self.usage = usage or {}
        self.finish_reason = finish_reason
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()


class StreamingResponse:
    """流式响应"""
    
    def __init__(
        self,
        generator: AsyncGenerator[str, None],
        model: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.generator = generator
        self.model = model
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()


class BaseLLMProvider(ABC):
    """LLM 提供商基类"""
    
    def __init__(self, model_config: Dict[str, Any]):
        self.model_config = model_config
        self.provider_name = self.get_provider_name()
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """获取提供商名称"""
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[ModelResponse, StreamingResponse]:
        """聊天补全"""
        pass
    
    @abstractmethod
    async def embedding(
        self,
        texts: Union[str, List[str]],
        model: str,
        **kwargs
    ) -> List[List[float]]:
        """文本嵌入"""
        pass
    
    async def image_generation(
        self,
        prompt: str,
        model: str,
        **kwargs
    ) -> Optional[str]:
        """图像生成（可选实现）"""
        raise NotImplementedError(f"{self.provider_name} 不支持图像生成")
    
    async def audio_transcription(
        self,
        audio_file: str,
        model: str,
        **kwargs
    ) -> Optional[str]:
        """音频转录（可选实现）"""
        raise NotImplementedError(f"{self.provider_name} 不支持音频转录")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI 提供商"""
    
    def __init__(self, model_config: Dict[str, Any]):
        super().__init__(model_config)
        self.api_key = model_config.get("api_key") or settings.OPENAI_API_KEY
        self.base_url = model_config.get("base_url", "https://api.openai.com/v1")
        self.organization = model_config.get("organization")
        
        # 初始化客户端
        import openai
        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            organization=self.organization
        )
    
    def get_provider_name(self) -> str:
        return "openai"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[ModelResponse, StreamingResponse]:
        """OpenAI 聊天补全"""
        try:
            start_time = time.time()
            
            # 准备请求参数
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": stream,
                **kwargs
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            if stream:
                # 流式响应
                async def stream_generator():
                    async for chunk in await self.client.chat.completions.create(**params):
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                
                return StreamingResponse(
                    generator=stream_generator(),
                    model=model,
                    metadata={"provider": self.provider_name}
                )
            else:
                # 普通响应
                response = await self.client.chat.completions.create(**params)
                
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else {}
                
                return ModelResponse(
                    content=response.choices[0].message.content or "",
                    model=response.model,
                    usage=usage,
                    finish_reason=response.choices[0].finish_reason or "stop",
                    metadata={
                        "provider": self.provider_name,
                        "response_time": time.time() - start_time
                    }
                )
                
        except Exception as e:
            logger.error(f"OpenAI 聊天补全失败: {e}")
            raise
    
    async def embedding(
        self,
        texts: Union[str, List[str]],
        model: str,
        **kwargs
    ) -> List[List[float]]:
        """OpenAI 文本嵌入"""
        try:
            if isinstance(texts, str):
                texts = [texts]
            
            response = await self.client.embeddings.create(
                model=model,
                input=texts,
                **kwargs
            )
            
            return [data.embedding for data in response.data]
            
        except Exception as e:
            logger.error(f"OpenAI 文本嵌入失败: {e}")
            raise
    
    async def image_generation(
        self,
        prompt: str,
        model: str = "dall-e-3",
        **kwargs
    ) -> Optional[str]:
        """OpenAI 图像生成"""
        try:
            response = await self.client.images.generate(
                model=model,
                prompt=prompt,
                **kwargs
            )
            
            return response.data[0].url if response.data else None
            
        except Exception as e:
            logger.error(f"OpenAI 图像生成失败: {e}")
            raise
    
    async def audio_transcription(
        self,
        audio_file: str,
        model: str = "whisper-1",
        **kwargs
    ) -> Optional[str]:
        """OpenAI 音频转录"""
        try:
            with open(audio_file, "rb") as f:
                response = await self.client.audio.transcriptions.create(
                    model=model,
                    file=f,
                    **kwargs
                )
            
            return response.text
            
        except Exception as e:
            logger.error(f"OpenAI 音频转录失败: {e}")
            raise


class AnthropicProvider(BaseLLMProvider):
    """Anthropic 提供商"""
    
    def __init__(self, model_config: Dict[str, Any]):
        super().__init__(model_config)
        self.api_key = model_config.get("api_key") or settings.ANTHROPIC_API_KEY
        
        # 初始化客户端
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
    
    def get_provider_name(self) -> str:
        return "anthropic"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[ModelResponse, StreamingResponse]:
        """Anthropic 聊天补全"""
        try:
            start_time = time.time()
            
            # 转换消息格式
            system_message = ""
            anthropic_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # 准备请求参数
            params = {
                "model": model,
                "messages": anthropic_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 2048,
                "stream": stream,
                **kwargs
            }
            
            if system_message:
                params["system"] = system_message
            
            if stream:
                # 流式响应
                async def stream_generator():
                    async for chunk in await self.client.messages.create(**params):
                        if chunk.type == "content_block_delta" and chunk.delta.text:
                            yield chunk.delta.text
                
                return StreamingResponse(
                    generator=stream_generator(),
                    model=model,
                    metadata={"provider": self.provider_name}
                )
            else:
                # 普通响应
                response = await self.client.messages.create(**params)
                
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                } if response.usage else {}
                
                content = ""
                if response.content:
                    content = response.content[0].text if response.content[0].type == "text" else ""
                
                return ModelResponse(
                    content=content,
                    model=response.model,
                    usage=usage,
                    finish_reason=response.stop_reason or "stop",
                    metadata={
                        "provider": self.provider_name,
                        "response_time": time.time() - start_time
                    }
                )
                
        except Exception as e:
            logger.error(f"Anthropic 聊天补全失败: {e}")
            raise
    
    async def embedding(
        self,
        texts: Union[str, List[str]],
        model: str,
        **kwargs
    ) -> List[List[float]]:
        """Anthropic 不支持嵌入"""
        raise NotImplementedError("Anthropic 不支持文本嵌入")


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI 提供商"""
    
    def __init__(self, model_config: Dict[str, Any]):
        super().__init__(model_config)
        self.api_key = model_config.get("api_key") or settings.AZURE_OPENAI_API_KEY
        self.endpoint = model_config.get("endpoint") or settings.AZURE_OPENAI_ENDPOINT
        self.api_version = model_config.get("api_version") or settings.AZURE_OPENAI_API_VERSION
        
        # 初始化客户端
        import openai
        self.client = openai.AsyncAzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version
        )
    
    def get_provider_name(self) -> str:
        return "azure_openai"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[ModelResponse, StreamingResponse]:
        """Azure OpenAI 聊天补全"""
        # 实现与 OpenAI 类似，但使用不同的客户端
        try:
            start_time = time.time()
            
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": stream,
                **kwargs
            }
            
            if max_tokens:
                params["max_tokens"] = max_tokens
            
            if stream:
                async def stream_generator():
                    async for chunk in await self.client.chat.completions.create(**params):
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                
                return StreamingResponse(
                    generator=stream_generator(),
                    model=model,
                    metadata={"provider": self.provider_name}
                )
            else:
                response = await self.client.chat.completions.create(**params)
                
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else {}
                
                return ModelResponse(
                    content=response.choices[0].message.content or "",
                    model=response.model,
                    usage=usage,
                    finish_reason=response.choices[0].finish_reason or "stop",
                    metadata={
                        "provider": self.provider_name,
                        "response_time": time.time() - start_time
                    }
                )
                
        except Exception as e:
            logger.error(f"Azure OpenAI 聊天补全失败: {e}")
            raise
    
    async def embedding(
        self,
        texts: Union[str, List[str]],
        model: str,
        **kwargs
    ) -> List[List[float]]:
        """Azure OpenAI 文本嵌入"""
        try:
            if isinstance(texts, str):
                texts = [texts]
            
            response = await self.client.embeddings.create(
                model=model,
                input=texts,
                **kwargs
            )
            
            return [data.embedding for data in response.data]
            
        except Exception as e:
            logger.error(f"Azure OpenAI 文本嵌入失败: {e}")
            raise


class LLMService:
    """大语言模型服务"""
    
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.models: Dict[str, Model] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化提供商"""
        # 注册默认提供商
        if settings.OPENAI_API_KEY:
            self.register_provider("openai", OpenAIProvider, {
                "api_key": settings.OPENAI_API_KEY
            })
        
        if settings.ANTHROPIC_API_KEY:
            self.register_provider("anthropic", AnthropicProvider, {
                "api_key": settings.ANTHROPIC_API_KEY
            })
        
        if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
            self.register_provider("azure_openai", AzureOpenAIProvider, {
                "api_key": settings.AZURE_OPENAI_API_KEY,
                "endpoint": settings.AZURE_OPENAI_ENDPOINT,
                "api_version": settings.AZURE_OPENAI_API_VERSION
            })
    
    def register_provider(
        self, 
        name: str, 
        provider_class: type, 
        config: Dict[str, Any]
    ):
        """注册提供商"""
        try:
            provider = provider_class(config)
            self.providers[name] = provider
            logger.info(f"LLM 提供商已注册: {name}")
        except Exception as e:
            logger.error(f"注册 LLM 提供商失败 {name}: {e}")
    
    def register_model(self, model: Model):
        """注册模型"""
        self.models[model.id] = model
        logger.info(f"LLM 模型已注册: {model.name} ({model.provider})")
    
    async def chat(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[ModelResponse, StreamingResponse]:
        """聊天补全"""
        model = self.models.get(model_id)
        if not model:
            raise ValueError(f"模型未找到: {model_id}")
        
        provider = self.providers.get(model.provider)
        if not provider:
            raise ValueError(f"提供商未找到: {model.provider}")
        
        # 合并模型配置和请求参数
        model_params = model.parameters or {}
        final_params = {**model_params, **kwargs}
        
        return await provider.chat(
            messages=messages,
            model=model.api_config.get("model", model.name),
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            **final_params
        )
    
    async def embedding(
        self,
        model_id: str,
        texts: Union[str, List[str]],
        **kwargs
    ) -> List[List[float]]:
        """文本嵌入"""
        model = self.models.get(model_id)
        if not model:
            raise ValueError(f"模型未找到: {model_id}")
        
        if model.model_type != ModelType.EMBEDDING:
            raise ValueError(f"模型类型不支持嵌入: {model.model_type}")
        
        provider = self.providers.get(model.provider)
        if not provider:
            raise ValueError(f"提供商未找到: {model.provider}")
        
        return await provider.embedding(
            texts=texts,
            model=model.api_config.get("model", model.name),
            **kwargs
        )
    
    async def image_generation(
        self,
        model_id: str,
        prompt: str,
        **kwargs
    ) -> Optional[str]:
        """图像生成"""
        model = self.models.get(model_id)
        if not model:
            raise ValueError(f"模型未找到: {model_id}")
        
        if model.model_type != ModelType.IMAGE:
            raise ValueError(f"模型类型不支持图像生成: {model.model_type}")
        
        provider = self.providers.get(model.provider)
        if not provider:
            raise ValueError(f"提供商未找到: {model.provider}")
        
        return await provider.image_generation(
            prompt=prompt,
            model=model.api_config.get("model", model.name),
            **kwargs
        )
    
    async def audio_transcription(
        self,
        model_id: str,
        audio_file: str,
        **kwargs
    ) -> Optional[str]:
        """音频转录"""
        model = self.models.get(model_id)
        if not model:
            raise ValueError(f"模型未找到: {model_id}")
        
        if model.model_type != ModelType.AUDIO:
            raise ValueError(f"模型类型不支持音频转录: {model.model_type}")
        
        provider = self.providers.get(model.provider)
        if not provider:
            raise ValueError(f"提供商未找到: {model.provider}")
        
        return await provider.audio_transcription(
            audio_file=audio_file,
            model=model.api_config.get("model", model.name),
            **kwargs
        )
    
    def list_models(self) -> List[Dict[str, Any]]:
        """列出所有模型"""
        return [
            {
                "id": model.id,
                "name": model.name,
                "provider": model.provider,
                "type": model.model_type,
                "is_active": model.is_active
            }
            for model in self.models.values()
        ]
    
    def list_providers(self) -> List[str]:
        """列出所有提供商"""
        return list(self.providers.keys())


# 全局 LLM 服务实例
llm_service = LLMService()


async def get_llm_service() -> LLMService:
    """获取 LLM 服务实例"""
    return llm_service