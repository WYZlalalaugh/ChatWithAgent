"""
图像处理器
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import base64
import io
from pathlib import Path

try:
    from PIL import Image, ImageEnhance, ImageFilter
    from PIL.ExifTags import TAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from .base import BaseMediaProcessor, ProcessingResult, MediaType


class PILImageProcessor(BaseMediaProcessor):
    """PIL图像处理器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        self.max_file_size = 20 * 1024 * 1024  # 20MB
    
    def supports_format(self, file_extension: str) -> bool:
        return file_extension.lower() in self.supported_formats
    
    async def process(self, file_path: str, **kwargs) -> ProcessingResult:
        """处理图像文件"""
        if not PIL_AVAILABLE:
            return ProcessingResult(
                success=False,
                media_type=MediaType.IMAGE,
                error="PIL not available"
            )
        
        try:
            if not self.validate_file(file_path):
                return ProcessingResult(
                    success=False,
                    media_type=MediaType.IMAGE,
                    error="File validation failed"
                )
            
            # 处理选项
            extract_text = kwargs.get('extract_text', False)
            resize = kwargs.get('resize', None)
            enhance = kwargs.get('enhance', False)
            get_metadata = kwargs.get('get_metadata', True)
            compress = kwargs.get('compress', False)
            
            with Image.open(file_path) as img:
                result_data = {
                    'original_size': img.size,
                    'mode': img.mode,
                    'format': img.format
                }
                
                content_parts = []
                processed_files = []
                
                # 提取元数据
                if get_metadata:
                    metadata = await self._extract_metadata(img)
                    result_data.update(metadata)
                
                # 图像增强
                if enhance:
                    enhanced_img = await self._enhance_image(img)
                    if enhanced_img:
                        enhanced_path = self._get_output_path(file_path, "_enhanced")
                        enhanced_img.save(enhanced_path)
                        processed_files.append(enhanced_path)
                        img = enhanced_img
                
                # 调整大小
                if resize:
                    resized_img = await self._resize_image(img, resize)
                    if resized_img:
                        resized_path = self._get_output_path(file_path, "_resized")
                        resized_img.save(resized_path)
                        processed_files.append(resized_path)
                        img = resized_img
                
                # 压缩
                if compress:
                    compressed_path = self._get_output_path(file_path, "_compressed")
                    await self._compress_image(img, compressed_path)
                    processed_files.append(compressed_path)
                
                # 文字识别
                if extract_text and TESSERACT_AVAILABLE:
                    text = await self._extract_text_ocr(img)
                    if text:
                        content_parts.append(f"图像中的文字：\n{text}")
                
                # 基本描述
                description = await self._generate_description(img, result_data)
                content_parts.append(description)
                
                # 转换为base64
                base64_data = await self._image_to_base64(img)
                result_data['base64'] = base64_data
                
                return ProcessingResult(
                    success=True,
                    media_type=MediaType.IMAGE,
                    content='\n'.join(content_parts),
                    metadata=result_data,
                    processed_files=processed_files
                )
                
        except Exception as e:
            self.logger.error(f"Image processing error: {e}")
            return ProcessingResult(
                success=False,
                media_type=MediaType.IMAGE,
                error=str(e)
            )
    
    async def _extract_metadata(self, img: Image.Image) -> Dict[str, Any]:
        """提取图像元数据"""
        metadata = {}
        
        try:
            # EXIF数据
            if hasattr(img, '_getexif') and img._getexif():
                exif_data = {}
                for tag_id, value in img._getexif().items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_data[tag] = value
                metadata['exif'] = exif_data
            
            # 基本信息
            metadata.update({
                'width': img.width,
                'height': img.height,
                'mode': img.mode,
                'format': img.format,
                'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
            })
            
        except Exception as e:
            self.logger.error(f"Metadata extraction error: {e}")
        
        return metadata
    
    async def _enhance_image(self, img: Image.Image) -> Optional[Image.Image]:
        """图像增强"""
        try:
            # 自动增强对比度和锐度
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)
            
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.1)
            
            return img
            
        except Exception as e:
            self.logger.error(f"Image enhancement error: {e}")
            return None
    
    async def _resize_image(self, img: Image.Image, size_spec: Any) -> Optional[Image.Image]:
        """调整图像大小"""
        try:
            if isinstance(size_spec, (list, tuple)) and len(size_spec) == 2:
                new_size = tuple(size_spec)
            elif isinstance(size_spec, int):
                # 等比例缩放
                ratio = size_spec / max(img.size)
                new_size = (int(img.width * ratio), int(img.height * ratio))
            else:
                return None
            
            return img.resize(new_size, Image.Resampling.LANCZOS)
            
        except Exception as e:
            self.logger.error(f"Image resize error: {e}")
            return None
    
    async def _compress_image(self, img: Image.Image, output_path: str):
        """压缩图像"""
        try:
            # 转换为RGB模式（如果需要）
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # 保存为JPEG，质量85
            img.save(output_path, 'JPEG', quality=85, optimize=True)
            
        except Exception as e:
            self.logger.error(f"Image compression error: {e}")
    
    async def _extract_text_ocr(self, img: Image.Image) -> Optional[str]:
        """使用OCR提取文字"""
        try:
            # 预处理图像以提高OCR准确性
            # 转换为灰度
            gray_img = img.convert('L')
            
            # 增强对比度
            enhancer = ImageEnhance.Contrast(gray_img)
            enhanced_img = enhancer.enhance(2.0)
            
            # OCR识别
            text = pytesseract.image_to_string(enhanced_img, lang='chi_sim+eng')
            
            # 清理文字
            text = text.strip()
            if len(text) > 0:
                return text
            
        except Exception as e:
            self.logger.error(f"OCR error: {e}")
        
        return None
    
    async def _generate_description(self, img: Image.Image, metadata: Dict[str, Any]) -> str:
        """生成图像描述"""
        try:
            width, height = img.size
            mode = img.mode
            format_name = img.format or "Unknown"
            
            # 计算宽高比
            aspect_ratio = width / height
            
            if aspect_ratio > 1.5:
                orientation = "横向"
            elif aspect_ratio < 0.67:
                orientation = "纵向"
            else:
                orientation = "方形"
            
            # 分析颜色
            colors = img.getcolors(maxcolors=256)
            dominant_colors = "多彩"
            if colors:
                # 简单的颜色分析
                total_pixels = width * height
                if len(colors) < 10:
                    dominant_colors = "单色调"
                elif len(colors) < 50:
                    dominant_colors = "少色彩"
            
            description = f"这是一张{orientation}的{format_name}图像，尺寸为{width}x{height}像素，颜色模式为{mode}，呈现{dominant_colors}特征。"
            
            # 添加文件大小信息
            if 'file_size' in metadata:
                size_mb = metadata['file_size'] / (1024 * 1024)
                description += f" 文件大小约{size_mb:.2f}MB。"
            
            return description
            
        except Exception as e:
            self.logger.error(f"Description generation error: {e}")
            return "图像分析失败"
    
    async def _image_to_base64(self, img: Image.Image) -> str:
        """转换图像为base64"""
        try:
            buffer = io.BytesIO()
            
            # 转换为RGB（如果需要）
            if img.mode in ('RGBA', 'LA'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            
            img.save(buffer, format='JPEG', quality=90)
            img_bytes = buffer.getvalue()
            
            return base64.b64encode(img_bytes).decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Base64 conversion error: {e}")
            return ""
    
    def _get_output_path(self, original_path: str, suffix: str) -> str:
        """获取输出文件路径"""
        path = Path(original_path)
        return str(path.parent / f"{path.stem}{suffix}{path.suffix}")


class OpenCVImageProcessor(BaseMediaProcessor):
    """OpenCV图像处理器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        self.max_file_size = 50 * 1024 * 1024  # 50MB
    
    def supports_format(self, file_extension: str) -> bool:
        return file_extension.lower() in self.supported_formats
    
    async def process(self, file_path: str, **kwargs) -> ProcessingResult:
        """处理图像文件"""
        if not CV2_AVAILABLE:
            return ProcessingResult(
                success=False,
                media_type=MediaType.IMAGE,
                error="OpenCV not available"
            )
        
        try:
            if not self.validate_file(file_path):
                return ProcessingResult(
                    success=False,
                    media_type=MediaType.IMAGE,
                    error="File validation failed"
                )
            
            # 读取图像
            img = cv2.imread(file_path)
            if img is None:
                return ProcessingResult(
                    success=False,
                    media_type=MediaType.IMAGE,
                    error="Failed to read image"
                )
            
            # 处理选项
            detect_faces = kwargs.get('detect_faces', False)
            detect_objects = kwargs.get('detect_objects', False)
            edge_detection = kwargs.get('edge_detection', False)
            
            result_data = {
                'height': img.shape[0],
                'width': img.shape[1],
                'channels': img.shape[2] if len(img.shape) > 2 else 1
            }
            
            content_parts = []
            processed_files = []
            
            # 基本分析
            analysis = await self._analyze_image(img)
            content_parts.append(analysis)
            
            # 人脸检测
            if detect_faces:
                faces = await self._detect_faces(img)
                if faces:
                    content_parts.append(f"检测到 {len(faces)} 个人脸")
                    result_data['faces'] = faces
                    
                    # 保存标注图像
                    marked_img = self._draw_faces(img.copy(), faces)
                    marked_path = self._get_output_path(file_path, "_faces")
                    cv2.imwrite(marked_path, marked_img)
                    processed_files.append(marked_path)
            
            # 边缘检测
            if edge_detection:
                edges_path = self._get_output_path(file_path, "_edges")
                await self._detect_edges(img, edges_path)
                processed_files.append(edges_path)
                content_parts.append("已生成边缘检测图像")
            
            return ProcessingResult(
                success=True,
                media_type=MediaType.IMAGE,
                content='\n'.join(content_parts),
                metadata=result_data,
                processed_files=processed_files
            )
            
        except Exception as e:
            self.logger.error(f"OpenCV image processing error: {e}")
            return ProcessingResult(
                success=False,
                media_type=MediaType.IMAGE,
                error=str(e)
            )
    
    async def _analyze_image(self, img: np.ndarray) -> str:
        """分析图像基本特征"""
        try:
            height, width = img.shape[:2]
            
            # 计算平均亮度
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            
            # 计算对比度
            contrast = np.std(gray)
            
            # 颜色分析
            mean_color = np.mean(img, axis=(0, 1))
            
            brightness_desc = "明亮" if brightness > 127 else "昏暗"
            contrast_desc = "高对比度" if contrast > 50 else "低对比度"
            
            return f"图像尺寸: {width}x{height}, 整体{brightness_desc}, {contrast_desc}, 平均RGB值: {mean_color.astype(int)}"
            
        except Exception as e:
            self.logger.error(f"Image analysis error: {e}")
            return "图像分析失败"
    
    async def _detect_faces(self, img: np.ndarray) -> List[Dict[str, Any]]:
        """检测人脸"""
        try:
            # 使用Haar级联分类器
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            face_list = []
            for i, (x, y, w, h) in enumerate(faces):
                face_list.append({
                    'id': i,
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'confidence': 1.0  # Haar级联不提供置信度
                })
            
            return face_list
            
        except Exception as e:
            self.logger.error(f"Face detection error: {e}")
            return []
    
    def _draw_faces(self, img: np.ndarray, faces: List[Dict[str, Any]]) -> np.ndarray:
        """在图像上标注人脸"""
        for face in faces:
            x, y, w, h = face['x'], face['y'], face['width'], face['height']
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(img, f"Face {face['id']}", (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
        
        return img
    
    async def _detect_edges(self, img: np.ndarray, output_path: str):
        """边缘检测"""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            cv2.imwrite(output_path, edges)
            
        except Exception as e:
            self.logger.error(f"Edge detection error: {e}")
    
    def _get_output_path(self, original_path: str, suffix: str) -> str:
        """获取输出文件路径"""
        path = Path(original_path)
        return str(path.parent / f"{path.stem}{suffix}{path.suffix}")


# 注册图像处理器
def register_image_processors(multimodal_processor):
    """注册图像处理器"""
    if PIL_AVAILABLE:
        multimodal_processor.register_processor(MediaType.IMAGE, PILImageProcessor())
    
    if CV2_AVAILABLE:
        multimodal_processor.register_processor(MediaType.IMAGE, OpenCVImageProcessor())