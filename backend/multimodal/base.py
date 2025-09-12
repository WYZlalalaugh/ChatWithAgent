"""
多模态处理基础框架
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, BinaryIO
from enum import Enum
import mimetypes
import tempfile
import os
from pathlib import Path

from app.config import settings


class MediaType(Enum):
    """媒体类型枚举"""
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


class ProcessingResult:
    """处理结果"""
    
    def __init__(
        self,
        success: bool,
        media_type: MediaType,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        processed_files: Optional[List[str]] = None
    ):
        self.success = success
        self.media_type = media_type
        self.content = content
        self.metadata = metadata or {}
        self.error = error
        self.processed_files = processed_files or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'media_type': self.media_type.value,
            'content': self.content,
            'metadata': self.metadata,
            'error': self.error,
            'processed_files': self.processed_files
        }


class BaseMediaProcessor(ABC):
    """媒体处理器基类"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.supported_formats: List[str] = []
        self.max_file_size = 50 * 1024 * 1024  # 50MB default
    
    @abstractmethod
    async def process(self, file_path: str, **kwargs) -> ProcessingResult:
        """处理媒体文件"""
        pass
    
    @abstractmethod
    def supports_format(self, file_extension: str) -> bool:
        """检查是否支持指定格式"""
        pass
    
    def get_media_type(self, file_path: str) -> MediaType:
        """获取媒体类型"""
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if not mime_type:
            return MediaType.UNKNOWN
        
        if mime_type.startswith('image/'):
            return MediaType.IMAGE
        elif mime_type.startswith('audio/'):
            return MediaType.AUDIO
        elif mime_type.startswith('video/'):
            return MediaType.VIDEO
        elif mime_type.startswith('application/') or mime_type.startswith('text/'):
            return MediaType.DOCUMENT
        else:
            return MediaType.UNKNOWN
    
    def validate_file(self, file_path: str) -> bool:
        """验证文件"""
        try:
            if not os.path.exists(file_path):
                return False
            
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                self.logger.warning(f"File size {file_size} exceeds limit {self.max_file_size}")
                return False
            
            # 检查文件格式
            file_extension = Path(file_path).suffix.lower()
            if not self.supports_format(file_extension):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"File validation error: {e}")
            return False


class MultimodalProcessor:
    """多模态处理器管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.processors: Dict[MediaType, List[BaseMediaProcessor]] = {
            MediaType.IMAGE: [],
            MediaType.AUDIO: [],
            MediaType.VIDEO: [],
            MediaType.DOCUMENT: []
        }
        self.temp_dir = tempfile.mkdtemp(prefix="multimodal_")
    
    def register_processor(self, media_type: MediaType, processor: BaseMediaProcessor):
        """注册处理器"""
        if media_type not in self.processors:
            self.processors[media_type] = []
        
        self.processors[media_type].append(processor)
        self.logger.info(f"Registered {processor.__class__.__name__} for {media_type.value}")
    
    def get_processors(self, media_type: MediaType) -> List[BaseMediaProcessor]:
        """获取指定类型的处理器"""
        return self.processors.get(media_type, [])
    
    async def process_file(
        self,
        file_path: str,
        media_type: Optional[MediaType] = None,
        **kwargs
    ) -> ProcessingResult:
        """处理文件"""
        try:
            # 自动检测媒体类型
            if media_type is None:
                media_type = self._detect_media_type(file_path)
            
            if media_type == MediaType.UNKNOWN:
                return ProcessingResult(
                    success=False,
                    media_type=media_type,
                    error="Unsupported file type"
                )
            
            # 获取处理器
            processors = self.get_processors(media_type)
            if not processors:
                return ProcessingResult(
                    success=False,
                    media_type=media_type,
                    error=f"No processor available for {media_type.value}"
                )
            
            # 尝试使用支持的处理器
            file_extension = Path(file_path).suffix.lower()
            
            for processor in processors:
                if processor.supports_format(file_extension):
                    try:
                        result = await processor.process(file_path, **kwargs)
                        if result.success:
                            return result
                    except Exception as e:
                        self.logger.error(f"Processor {processor.__class__.__name__} failed: {e}")
                        continue
            
            return ProcessingResult(
                success=False,
                media_type=media_type,
                error="All processors failed"
            )
            
        except Exception as e:
            self.logger.error(f"File processing error: {e}")
            return ProcessingResult(
                success=False,
                media_type=media_type or MediaType.UNKNOWN,
                error=str(e)
            )
    
    async def process_binary(
        self,
        binary_data: bytes,
        filename: str,
        media_type: Optional[MediaType] = None,
        **kwargs
    ) -> ProcessingResult:
        """处理二进制数据"""
        try:
            # 保存为临时文件
            temp_file_path = os.path.join(self.temp_dir, filename)
            
            with open(temp_file_path, 'wb') as f:
                f.write(binary_data)
            
            # 处理文件
            result = await self.process_file(temp_file_path, media_type, **kwargs)
            
            # 清理临时文件
            try:
                os.remove(temp_file_path)
            except:
                pass
            
            return result
            
        except Exception as e:
            self.logger.error(f"Binary processing error: {e}")
            return ProcessingResult(
                success=False,
                media_type=media_type or MediaType.UNKNOWN,
                error=str(e)
            )
    
    async def batch_process(
        self,
        file_paths: List[str],
        **kwargs
    ) -> List[ProcessingResult]:
        """批量处理文件"""
        tasks = []
        
        for file_path in file_paths:
            task = self.process_file(file_path, **kwargs)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ProcessingResult(
                    success=False,
                    media_type=MediaType.UNKNOWN,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def _detect_media_type(self, file_path: str) -> MediaType:
        """检测媒体类型"""
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if not mime_type:
            return MediaType.UNKNOWN
        
        if mime_type.startswith('image/'):
            return MediaType.IMAGE
        elif mime_type.startswith('audio/'):
            return MediaType.AUDIO
        elif mime_type.startswith('video/'):
            return MediaType.VIDEO
        elif mime_type.startswith('application/') or mime_type.startswith('text/'):
            return MediaType.DOCUMENT
        else:
            return MediaType.UNKNOWN
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """获取支持的格式列表"""
        formats = {}
        
        for media_type, processors in self.processors.items():
            media_formats = set()
            for processor in processors:
                media_formats.update(processor.supported_formats)
            formats[media_type.value] = list(media_formats)
        
        return formats
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            'temp_dir': self.temp_dir,
            'processors': {}
        }
        
        for media_type, processors in self.processors.items():
            stats['processors'][media_type.value] = {
                'count': len(processors),
                'processors': [p.__class__.__name__ for p in processors]
            }
        
        return stats
    
    def cleanup(self):
        """清理资源"""
        try:
            # 清理临时目录
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")


# 全局多模态处理器实例
multimodal_processor = MultimodalProcessor()

# 便捷函数
async def process_file(file_path: str, **kwargs) -> ProcessingResult:
    """处理文件的便捷函数"""
    return await multimodal_processor.process_file(file_path, **kwargs)

async def process_binary(binary_data: bytes, filename: str, **kwargs) -> ProcessingResult:
    """处理二进制数据的便捷函数"""
    return await multimodal_processor.process_binary(binary_data, filename, **kwargs)

def get_supported_formats() -> Dict[str, List[str]]:
    """获取支持格式的便捷函数"""
    return multimodal_processor.get_supported_formats()