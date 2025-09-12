"""
多模态处理模块主入口
"""

import logging
from typing import Dict, List, Optional, Any
from .base import multimodal_processor, MediaType, ProcessingResult
from .image_processor import register_image_processors
from .audio_processor import register_audio_processors
from .video_processor import register_video_processors
from .document_processor import register_document_processors


# 初始化日志
logger = logging.getLogger(__name__)


def initialize_multimodal_processor():
    """初始化多模态处理器"""
    try:
        # 注册各种处理器
        register_image_processors(multimodal_processor)
        register_audio_processors(multimodal_processor)
        register_video_processors(multimodal_processor)
        register_document_processors(multimodal_processor)
        
        logger.info("Multimodal processor initialized successfully")
        
        # 输出支持的格式
        supported_formats = multimodal_processor.get_supported_formats()
        for media_type, formats in supported_formats.items():
            logger.info(f"{media_type.title()} formats: {', '.join(formats)}")
        
    except Exception as e:
        logger.error(f"Failed to initialize multimodal processor: {e}")
        raise


# 导出的便捷函数
async def process_file(file_path: str, **kwargs) -> ProcessingResult:
    """
    处理文件的便捷函数
    
    Args:
        file_path: 文件路径
        **kwargs: 处理选项
            - extract_text: 是否提取文本 (bool)
            - extract_images: 是否提取图像 (bool)
            - extract_audio: 是否提取音频 (bool)
            - transcribe: 是否转录音频 (bool)
            - detect_faces: 是否检测人脸 (bool)
            - resize: 调整大小 (tuple/int/float)
            - normalize: 是否标准化 (bool)
            - compress: 是否压缩 (bool)
            - convert_format: 转换格式 (str)
            - page_range: 页面范围 (tuple)
            - max_rows: 最大行数 (int)
    
    Returns:
        ProcessingResult: 处理结果
    """
    return await multimodal_processor.process_file(file_path, **kwargs)


async def process_binary(binary_data: bytes, filename: str, **kwargs) -> ProcessingResult:
    """
    处理二进制数据的便捷函数
    
    Args:
        binary_data: 二进制数据
        filename: 文件名
        **kwargs: 处理选项
    
    Returns:
        ProcessingResult: 处理结果
    """
    return await multimodal_processor.process_binary(binary_data, filename, **kwargs)


async def batch_process(file_paths: List[str], **kwargs) -> List[ProcessingResult]:
    """
    批量处理文件的便捷函数
    
    Args:
        file_paths: 文件路径列表
        **kwargs: 处理选项
    
    Returns:
        List[ProcessingResult]: 处理结果列表
    """
    return await multimodal_processor.batch_process(file_paths, **kwargs)


def get_supported_formats() -> Dict[str, List[str]]:
    """
    获取支持的文件格式
    
    Returns:
        Dict[str, List[str]]: 支持的格式字典
    """
    return multimodal_processor.get_supported_formats()


def get_statistics() -> Dict[str, Any]:
    """
    获取多模态处理器统计信息
    
    Returns:
        Dict[str, Any]: 统计信息
    """
    return multimodal_processor.get_statistics()


# 处理器类型映射
PROCESSOR_CAPABILITIES = {
    MediaType.IMAGE: {
        'description': '图像处理',
        'features': [
            '基本信息提取（尺寸、格式、色彩模式）',
            '元数据读取（EXIF信息）',
            '图像增强（对比度、锐度调整）',
            '尺寸调整和压缩',
            'OCR文字识别',
            '人脸检测',
            '边缘检测',
            'Base64编码转换'
        ],
        'supported_formats': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    },
    MediaType.AUDIO: {
        'description': '音频处理',
        'features': [
            '基本信息提取（时长、采样率、声道）',
            '音频特征分析（频谱、MFCC、音调）',
            '静音检测和修剪',
            '音量标准化',
            '格式转换',
            '语音转文字（Whisper/Google）',
            '音频效果处理（淡入淡出、变速）'
        ],
        'supported_formats': ['.wav', '.mp3', '.flac', '.ogg', '.m4a', '.mp4', '.wma']
    },
    MediaType.VIDEO: {
        'description': '视频处理',
        'features': [
            '基本信息提取（时长、分辨率、帧率）',
            '关键帧提取',
            '缩略图生成',
            '运动检测',
            '场景分析',
            '视频压缩和格式转换',
            'GIF预览生成',
            '音频轨道提取'
        ],
        'supported_formats': ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
    },
    MediaType.DOCUMENT: {
        'description': '文档处理',
        'features': [
            'PDF文本和图像提取',
            'Word文档解析',
            'Excel数据分析',
            'PowerPoint内容提取',
            '文本编码检测',
            '结构化数据解析（CSV、JSON、XML）',
            '代码文件分析',
            '元数据提取'
        ],
        'supported_formats': ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.txt', '.md', '.csv', '.json', '.xml', '.html']
    }
}


def get_capabilities() -> Dict[str, Any]:
    """
    获取多模态处理器能力描述
    
    Returns:
        Dict[str, Any]: 能力描述
    """
    return {
        'overview': '多模态文件处理系统，支持图像、音频、视频和文档的智能分析和处理',
        'media_types': {
            media_type.value: {
                'description': info['description'],
                'features': info['features'],
                'supported_formats': info['supported_formats']
            }
            for media_type, info in PROCESSOR_CAPABILITIES.items()
        },
        'common_features': [
            '自动文件类型检测',
            '多格式支持',
            '批量处理',
            '异步处理',
            '错误恢复',
            '进度跟踪',
            '缓存管理'
        ]
    }


# 模块导出
__all__ = [
    'initialize_multimodal_processor',
    'process_file',
    'process_binary',
    'batch_process',
    'get_supported_formats',
    'get_statistics',
    'get_capabilities',
    'MediaType',
    'ProcessingResult',
    'multimodal_processor'
]


# 自动初始化
try:
    initialize_multimodal_processor()
except Exception as e:
    logger.warning(f"Auto-initialization failed: {e}")
    # 不抛出异常，允许手动初始化