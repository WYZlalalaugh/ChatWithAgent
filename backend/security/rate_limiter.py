"""
限流机制实现
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import redis.asyncio as redis

from app.config import settings


class RateLimitType(str, Enum):
    """限流类型"""
    PER_SECOND = "per_second"
    PER_MINUTE = "per_minute"
    PER_HOUR = "per_hour"
    PER_DAY = "per_day"


class RateLimitStrategy(str, Enum):
    """限流策略"""
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitConfig:
    """限流配置"""
    limit: int  # 限制数量
    window: int  # 时间窗口（秒）
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst_limit: Optional[int] = None  # 突发限制
    
    def get_window_seconds(self, rate_type: RateLimitType) -> int:
        """根据限流类型获取窗口秒数"""
        if rate_type == RateLimitType.PER_SECOND:
            return 1
        elif rate_type == RateLimitType.PER_MINUTE:
            return 60
        elif rate_type == RateLimitType.PER_HOUR:
            return 3600
        elif rate_type == RateLimitType.PER_DAY:
            return 86400
        else:
            return self.window


@dataclass
class RateLimitResult:
    """限流结果"""
    allowed: bool
    limit: int
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None


class RateLimiter:
    """限流器"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.logger = logging.getLogger("security.rate_limiter")
        self.redis_client = redis_client
        
        # 内存存储（当Redis不可用时）
        self.memory_store: Dict[str, List[float]] = {}
        
        # 预定义限流配置
        self.default_configs = {
            "api_call": RateLimitConfig(limit=1000, window=3600),  # 每小时1000次
            "login_attempt": RateLimitConfig(limit=5, window=300),  # 5分钟5次
            "message_send": RateLimitConfig(limit=100, window=60),  # 每分钟100条
            "file_upload": RateLimitConfig(limit=10, window=3600),  # 每小时10个文件
        }
    
    async def check_rate_limit(
        self,
        key: str,
        config: RateLimitConfig,
        increment: int = 1
    ) -> RateLimitResult:
        """检查限流"""
        try:
            if self.redis_client:
                return await self._check_redis_rate_limit(key, config, increment)
            else:
                return await self._check_memory_rate_limit(key, config, increment)
                
        except Exception as e:
            self.logger.error(f"Rate limit check error: {e}")
            # 出错时允许通过，但记录日志
            return RateLimitResult(
                allowed=True,
                limit=config.limit,
                remaining=config.limit,
                reset_time=int(time.time() + config.window)
            )
    
    async def _check_redis_rate_limit(
        self,
        key: str,
        config: RateLimitConfig,
        increment: int
    ) -> RateLimitResult:
        """使用Redis检查限流"""
        current_time = time.time()
        window_start = current_time - config.window
        
        if config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._sliding_window_redis(key, config, increment, current_time, window_start)
        elif config.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._fixed_window_redis(key, config, increment, current_time)
        elif config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._token_bucket_redis(key, config, increment, current_time)
        else:
            # 默认使用滑动窗口
            return await self._sliding_window_redis(key, config, increment, current_time, window_start)
    
    async def _sliding_window_redis(
        self,
        key: str,
        config: RateLimitConfig,
        increment: int,
        current_time: float,
        window_start: float
    ) -> RateLimitResult:
        """Redis滑动窗口限流"""
        pipe = self.redis_client.pipeline()
        
        # 清理过期记录
        pipe.zremrangebyscore(key, 0, window_start)
        
        # 获取当前窗口内的请求数
        pipe.zcard(key)
        
        # 执行查询
        results = await pipe.execute()
        current_count = results[1]
        
        # 检查是否超限
        if current_count + increment > config.limit:
            return RateLimitResult(
                allowed=False,
                limit=config.limit,
                remaining=max(0, config.limit - current_count),
                reset_time=int(current_time + config.window),
                retry_after=int(config.window)
            )
        
        # 记录新请求
        pipe = self.redis_client.pipeline()
        for i in range(increment):
            pipe.zadd(key, {f"{current_time}_{i}": current_time})
        
        # 设置过期时间
        pipe.expire(key, config.window + 1)
        
        await pipe.execute()
        
        return RateLimitResult(
            allowed=True,
            limit=config.limit,
            remaining=config.limit - current_count - increment,
            reset_time=int(current_time + config.window)
        )
    
    async def _fixed_window_redis(
        self,
        key: str,
        config: RateLimitConfig,
        increment: int,
        current_time: float
    ) -> RateLimitResult:
        """Redis固定窗口限流"""
        # 计算当前窗口
        window_id = int(current_time // config.window)
        window_key = f"{key}:{window_id}"
        
        # 获取当前计数
        current_count = await self.redis_client.get(window_key)
        current_count = int(current_count) if current_count else 0
        
        # 检查是否超限
        if current_count + increment > config.limit:
            window_reset = (window_id + 1) * config.window
            return RateLimitResult(
                allowed=False,
                limit=config.limit,
                remaining=max(0, config.limit - current_count),
                reset_time=int(window_reset),
                retry_after=int(window_reset - current_time)
            )
        
        # 更新计数
        pipe = self.redis_client.pipeline()
        pipe.incrby(window_key, increment)
        pipe.expire(window_key, config.window)
        await pipe.execute()
        
        window_reset = (window_id + 1) * config.window
        return RateLimitResult(
            allowed=True,
            limit=config.limit,
            remaining=config.limit - current_count - increment,
            reset_time=int(window_reset)
        )
    
    async def _token_bucket_redis(
        self,
        key: str,
        config: RateLimitConfig,
        increment: int,
        current_time: float
    ) -> RateLimitResult:
        """Redis令牌桶限流"""
        bucket_key = f"bucket:{key}"
        
        # Lua脚本实现原子性令牌桶操作
        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local tokens = tonumber(ARGV[2])
        local interval = tonumber(ARGV[3])
        local requested = tonumber(ARGV[4])
        local now = tonumber(ARGV[5])
        
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local current_tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now
        
        -- 计算需要添加的令牌
        local elapsed = now - last_refill
        local new_tokens = math.min(capacity, current_tokens + (elapsed / interval) * tokens)
        
        if new_tokens >= requested then
            new_tokens = new_tokens - requested
            redis.call('HMSET', key, 'tokens', new_tokens, 'last_refill', now)
            redis.call('EXPIRE', key, interval * 2)
            return {1, new_tokens, capacity}
        else
            redis.call('HMSET', key, 'tokens', new_tokens, 'last_refill', now)
            redis.call('EXPIRE', key, interval * 2)
            return {0, new_tokens, capacity}
        end
        """
        
        # 令牌生成速率：每秒生成 limit/window 个令牌
        refill_rate = config.limit / config.window
        
        result = await self.redis_client.eval(
            lua_script,
            1,
            bucket_key,
            config.limit,  # capacity
            refill_rate,   # tokens per second
            1,             # interval
            increment,     # requested
            current_time   # now
        )
        
        allowed = bool(result[0])
        remaining_tokens = result[1]
        
        return RateLimitResult(
            allowed=allowed,
            limit=config.limit,
            remaining=int(remaining_tokens),
            reset_time=int(current_time + config.window),
            retry_after=int(increment / refill_rate) if not allowed else None
        )
    
    async def _check_memory_rate_limit(
        self,
        key: str,
        config: RateLimitConfig,
        increment: int
    ) -> RateLimitResult:
        """使用内存检查限流"""
        current_time = time.time()
        window_start = current_time - config.window
        
        # 获取或创建请求历史
        if key not in self.memory_store:
            self.memory_store[key] = []
        
        request_history = self.memory_store[key]
        
        # 清理过期记录
        self.memory_store[key] = [
            timestamp for timestamp in request_history
            if timestamp > window_start
        ]
        
        current_count = len(self.memory_store[key])
        
        # 检查是否超限
        if current_count + increment > config.limit:
            return RateLimitResult(
                allowed=False,
                limit=config.limit,
                remaining=max(0, config.limit - current_count),
                reset_time=int(current_time + config.window),
                retry_after=int(config.window)
            )
        
        # 记录新请求
        for _ in range(increment):
            self.memory_store[key].append(current_time)
        
        return RateLimitResult(
            allowed=True,
            limit=config.limit,
            remaining=config.limit - current_count - increment,
            reset_time=int(current_time + config.window)
        )
    
    async def get_rate_limit_status(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """获取限流状态（不增加计数）"""
        return await self.check_rate_limit(key, config, increment=0)
    
    async def reset_rate_limit(self, key: str) -> bool:
        """重置限流计数"""
        try:
            if self.redis_client:
                await self.redis_client.delete(key)
                await self.redis_client.delete(f"bucket:{key}")
            else:
                self.memory_store.pop(key, None)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Reset rate limit error: {e}")
            return False
    
    def get_default_config(self, config_name: str) -> Optional[RateLimitConfig]:
        """获取预定义配置"""
        return self.default_configs.get(config_name)
    
    def add_default_config(self, name: str, config: RateLimitConfig):
        """添加预定义配置"""
        self.default_configs[name] = config


# 全局限流器实例
rate_limiter = None


async def get_rate_limiter() -> RateLimiter:
    """获取限流器实例"""
    global rate_limiter
    if rate_limiter is None:
        try:
            # 尝试连接Redis
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=1,  # 使用专门的数据库
                decode_responses=False
            )
            await redis_client.ping()
            rate_limiter = RateLimiter(redis_client)
        except:
            # Redis不可用时使用内存存储
            rate_limiter = RateLimiter()
    
    return rate_limiter


# 装饰器用法
def rate_limit(config_name: str, custom_config: Optional[RateLimitConfig] = None):
    """限流装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            limiter = await get_rate_limiter()
            
            # 生成限流键
            key = f"rate_limit:{func.__name__}"
            if args and hasattr(args[0], 'user_id'):
                key += f":{args[0].user_id}"
            
            # 获取配置
            config = custom_config or limiter.get_default_config(config_name)
            if not config:
                raise ValueError(f"Rate limit config not found: {config_name}")
            
            # 检查限流
            result = await limiter.check_rate_limit(key, config)
            
            if not result.allowed:
                raise Exception(f"Rate limit exceeded. Retry after {result.retry_after} seconds")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator