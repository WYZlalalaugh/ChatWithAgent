"""
Redis 连接和操作
"""

import json
from typing import Any, Optional, Union
import redis.asyncio as redis
from app.config import settings


class RedisClient:
    """Redis 客户端封装"""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """连接 Redis"""
        self.redis = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        
    async def disconnect(self):
        """断开 Redis 连接"""
        if self.redis:
            await self.redis.close()
    
    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        return await self.redis.get(key)
    
    async def set(self, key: str, value: Union[str, dict, list], expire: int = None):
        """设置值"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        
        await self.redis.set(key, value, ex=expire)
    
    async def delete(self, key: str):
        """删除键"""
        await self.redis.delete(key)
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return bool(await self.redis.exists(key))
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """获取哈希值"""
        return await self.redis.hget(name, key)
    
    async def hset(self, name: str, key: str, value: Union[str, dict, list]):
        """设置哈希值"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        
        await self.redis.hset(name, key, value)
    
    async def hdel(self, name: str, key: str):
        """删除哈希键"""
        await self.redis.hdel(name, key)
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """递增计数器"""
        return await self.redis.incr(key, amount)
    
    async def expire(self, key: str, time: int):
        """设置过期时间"""
        await self.redis.expire(key, time)
    
    async def publish(self, channel: str, message: Union[str, dict]):
        """发布消息"""
        if isinstance(message, dict):
            message = json.dumps(message, ensure_ascii=False)
        
        await self.redis.publish(channel, message)
    
    async def subscribe(self, channel: str):
        """订阅频道"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        return pubsub


# 全局 Redis 客户端实例
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """获取 Redis 客户端"""
    return redis_client