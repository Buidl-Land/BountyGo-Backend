"""
Agent result caching system
Agent结果缓存系统 - 提供智能缓存和结果复用功能
"""
import asyncio
import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from ..core.performance import get_cache_manager, cache_result
from .structured_logging import get_logger

logger = get_logger(__name__)


class CacheStrategy(str, Enum):
    """缓存策略"""
    NONE = "none"           # 不缓存
    MEMORY = "memory"       # 仅内存缓存
    REDIS = "redis"         # 仅Redis缓存
    BOTH = "both"           # 内存+Redis缓存
    SMART = "smart"         # 智能缓存策略


@dataclass
class CacheConfig:
    """缓存配置"""
    strategy: CacheStrategy = CacheStrategy.SMART
    memory_ttl: int = 300           # 内存缓存TTL（秒）
    redis_ttl: int = 3600          # Redis缓存TTL（秒）
    max_memory_size: int = 1000    # 最大内存缓存条目数
    enable_compression: bool = True # 启用压缩
    cache_negative_results: bool = False  # 缓存负面结果
    negative_result_ttl: int = 60  # 负面结果TTL


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def touch(self) -> None:
        """更新访问信息"""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


class AgentResultCache:
    """Agent结果缓存器"""
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.cache_manager = get_cache_manager()
        
        # 统计信息
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "errors": 0
        }
        
        # 缓存键前缀
        self.key_prefix = "agent_result"
    
    def _generate_cache_key(
        self,
        agent_name: str,
        method_name: str,
        args: tuple,
        kwargs: dict,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成缓存键"""
        # 创建参数的标准化表示
        params_data = {
            "args": args,
            "kwargs": sorted(kwargs.items()) if kwargs else {},
            "user_context": user_context or {}
        }
        
        # 生成参数哈希
        params_str = json.dumps(params_data, sort_keys=True, default=str)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:12]
        
        return f"{self.key_prefix}:{agent_name}:{method_name}:{params_hash}"
    
    async def get(
        self,
        agent_name: str,
        method_name: str,
        args: tuple,
        kwargs: dict,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """获取缓存结果"""
        if self.config.strategy == CacheStrategy.NONE:
            return None
        
        cache_key = self._generate_cache_key(agent_name, method_name, args, kwargs, user_context)
        
        try:
            result = await self.cache_manager.get(cache_key)
            
            if result is not None:
                self._stats["hits"] += 1
                logger.debug(f"缓存命中: {cache_key}")
                
                # 如果是压缩的结果，解压缩
                if self.config.enable_compression and isinstance(result, dict) and result.get("_compressed"):
                    result = self._decompress_result(result)
                
                return result
            else:
                self._stats["misses"] += 1
                logger.debug(f"缓存未命中: {cache_key}")
                return None
                
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"缓存读取错误: {e}")
            return None
    
    async def set(
        self,
        agent_name: str,
        method_name: str,
        args: tuple,
        kwargs: dict,
        result: Any,
        user_context: Optional[Dict[str, Any]] = None,
        custom_ttl: Optional[int] = None
    ) -> bool:
        """设置缓存结果"""
        if self.config.strategy == CacheStrategy.NONE:
            return False
        
        # 检查是否应该缓存负面结果
        if not self.config.cache_negative_results and self._is_negative_result(result):
            return False
        
        cache_key = self._generate_cache_key(agent_name, method_name, args, kwargs, user_context)
        
        try:
            # 压缩结果（如果启用）
            cached_result = result
            if self.config.enable_compression:
                cached_result = self._compress_result(result)
            
            # 确定TTL
            if self._is_negative_result(result):
                memory_ttl = self.config.negative_result_ttl
                redis_ttl = self.config.negative_result_ttl
            else:
                memory_ttl = custom_ttl or self.config.memory_ttl
                redis_ttl = custom_ttl or self.config.redis_ttl
            
            await self.cache_manager.put(
                cache_key,
                cached_result,
                memory_ttl=memory_ttl,
                redis_ttl=redis_ttl
            )
            
            self._stats["sets"] += 1
            logger.debug(f"缓存设置: {cache_key}")
            return True
            
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"缓存写入错误: {e}")
            return False
    
    async def invalidate(
        self,
        agent_name: str,
        method_name: Optional[str] = None,
        pattern: Optional[str] = None
    ) -> int:
        """失效缓存"""
        try:
            if pattern:
                # 使用模式匹配失效
                invalidated_count = await self._invalidate_by_pattern(pattern)
            elif method_name:
                # 失效特定方法的所有缓存
                pattern = f"{self.key_prefix}:{agent_name}:{method_name}:*"
                invalidated_count = await self._invalidate_by_pattern(pattern)
            else:
                # 失效Agent的所有缓存
                pattern = f"{self.key_prefix}:{agent_name}:*"
                invalidated_count = await self._invalidate_by_pattern(pattern)
            
            logger.info(f"失效缓存 {invalidated_count} 条: {agent_name}.{method_name or 'all'}")
            return invalidated_count
            
        except Exception as e:
            logger.error(f"缓存失效错误: {e}")
            return 0
    
    async def _invalidate_by_pattern(self, pattern: str) -> int:
        """按模式失效缓存"""
        # 这里需要实现模式匹配的缓存失效
        # 由于当前的缓存管理器可能不支持模式匹配，这里简化实现
        logger.warning(f"模式匹配缓存失效暂未完全实现: {pattern}")
        return 0
    
    def _is_negative_result(self, result: Any) -> bool:
        """判断是否为负面结果"""
        if result is None:
            return True
        
        if isinstance(result, dict):
            # 检查是否包含错误信息
            if result.get("error") or result.get("success") is False:
                return True
        
        if isinstance(result, str) and result.lower() in ["error", "failed", "none"]:
            return True
        
        return False
    
    def _compress_result(self, result: Any) -> Dict[str, Any]:
        """压缩结果"""
        try:
            import gzip
            import base64
            
            # 序列化结果
            serialized = json.dumps(result, default=str)
            
            # 只有当结果足够大时才压缩
            if len(serialized) > 1024:  # 1KB
                compressed = gzip.compress(serialized.encode())
                encoded = base64.b64encode(compressed).decode()
                
                return {
                    "_compressed": True,
                    "_data": encoded,
                    "_original_size": len(serialized),
                    "_compressed_size": len(encoded)
                }
            else:
                return result
                
        except Exception as e:
            logger.warning(f"结果压缩失败: {e}")
            return result
    
    def _decompress_result(self, compressed_result: Dict[str, Any]) -> Any:
        """解压缩结果"""
        try:
            import gzip
            import base64
            
            encoded_data = compressed_result["_data"]
            compressed_data = base64.b64decode(encoded_data.encode())
            decompressed = gzip.decompress(compressed_data)
            
            return json.loads(decompressed.decode())
            
        except Exception as e:
            logger.error(f"结果解压缩失败: {e}")
            return compressed_result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        hit_rate = self._stats["hits"] / (self._stats["hits"] + self._stats["misses"]) if (self._stats["hits"] + self._stats["misses"]) > 0 else 0
        
        return {
            **self._stats,
            "hit_rate": hit_rate,
            "config": {
                "strategy": self.config.strategy.value,
                "memory_ttl": self.config.memory_ttl,
                "redis_ttl": self.config.redis_ttl,
                "compression_enabled": self.config.enable_compression,
                "cache_negative_results": self.config.cache_negative_results
            }
        }


def cached_agent_method(
    cache_config: Optional[CacheConfig] = None,
    ttl: Optional[int] = None,
    cache_key_func: Optional[Callable] = None
):
    """Agent方法缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        cache = AgentResultCache(cache_config)
        
        async def wrapper(self, *args, **kwargs):
            # 提取用户上下文
            user_context = kwargs.pop('_user_context', None)
            
            # 生成缓存键
            agent_name = self.__class__.__name__
            method_name = func.__name__
            
            # 尝试从缓存获取
            cached_result = await cache.get(
                agent_name, method_name, args, kwargs, user_context
            )
            
            if cached_result is not None:
                return cached_result
            
            # 执行原函数
            result = await func(self, *args, **kwargs)
            
            # 缓存结果
            await cache.set(
                agent_name, method_name, args, kwargs, result, 
                user_context, ttl
            )
            
            return result
        
        return wrapper
    return decorator


class SmartCacheManager:
    """智能缓存管理器"""
    
    def __init__(self):
        self._agent_caches: Dict[str, AgentResultCache] = {}
        self._global_config = CacheConfig()
        
    def get_agent_cache(self, agent_name: str, config: Optional[CacheConfig] = None) -> AgentResultCache:
        """获取Agent专用缓存"""
        if agent_name not in self._agent_caches:
            self._agent_caches[agent_name] = AgentResultCache(config or self._global_config)
        return self._agent_caches[agent_name]
    
    async def warm_up_cache(self, agent_name: str, warm_up_data: List[Dict[str, Any]]):
        """预热缓存"""
        cache = self.get_agent_cache(agent_name)
        
        for data in warm_up_data:
            await cache.set(
                agent_name=data["agent_name"],
                method_name=data["method_name"],
                args=data.get("args", ()),
                kwargs=data.get("kwargs", {}),
                result=data["result"],
                user_context=data.get("user_context")
            )
        
        logger.info(f"缓存预热完成: {agent_name}, 条目数: {len(warm_up_data)}")
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """获取全局缓存统计"""
        stats = {}
        total_hits = 0
        total_misses = 0
        
        for agent_name, cache in self._agent_caches.items():
            agent_stats = cache.get_stats()
            stats[agent_name] = agent_stats
            total_hits += agent_stats["hits"]
            total_misses += agent_stats["misses"]
        
        global_hit_rate = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0
        
        return {
            "agents": stats,
            "global": {
                "total_hits": total_hits,
                "total_misses": total_misses,
                "global_hit_rate": global_hit_rate,
                "active_agents": len(self._agent_caches)
            }
        }
    
    async def cleanup_expired_caches(self):
        """清理过期缓存"""
        for agent_name, cache in self._agent_caches.items():
            try:
                # 这里可以实现更复杂的清理逻辑
                logger.debug(f"清理Agent缓存: {agent_name}")
            except Exception as e:
                logger.error(f"清理缓存失败 {agent_name}: {e}")


# 全局智能缓存管理器
_smart_cache_manager: Optional[SmartCacheManager] = None


def get_smart_cache_manager() -> SmartCacheManager:
    """获取智能缓存管理器"""
    global _smart_cache_manager
    if _smart_cache_manager is None:
        _smart_cache_manager = SmartCacheManager()
    return _smart_cache_manager