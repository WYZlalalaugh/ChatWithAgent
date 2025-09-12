"""
流式输出处理器
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator, Callable
from datetime import datetime
import json
import uuid

from fastapi import WebSocket
from engines.conversation_engine import conversation_engine


class StreamProcessor:
    """流式输出处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_streams: Dict[str, Dict[str, Any]] = {}
    
    async def create_stream(
        self,
        conversation_id: str,
        user_message: str,
        bot_config: Dict[str, Any],
        websocket: Optional[WebSocket] = None,
        callback: Optional[Callable] = None
    ) -> str:
        """创建流式对话"""
        stream_id = str(uuid.uuid4())
        
        try:
            # 注册流
            self.active_streams[stream_id] = {
                'conversation_id': conversation_id,
                'websocket': websocket,
                'callback': callback,
                'start_time': datetime.utcnow(),
                'status': 'active',
                'content_buffer': '',
                'metadata': {}
            }
            
            # 启动处理任务
            task = asyncio.create_task(
                self._process_stream(stream_id, conversation_id, user_message, bot_config)
            )
            
            self.active_streams[stream_id]['task'] = task
            
            return stream_id
            
        except Exception as e:
            self.logger.error(f"Failed to create stream: {e}")
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
            raise
    
    async def _process_stream(
        self,
        stream_id: str,
        conversation_id: str,
        user_message: str,
        bot_config: Dict[str, Any]
    ):
        """处理流式对话"""
        try:
            stream_info = self.active_streams[stream_id]
            
            async for chunk in conversation_engine.process_message(
                conversation_id=conversation_id,
                user_message=user_message,
                bot_config=bot_config,
                stream=True
            ):
                if stream_id not in self.active_streams:
                    # 流已被取消
                    break
                
                await self._handle_chunk(stream_id, chunk)
            
            # 标记完成
            if stream_id in self.active_streams:
                self.active_streams[stream_id]['status'] = 'completed'
                self.active_streams[stream_id]['end_time'] = datetime.utcnow()
                
                # 保存最终内容
                final_content = self.active_streams[stream_id]['content_buffer']
                if final_content:
                    await conversation_engine.save_response(
                        conversation_id=conversation_id,
                        response_content=final_content,
                        metadata=self.active_streams[stream_id]['metadata']
                    )
            
        except Exception as e:
            self.logger.error(f"Stream processing error {stream_id}: {e}")
            if stream_id in self.active_streams:
                self.active_streams[stream_id]['status'] = 'error'
                self.active_streams[stream_id]['error'] = str(e)
                
                # 发送错误消息
                await self._send_message(stream_id, {
                    'type': 'error',
                    'content': '处理消息时发生错误，请稍后重试。'
                })
        
        finally:
            # 清理流（延迟清理，保留一段时间供查询）
            asyncio.create_task(self._cleanup_stream(stream_id, delay=300))
    
    async def _handle_chunk(self, stream_id: str, chunk: Dict[str, Any]):
        """处理流式数据块"""
        try:
            stream_info = self.active_streams[stream_id]
            chunk_type = chunk.get('type')
            
            if chunk_type == 'stream':
                content = chunk.get('content', '')
                is_complete = chunk.get('is_complete', False)
                
                if not is_complete:
                    # 累积内容
                    stream_info['content_buffer'] += content
                    
                    # 发送流式内容
                    await self._send_message(stream_id, {
                        'type': 'stream',
                        'content': content,
                        'is_complete': False
                    })
                else:
                    # 流式完成
                    final_content = chunk.get('final_content')
                    if final_content:
                        stream_info['content_buffer'] = final_content
                    
                    stream_info['metadata'] = chunk.get('metadata', {})
                    
                    await self._send_message(stream_id, {
                        'type': 'stream',
                        'content': '',
                        'is_complete': True,
                        'final_content': stream_info['content_buffer']
                    })
            
            elif chunk_type == 'message':
                # 非流式消息
                content = chunk.get('content', '')
                stream_info['content_buffer'] = content
                stream_info['metadata'] = chunk.get('metadata', {})
                
                await self._send_message(stream_id, {
                    'type': 'message',
                    'content': content
                })
            
            elif chunk_type == 'error':
                # 错误消息
                await self._send_message(stream_id, chunk)
            
        except Exception as e:
            self.logger.error(f"Failed to handle chunk for stream {stream_id}: {e}")
    
    async def _send_message(self, stream_id: str, message: Dict[str, Any]):
        """发送消息"""
        try:
            if stream_id not in self.active_streams:
                return
            
            stream_info = self.active_streams[stream_id]
            
            # 添加流ID和时间戳
            message.update({
                'stream_id': stream_id,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # WebSocket发送
            if stream_info.get('websocket'):
                websocket = stream_info['websocket']
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    self.logger.warning(f"WebSocket send failed for stream {stream_id}: {e}")
                    # WebSocket断开，取消流
                    await self.cancel_stream(stream_id)
            
            # 回调函数
            if stream_info.get('callback'):
                callback = stream_info['callback']
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
                except Exception as e:
                    self.logger.warning(f"Callback failed for stream {stream_id}: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to send message for stream {stream_id}: {e}")
    
    async def cancel_stream(self, stream_id: str) -> bool:
        """取消流"""
        try:
            if stream_id not in self.active_streams:
                return False
            
            stream_info = self.active_streams[stream_id]
            
            # 取消任务
            if 'task' in stream_info:
                task = stream_info['task']
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # 更新状态
            stream_info['status'] = 'cancelled'
            stream_info['end_time'] = datetime.utcnow()
            
            # 发送取消消息
            await self._send_message(stream_id, {
                'type': 'cancelled',
                'content': '流已被取消'
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cancel stream {stream_id}: {e}")
            return False
    
    async def get_stream_status(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """获取流状态"""
        try:
            if stream_id not in self.active_streams:
                return None
            
            stream_info = self.active_streams[stream_id]
            
            status = {
                'stream_id': stream_id,
                'conversation_id': stream_info['conversation_id'],
                'status': stream_info['status'],
                'start_time': stream_info['start_time'].isoformat(),
                'content_length': len(stream_info['content_buffer'])
            }
            
            if 'end_time' in stream_info:
                status['end_time'] = stream_info['end_time'].isoformat()
                duration = (stream_info['end_time'] - stream_info['start_time']).total_seconds()
                status['duration'] = duration
            
            if 'error' in stream_info:
                status['error'] = stream_info['error']
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get stream status {stream_id}: {e}")
            return None
    
    async def _cleanup_stream(self, stream_id: str, delay: int = 300):
        """清理流（延迟）"""
        try:
            await asyncio.sleep(delay)
            
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
                self.logger.debug(f"Cleaned up stream {stream_id}")
        
        except Exception as e:
            self.logger.error(f"Failed to cleanup stream {stream_id}: {e}")
    
    def get_active_streams(self) -> List[str]:
        """获取活跃流列表"""
        return [
            stream_id for stream_id, info in self.active_streams.items()
            if info['status'] == 'active'
        ]
    
    def get_stream_statistics(self) -> Dict[str, Any]:
        """获取流统计信息"""
        total_streams = len(self.active_streams)
        active_streams = len([
            info for info in self.active_streams.values()
            if info['status'] == 'active'
        ])
        completed_streams = len([
            info for info in self.active_streams.values()
            if info['status'] == 'completed'
        ])
        error_streams = len([
            info for info in self.active_streams.values()
            if info['status'] == 'error'
        ])
        
        return {
            'total_streams': total_streams,
            'active_streams': active_streams,
            'completed_streams': completed_streams,
            'error_streams': error_streams
        }


class WebSocketStreamHandler:
    """WebSocket流处理器"""
    
    def __init__(self, stream_processor: StreamProcessor):
        self.stream_processor = stream_processor
        self.logger = logging.getLogger(__name__)
    
    async def handle_websocket(
        self,
        websocket: WebSocket,
        conversation_id: str,
        bot_config: Dict[str, Any]
    ):
        """处理WebSocket连接"""
        try:
            await websocket.accept()
            
            while True:
                try:
                    # 接收消息
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    message_type = message.get('type')
                    
                    if message_type == 'send_message':
                        # 处理发送消息
                        user_message = message.get('content', '')
                        
                        if user_message.strip():
                            stream_id = await self.stream_processor.create_stream(
                                conversation_id=conversation_id,
                                user_message=user_message,
                                bot_config=bot_config,
                                websocket=websocket
                            )
                            
                            # 发送流ID确认
                            await websocket.send_text(json.dumps({
                                'type': 'stream_created',
                                'stream_id': stream_id
                            }))
                    
                    elif message_type == 'cancel_stream':
                        # 取消流
                        stream_id = message.get('stream_id')
                        if stream_id:
                            await self.stream_processor.cancel_stream(stream_id)
                    
                    elif message_type == 'get_status':
                        # 获取状态
                        stream_id = message.get('stream_id')
                        if stream_id:
                            status = await self.stream_processor.get_stream_status(stream_id)
                            await websocket.send_text(json.dumps({
                                'type': 'status',
                                'data': status
                            }))
                    
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        'type': 'error',
                        'content': 'Invalid JSON format'
                    }))
                
                except Exception as e:
                    self.logger.error(f"WebSocket message handling error: {e}")
                    await websocket.send_text(json.dumps({
                        'type': 'error',
                        'content': 'Internal server error'
                    }))
        
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {e}")
        
        finally:
            try:
                await websocket.close()
            except:
                pass


# 全局流处理器实例
stream_processor = StreamProcessor()
websocket_stream_handler = WebSocketStreamHandler(stream_processor)