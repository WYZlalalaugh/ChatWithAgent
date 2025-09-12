"""
视频处理器
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import tempfile
import os
from pathlib import Path
import json

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import moviepy.editor as mp
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False

from .base import BaseMediaProcessor, ProcessingResult, MediaType


class OpenCVVideoProcessor(BaseMediaProcessor):
    """OpenCV视频处理器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
        self.max_file_size = 500 * 1024 * 1024  # 500MB
    
    def supports_format(self, file_extension: str) -> bool:
        return file_extension.lower() in self.supported_formats
    
    async def process(self, file_path: str, **kwargs) -> ProcessingResult:
        """处理视频文件"""
        if not CV2_AVAILABLE:
            return ProcessingResult(
                success=False,
                media_type=MediaType.VIDEO,
                error="OpenCV not available"
            )
        
        try:
            if not self.validate_file(file_path):
                return ProcessingResult(
                    success=False,
                    media_type=MediaType.VIDEO,
                    error="File validation failed"
                )
            
            # 打开视频
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                return ProcessingResult(
                    success=False,
                    media_type=MediaType.VIDEO,
                    error="Failed to open video file"
                )
            
            try:
                # 处理选项
                extract_frames = kwargs.get('extract_frames', False)
                frame_interval = kwargs.get('frame_interval', 30)  # 每30帧提取一帧
                detect_motion = kwargs.get('detect_motion', False)
                create_thumbnail = kwargs.get('create_thumbnail', True)
                
                # 获取视频信息
                video_info = await self._get_video_info(cap)
                
                content_parts = []
                processed_files = []
                
                # 基本信息
                duration_str = self._format_duration(video_info['duration'])
                content_parts.append(
                    f"视频信息: 时长{duration_str}, "
                    f"分辨率{video_info['width']}x{video_info['height']}, "
                    f"帧率{video_info['fps']:.2f}fps, "
                    f"总帧数{video_info['frame_count']}"
                )
                
                # 创建缩略图
                if create_thumbnail:
                    thumbnail_path = await self._create_thumbnail(cap, file_path)
                    if thumbnail_path:
                        processed_files.append(thumbnail_path)
                        content_parts.append("已生成视频缩略图")
                
                # 提取关键帧
                if extract_frames:
                    frame_paths = await self._extract_frames(cap, file_path, frame_interval)
                    if frame_paths:
                        processed_files.extend(frame_paths)
                        content_parts.append(f"已提取{len(frame_paths)}个关键帧")
                
                # 运动检测
                if detect_motion:
                    motion_info = await self._detect_motion(cap)
                    video_info.update(motion_info)
                    content_parts.append(self._describe_motion(motion_info))
                
                # 场景分析
                scene_analysis = await self._analyze_scenes(cap)
                video_info.update(scene_analysis)
                content_parts.append(self._describe_scenes(scene_analysis))
                
                return ProcessingResult(
                    success=True,
                    media_type=MediaType.VIDEO,
                    content='\n'.join(content_parts),
                    metadata=video_info,
                    processed_files=processed_files
                )
                
            finally:
                cap.release()
                
        except Exception as e:
            self.logger.error(f"Video processing error: {e}")
            return ProcessingResult(
                success=False,
                media_type=MediaType.VIDEO,
                error=str(e)
            )
    
    async def _get_video_info(self, cap: cv2.VideoCapture) -> Dict[str, Any]:
        """获取视频信息"""
        info = {}
        
        try:
            # 基本属性
            info['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            info['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            info['fps'] = cap.get(cv2.CAP_PROP_FPS)
            info['frame_count'] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 计算时长
            if info['fps'] > 0:
                info['duration'] = info['frame_count'] / info['fps']
            else:
                info['duration'] = 0
            
            # 编码信息
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            info['codec'] = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
            
        except Exception as e:
            self.logger.error(f"Error getting video info: {e}")
        
        return info
    
    async def _create_thumbnail(self, cap: cv2.VideoCapture, file_path: str) -> Optional[str]:
        """创建视频缩略图"""
        try:
            # 跳到视频中间位置
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            middle_frame = frame_count // 2
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
            ret, frame = cap.read()
            
            if ret:
                thumbnail_path = self._get_output_path(file_path, "_thumbnail", ".jpg")
                cv2.imwrite(thumbnail_path, frame)
                return thumbnail_path
                
        except Exception as e:
            self.logger.error(f"Thumbnail creation error: {e}")
        
        return None
    
    async def _extract_frames(self, cap: cv2.VideoCapture, file_path: str, interval: int) -> List[str]:
        """提取关键帧"""
        frame_paths = []
        
        try:
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            frame_num = 0
            extracted_count = 0
            
            while frame_num < frame_count and extracted_count < 10:  # 最多提取10帧
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if ret:
                    frame_path = self._get_output_path(
                        file_path, f"_frame_{extracted_count:03d}", ".jpg"
                    )
                    cv2.imwrite(frame_path, frame)
                    frame_paths.append(frame_path)
                    extracted_count += 1
                
                frame_num += interval
                
        except Exception as e:
            self.logger.error(f"Frame extraction error: {e}")
        
        return frame_paths
    
    async def _detect_motion(self, cap: cv2.VideoCapture) -> Dict[str, Any]:
        """检测视频中的运动"""
        motion_info = {
            'has_motion': False,
            'motion_intensity': 0.0,
            'static_scenes': 0,
            'motion_scenes': 0
        }
        
        try:
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            # 背景减法器
            back_sub = cv2.createBackgroundSubtractorMOG2()
            motion_values = []
            
            sample_frames = min(100, frame_count)  # 最多采样100帧
            step = max(1, frame_count // sample_frames)
            
            for i in range(0, frame_count, step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                
                if ret:
                    # 应用背景减法
                    fg_mask = back_sub.apply(frame)
                    
                    # 计算运动量
                    motion_pixels = cv2.countNonZero(fg_mask)
                    total_pixels = fg_mask.shape[0] * fg_mask.shape[1]
                    motion_ratio = motion_pixels / total_pixels
                    
                    motion_values.append(motion_ratio)
                    
                    # 判断是否有运动
                    if motion_ratio > 0.01:  # 1%的像素变化认为有运动
                        motion_info['motion_scenes'] += 1
                    else:
                        motion_info['static_scenes'] += 1
            
            if motion_values:
                motion_info['motion_intensity'] = sum(motion_values) / len(motion_values)
                motion_info['has_motion'] = motion_info['motion_intensity'] > 0.005
                
        except Exception as e:
            self.logger.error(f"Motion detection error: {e}")
        
        return motion_info
    
    async def _analyze_scenes(self, cap: cv2.VideoCapture) -> Dict[str, Any]:
        """分析视频场景"""
        scene_info = {
            'brightness_avg': 0.0,
            'brightness_std': 0.0,
            'color_variance': 0.0,
            'scene_changes': 0
        }
        
        try:
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            brightness_values = []
            color_values = []
            prev_hist = None
            
            sample_frames = min(50, frame_count)  # 采样50帧
            step = max(1, frame_count // sample_frames)
            
            for i in range(0, frame_count, step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                
                if ret:
                    # 亮度分析
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    brightness = gray.mean()
                    brightness_values.append(brightness)
                    
                    # 颜色分析
                    color_mean = frame.mean(axis=(0, 1))
                    color_values.append(color_mean)
                    
                    # 场景变化检测（使用直方图）
                    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
                    if prev_hist is not None:
                        correlation = cv2.compareHist(hist, prev_hist, cv2.HISTCMP_CORREL)
                        if correlation < 0.8:  # 相关性小于0.8认为是场景变化
                            scene_info['scene_changes'] += 1
                    prev_hist = hist
            
            if brightness_values:
                scene_info['brightness_avg'] = sum(brightness_values) / len(brightness_values)
                scene_info['brightness_std'] = np.std(brightness_values) if len(brightness_values) > 1 else 0
            
            if color_values:
                import numpy as np
                color_array = np.array(color_values)
                scene_info['color_variance'] = float(np.var(color_array))
                
        except Exception as e:
            self.logger.error(f"Scene analysis error: {e}")
        
        return scene_info
    
    def _describe_motion(self, motion_info: Dict[str, Any]) -> str:
        """描述运动特征"""
        try:
            motion_intensity = motion_info.get('motion_intensity', 0)
            motion_scenes = motion_info.get('motion_scenes', 0)
            static_scenes = motion_info.get('static_scenes', 0)
            
            if motion_intensity > 0.05:
                motion_desc = "高运动量"
            elif motion_intensity > 0.01:
                motion_desc = "中等运动量"
            else:
                motion_desc = "低运动量"
            
            total_scenes = motion_scenes + static_scenes
            if total_scenes > 0:
                motion_ratio = motion_scenes / total_scenes
                scene_desc = f"运动场景占比{motion_ratio:.1%}"
            else:
                scene_desc = "场景分析不足"
            
            return f"运动分析: {motion_desc}, {scene_desc}"
            
        except Exception as e:
            self.logger.error(f"Motion description error: {e}")
            return "运动分析完成"
    
    def _describe_scenes(self, scene_info: Dict[str, Any]) -> str:
        """描述场景特征"""
        try:
            brightness = scene_info.get('brightness_avg', 0)
            brightness_std = scene_info.get('brightness_std', 0)
            scene_changes = scene_info.get('scene_changes', 0)
            
            if brightness > 150:
                brightness_desc = "明亮"
            elif brightness > 100:
                brightness_desc = "中等亮度"
            else:
                brightness_desc = "昏暗"
            
            if brightness_std > 30:
                contrast_desc = "高对比度"
            elif brightness_std > 15:
                contrast_desc = "中等对比度"
            else:
                contrast_desc = "低对比度"
            
            scene_desc = f"场景变化{scene_changes}次" if scene_changes > 0 else "场景稳定"
            
            return f"场景分析: {brightness_desc}, {contrast_desc}, {scene_desc}"
            
        except Exception as e:
            self.logger.error(f"Scene description error: {e}")
            return "场景分析完成"
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    def _get_output_path(self, original_path: str, suffix: str, extension: str = None) -> str:
        """获取输出文件路径"""
        path = Path(original_path)
        if extension:
            return str(path.parent / f"{path.stem}{suffix}{extension}")
        else:
            return str(path.parent / f"{path.stem}{suffix}{path.suffix}")


class MoviePyVideoProcessor(BaseMediaProcessor):
    """MoviePy视频处理器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.gif']
        self.max_file_size = 1024 * 1024 * 1024  # 1GB
    
    def supports_format(self, file_extension: str) -> bool:
        return file_extension.lower() in self.supported_formats
    
    async def process(self, file_path: str, **kwargs) -> ProcessingResult:
        """处理视频文件"""
        if not MOVIEPY_AVAILABLE:
            return ProcessingResult(
                success=False,
                media_type=MediaType.VIDEO,
                error="MoviePy not available"
            )
        
        try:
            if not self.validate_file(file_path):
                return ProcessingResult(
                    success=False,
                    media_type=MediaType.VIDEO,
                    error="File validation failed"
                )
            
            # 处理选项
            extract_audio = kwargs.get('extract_audio', False)
            create_gif = kwargs.get('create_gif', False)
            resize_video = kwargs.get('resize_video', None)
            clip_duration = kwargs.get('clip_duration', None)
            speed_change = kwargs.get('speed_change', 1.0)
            
            # 加载视频
            video = mp.VideoFileClip(file_path)
            
            try:
                # 获取视频信息
                video_info = {
                    'duration': video.duration,
                    'fps': video.fps,
                    'size': video.size,
                    'width': video.w,
                    'height': video.h,
                    'has_audio': video.audio is not None
                }
                
                content_parts = []
                processed_files = []
                
                # 基本信息
                duration_str = self._format_duration(video_info['duration'])
                content_parts.append(
                    f"视频信息: 时长{duration_str}, "
                    f"分辨率{video_info['width']}x{video_info['height']}, "
                    f"帧率{video_info['fps']:.2f}fps"
                )
                
                if video_info['has_audio']:
                    content_parts.append("包含音频轨道")
                
                processed_video = video
                
                # 调整视频大小
                if resize_video:
                    if isinstance(resize_video, (list, tuple)) and len(resize_video) == 2:
                        processed_video = processed_video.resize(resize_video)
                        content_parts.append(f"调整分辨率为{resize_video[0]}x{resize_video[1]}")
                    elif isinstance(resize_video, float):
                        processed_video = processed_video.resize(resize_video)
                        content_parts.append(f"缩放比例{resize_video}")
                
                # 裁剪时长
                if clip_duration and clip_duration < video_info['duration']:
                    processed_video = processed_video.subclip(0, clip_duration)
                    content_parts.append(f"裁剪为{self._format_duration(clip_duration)}")
                
                # 调整播放速度
                if speed_change != 1.0:
                    processed_video = processed_video.speedx(speed_change)
                    new_duration = processed_video.duration
                    content_parts.append(f"调整播放速度{speed_change}x，新时长{self._format_duration(new_duration)}")
                
                # 提取音频
                if extract_audio and video_info['has_audio']:
                    audio_path = self._get_output_path(file_path, "_audio", ".wav")
                    video.audio.write_audiofile(audio_path, verbose=False, logger=None)
                    processed_files.append(audio_path)
                    content_parts.append("已提取音频")
                
                # 创建GIF
                if create_gif:
                    gif_path = self._get_output_path(file_path, "_preview", ".gif")
                    # 创建短GIF预览（前5秒）
                    gif_clip = processed_video.subclip(0, min(5, processed_video.duration))
                    gif_clip = gif_clip.resize(width=320)  # 缩小尺寸
                    gif_clip.write_gif(gif_path, fps=10, verbose=False, logger=None)
                    processed_files.append(gif_path)
                    content_parts.append("已生成GIF预览")
                
                # 如果视频被处理，保存处理后的视频
                if processed_video != video:
                    processed_path = self._get_output_path(file_path, "_processed")
                    processed_video.write_videofile(
                        processed_path, 
                        verbose=False, 
                        logger=None,
                        audio_codec='aac' if video_info['has_audio'] else None
                    )
                    processed_files.append(processed_path)
                
                return ProcessingResult(
                    success=True,
                    media_type=MediaType.VIDEO,
                    content='\n'.join(content_parts),
                    metadata=video_info,
                    processed_files=processed_files
                )
                
            finally:
                video.close()
                if 'processed_video' in locals() and processed_video != video:
                    processed_video.close()
                
        except Exception as e:
            self.logger.error(f"MoviePy processing error: {e}")
            return ProcessingResult(
                success=False,
                media_type=MediaType.VIDEO,
                error=str(e)
            )
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    def _get_output_path(self, original_path: str, suffix: str, extension: str = None) -> str:
        """获取输出文件路径"""
        path = Path(original_path)
        if extension:
            return str(path.parent / f"{path.stem}{suffix}{extension}")
        else:
            return str(path.parent / f"{path.stem}{suffix}{path.suffix}")


# 注册视频处理器
def register_video_processors(multimodal_processor):
    """注册视频处理器"""
    if CV2_AVAILABLE:
        multimodal_processor.register_processor(MediaType.VIDEO, OpenCVVideoProcessor())
    
    if MOVIEPY_AVAILABLE:
        multimodal_processor.register_processor(MediaType.VIDEO, MoviePyVideoProcessor())