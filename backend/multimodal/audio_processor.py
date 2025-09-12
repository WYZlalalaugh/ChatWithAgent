"""
音频处理器
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import tempfile
import os
from pathlib import Path
import json

try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

from .base import BaseMediaProcessor, ProcessingResult, MediaType


class LibrosaAudioProcessor(BaseMediaProcessor):
    """Librosa音频处理器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']
        self.max_file_size = 100 * 1024 * 1024  # 100MB
    
    def supports_format(self, file_extension: str) -> bool:
        return file_extension.lower() in self.supported_formats
    
    async def process(self, file_path: str, **kwargs) -> ProcessingResult:
        """处理音频文件"""
        if not LIBROSA_AVAILABLE:
            return ProcessingResult(
                success=False,
                media_type=MediaType.AUDIO,
                error="Librosa not available"
            )
        
        try:
            if not self.validate_file(file_path):
                return ProcessingResult(
                    success=False,
                    media_type=MediaType.AUDIO,
                    error="File validation failed"
                )
            
            # 处理选项
            extract_features = kwargs.get('extract_features', True)
            transcribe = kwargs.get('transcribe', False)
            normalize = kwargs.get('normalize', False)
            trim_silence = kwargs.get('trim_silence', False)
            
            # 加载音频
            y, sr = librosa.load(file_path, sr=None)
            
            result_data = {
                'duration': len(y) / sr,
                'sample_rate': sr,
                'channels': 1,  # librosa默认转为单声道
                'samples': len(y)
            }
            
            content_parts = []
            processed_files = []
            
            # 基本信息
            duration_str = self._format_duration(result_data['duration'])
            content_parts.append(f"音频时长: {duration_str}, 采样率: {sr}Hz")
            
            # 音频特征提取
            if extract_features:
                features = await self._extract_audio_features(y, sr)
                result_data.update(features)
                content_parts.append(self._describe_audio_features(features))
            
            # 静音修剪
            if trim_silence:
                y_trimmed, _ = librosa.effects.trim(y, top_db=20)
                if len(y_trimmed) < len(y):
                    trimmed_path = self._get_output_path(file_path, "_trimmed")
                    librosa.output.write_wav(trimmed_path, y_trimmed, sr)
                    processed_files.append(trimmed_path)
                    
                    new_duration = len(y_trimmed) / sr
                    content_parts.append(f"已修剪静音，新时长: {self._format_duration(new_duration)}")
                    y = y_trimmed
            
            # 音频标准化
            if normalize:
                y_normalized = librosa.util.normalize(y)
                normalized_path = self._get_output_path(file_path, "_normalized")
                librosa.output.write_wav(normalized_path, y_normalized, sr)
                processed_files.append(normalized_path)
                content_parts.append("已生成标准化音频")
            
            # 语音转文字
            if transcribe:
                transcript = await self._transcribe_audio(file_path)
                if transcript:
                    content_parts.append(f"转录文本: {transcript}")
                    result_data['transcript'] = transcript
            
            return ProcessingResult(
                success=True,
                media_type=MediaType.AUDIO,
                content='\n'.join(content_parts),
                metadata=result_data,
                processed_files=processed_files
            )
            
        except Exception as e:
            self.logger.error(f"Audio processing error: {e}")
            return ProcessingResult(
                success=False,
                media_type=MediaType.AUDIO,
                error=str(e)
            )
    
    async def _extract_audio_features(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """提取音频特征"""
        features = {}
        
        try:
            # 基本统计
            features['rms_energy'] = float(np.sqrt(np.mean(y**2)))
            features['zero_crossing_rate'] = float(np.mean(librosa.feature.zero_crossing_rate(y)))
            
            # 频谱特征
            stft = librosa.stft(y)
            magnitude = np.abs(stft)
            features['spectral_centroid'] = float(np.mean(librosa.feature.spectral_centroid(S=magnitude, sr=sr)))
            features['spectral_bandwidth'] = float(np.mean(librosa.feature.spectral_bandwidth(S=magnitude, sr=sr)))
            features['spectral_rolloff'] = float(np.mean(librosa.feature.spectral_rolloff(S=magnitude, sr=sr)))
            
            # MFCC特征
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            features['mfcc_mean'] = mfcc.mean(axis=1).tolist()
            features['mfcc_std'] = mfcc.std(axis=1).tolist()
            
            # 色度特征
            chroma = librosa.feature.chroma_stft(S=magnitude, sr=sr)
            features['chroma_mean'] = float(np.mean(chroma))
            
            # 音调检测
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            if pitch_values:
                features['fundamental_frequency'] = float(np.mean(pitch_values))
                features['pitch_range'] = float(np.max(pitch_values) - np.min(pitch_values))
            
        except Exception as e:
            self.logger.error(f"Feature extraction error: {e}")
        
        return features
    
    def _describe_audio_features(self, features: Dict[str, Any]) -> str:
        """描述音频特征"""
        descriptions = []
        
        try:
            # 能量级别
            rms = features.get('rms_energy', 0)
            if rms > 0.1:
                energy_desc = "高能量"
            elif rms > 0.05:
                energy_desc = "中等能量"
            else:
                energy_desc = "低能量"
            descriptions.append(f"音频{energy_desc}")
            
            # 频谱特征
            centroid = features.get('spectral_centroid', 0)
            if centroid > 3000:
                tone_desc = "高音调"
            elif centroid > 1000:
                tone_desc = "中音调"
            else:
                tone_desc = "低音调"
            descriptions.append(f"整体{tone_desc}")
            
            # 基频
            fundamental_freq = features.get('fundamental_frequency')
            if fundamental_freq:
                if fundamental_freq > 200:
                    voice_desc = "可能是女声或儿童声音"
                elif fundamental_freq > 100:
                    voice_desc = "可能是男声"
                else:
                    voice_desc = "低频声音"
                descriptions.append(voice_desc)
        
        except Exception as e:
            self.logger.error(f"Feature description error: {e}")
        
        return "音频特征: " + ", ".join(descriptions) if descriptions else "音频特征分析完成"
    
    async def _transcribe_audio(self, file_path: str) -> Optional[str]:
        """音频转文字"""
        try:
            if WHISPER_AVAILABLE:
                # 使用Whisper进行转录
                model = whisper.load_model("base")
                result = model.transcribe(file_path)
                return result["text"].strip()
            
            elif SPEECH_RECOGNITION_AVAILABLE:
                # 使用speech_recognition
                r = sr.Recognizer()
                
                # 转换为WAV格式
                if not file_path.lower().endswith('.wav'):
                    wav_path = self._convert_to_wav(file_path)
                    if not wav_path:
                        return None
                    file_path = wav_path
                
                with sr.AudioFile(file_path) as source:
                    audio = r.record(source)
                
                # 尝试不同的识别引擎
                try:
                    text = r.recognize_google(audio, language='zh-CN')
                    return text
                except sr.UnknownValueError:
                    # 尝试英文识别
                    try:
                        text = r.recognize_google(audio, language='en-US')
                        return text
                    except:
                        pass
                except sr.RequestError:
                    pass
        
        except Exception as e:
            self.logger.error(f"Transcription error: {e}")
        
        return None
    
    def _convert_to_wav(self, file_path: str) -> Optional[str]:
        """转换音频为WAV格式"""
        try:
            if not PYDUB_AVAILABLE:
                return None
            
            audio = AudioSegment.from_file(file_path)
            wav_path = self._get_output_path(file_path, "_converted", ".wav")
            audio.export(wav_path, format="wav")
            return wav_path
            
        except Exception as e:
            self.logger.error(f"Audio conversion error: {e}")
            return None
    
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


class WhisperAudioProcessor(BaseMediaProcessor):
    """Whisper语音识别处理器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['.wav', '.mp3', '.flac', '.ogg', '.m4a', '.mp4', '.avi']
        self.max_file_size = 200 * 1024 * 1024  # 200MB
        self.model = None
    
    def supports_format(self, file_extension: str) -> bool:
        return file_extension.lower() in self.supported_formats
    
    async def process(self, file_path: str, **kwargs) -> ProcessingResult:
        """处理音频文件"""
        if not WHISPER_AVAILABLE:
            return ProcessingResult(
                success=False,
                media_type=MediaType.AUDIO,
                error="Whisper not available"
            )
        
        try:
            if not self.validate_file(file_path):
                return ProcessingResult(
                    success=False,
                    media_type=MediaType.AUDIO,
                    error="File validation failed"
                )
            
            # 处理选项
            model_size = kwargs.get('model_size', 'base')
            language = kwargs.get('language', None)
            translate = kwargs.get('translate', False)
            
            # 加载模型
            if self.model is None or self.model.dims.n_vocab != whisper.model.WHISPER_MODELS[model_size]:
                self.model = whisper.load_model(model_size)
            
            # 转录选项
            options = {}
            if language:
                options['language'] = language
            if translate:
                options['task'] = 'translate'
            
            # 执行转录
            result = self.model.transcribe(file_path, **options)
            
            # 提取信息
            text = result["text"].strip()
            language_detected = result.get("language", "unknown")
            
            result_data = {
                'transcript': text,
                'language': language_detected,
                'model_size': model_size,
                'segments': []
            }
            
            content_parts = [
                f"语音转录完成",
                f"检测语言: {language_detected}",
                f"转录文本: {text}"
            ]
            
            # 处理分段信息
            if "segments" in result:
                segments = []
                for segment in result["segments"]:
                    segments.append({
                        'start': segment['start'],
                        'end': segment['end'],
                        'text': segment['text'].strip()
                    })
                
                result_data['segments'] = segments
                content_parts.append(f"共 {len(segments)} 个语音段落")
            
            return ProcessingResult(
                success=True,
                media_type=MediaType.AUDIO,
                content='\n'.join(content_parts),
                metadata=result_data
            )
            
        except Exception as e:
            self.logger.error(f"Whisper processing error: {e}")
            return ProcessingResult(
                success=False,
                media_type=MediaType.AUDIO,
                error=str(e)
            )


class PyDubAudioProcessor(BaseMediaProcessor):
    """PyDub音频处理器"""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ['.wav', '.mp3', '.flac', '.ogg', '.m4a', '.mp4', '.wma']
        self.max_file_size = 100 * 1024 * 1024  # 100MB
    
    def supports_format(self, file_extension: str) -> bool:
        return file_extension.lower() in self.supported_formats
    
    async def process(self, file_path: str, **kwargs) -> ProcessingResult:
        """处理音频文件"""
        if not PYDUB_AVAILABLE:
            return ProcessingResult(
                success=False,
                media_type=MediaType.AUDIO,
                error="PyDub not available"
            )
        
        try:
            if not self.validate_file(file_path):
                return ProcessingResult(
                    success=False,
                    media_type=MediaType.AUDIO,
                    error="File validation failed"
                )
            
            # 加载音频
            audio = AudioSegment.from_file(file_path)
            
            # 处理选项
            convert_format = kwargs.get('convert_format', None)
            normalize_volume = kwargs.get('normalize_volume', False)
            fade_in = kwargs.get('fade_in', 0)
            fade_out = kwargs.get('fade_out', 0)
            speed_change = kwargs.get('speed_change', 1.0)
            
            result_data = {
                'duration': len(audio) / 1000.0,  # 转换为秒
                'channels': audio.channels,
                'sample_rate': audio.frame_rate,
                'frame_width': audio.frame_width,
                'max_possible_amplitude': audio.max_possible_amplitude
            }
            
            content_parts = []
            processed_files = []
            
            # 基本信息
            duration_str = self._format_duration(result_data['duration'])
            content_parts.append(
                f"音频信息: 时长{duration_str}, "
                f"{result_data['channels']}声道, "
                f"采样率{result_data['sample_rate']}Hz"
            )
            
            # 音量分析
            volume_analysis = self._analyze_volume(audio)
            result_data.update(volume_analysis)
            content_parts.append(self._describe_volume(volume_analysis))
            
            processed_audio = audio
            
            # 音量标准化
            if normalize_volume:
                processed_audio = processed_audio.normalize()
                content_parts.append("已标准化音量")
            
            # 淡入淡出
            if fade_in > 0:
                processed_audio = processed_audio.fade_in(int(fade_in * 1000))
                content_parts.append(f"添加{fade_in}秒淡入效果")
            
            if fade_out > 0:
                processed_audio = processed_audio.fade_out(int(fade_out * 1000))
                content_parts.append(f"添加{fade_out}秒淡出效果")
            
            # 速度调整
            if speed_change != 1.0:
                processed_audio = processed_audio.speedup(playback_speed=speed_change)
                new_duration = len(processed_audio) / 1000.0
                content_parts.append(f"调整播放速度{speed_change}x，新时长{self._format_duration(new_duration)}")
            
            # 格式转换
            if convert_format:
                converted_path = self._get_output_path(file_path, f"_converted", f".{convert_format}")
                processed_audio.export(converted_path, format=convert_format)
                processed_files.append(converted_path)
                content_parts.append(f"已转换为{convert_format.upper()}格式")
            
            # 如果有处理，保存处理后的音频
            if processed_audio != audio:
                processed_path = self._get_output_path(file_path, "_processed")
                processed_audio.export(processed_path, format="wav")
                processed_files.append(processed_path)
            
            return ProcessingResult(
                success=True,
                media_type=MediaType.AUDIO,
                content='\n'.join(content_parts),
                metadata=result_data,
                processed_files=processed_files
            )
            
        except Exception as e:
            self.logger.error(f"PyDub processing error: {e}")
            return ProcessingResult(
                success=False,
                media_type=MediaType.AUDIO,
                error=str(e)
            )
    
    def _analyze_volume(self, audio: AudioSegment) -> Dict[str, float]:
        """分析音频音量"""
        try:
            # 计算dBFS (相对于满刻度的分贝数)
            max_dBFS = audio.max_dBFS
            
            # 计算RMS音量
            rms_dBFS = audio.dBFS
            
            # 检测静音段
            silence_threshold = -50  # dBFS
            silence_duration = 0
            
            # 简单的静音检测（每秒检查一次）
            for i in range(0, len(audio), 1000):
                segment = audio[i:i+1000]
                if segment.dBFS < silence_threshold:
                    silence_duration += min(1000, len(segment))
            
            silence_percentage = (silence_duration / len(audio)) * 100
            
            return {
                'max_dBFS': max_dBFS,
                'rms_dBFS': rms_dBFS,
                'silence_percentage': silence_percentage
            }
            
        except Exception as e:
            self.logger.error(f"Volume analysis error: {e}")
            return {}
    
    def _describe_volume(self, volume_analysis: Dict[str, float]) -> str:
        """描述音频音量特征"""
        try:
            max_dBFS = volume_analysis.get('max_dBFS', -float('inf'))
            rms_dBFS = volume_analysis.get('rms_dBFS', -float('inf'))
            silence_percentage = volume_analysis.get('silence_percentage', 0)
            
            descriptions = []
            
            # 音量级别
            if max_dBFS > -6:
                descriptions.append("高音量")
            elif max_dBFS > -20:
                descriptions.append("中等音量")
            else:
                descriptions.append("低音量")
            
            # 动态范围
            dynamic_range = max_dBFS - rms_dBFS
            if dynamic_range > 20:
                descriptions.append("大动态范围")
            elif dynamic_range > 10:
                descriptions.append("中等动态范围")
            else:
                descriptions.append("小动态范围")
            
            # 静音比例
            if silence_percentage > 30:
                descriptions.append(f"较多静音({silence_percentage:.1f}%)")
            elif silence_percentage > 10:
                descriptions.append(f"少量静音({silence_percentage:.1f}%)")
            
            return "音频特征: " + ", ".join(descriptions)
            
        except Exception as e:
            self.logger.error(f"Volume description error: {e}")
            return "音频音量分析完成"
    
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


# 注册音频处理器
def register_audio_processors(multimodal_processor):
    """注册音频处理器"""
    if LIBROSA_AVAILABLE:
        multimodal_processor.register_processor(MediaType.AUDIO, LibrosaAudioProcessor())
    
    if WHISPER_AVAILABLE:
        multimodal_processor.register_processor(MediaType.AUDIO, WhisperAudioProcessor())
    
    if PYDUB_AVAILABLE:
        multimodal_processor.register_processor(MediaType.AUDIO, PyDubAudioProcessor())