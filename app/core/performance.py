"""
Performance optimization module for multi-agent system
性能优化模块 - 提供缓存、连接池和资源管理功能
"""
import asyncio
import time
import weakref
import gc
from typing import Dict, Any, Optional, Callable, TypeVar, Generic, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict, OrderedDict
from concurrent.futures import ThreadPoolExecutor
import threading
import logging
import json
import hashlib
from enum import Enum

from .redis import get_redis
from .config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheLevel(str, Enum):
    """缓存级别"""
    MEMORY = "memory"
    REDIS = "redis"
    BOTH = "both"


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""
    value: T
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def touch(self) -> None:
        """更新访问时间和计数"""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


class LRUCache(Generic[T]):
    """LRU缓存实现"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: Optional[int] = None):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "size": 0,
            "memory_usage": 0
        }
    
    def get(self, key: str) -> Optional[T]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None
            
            entry = self._cache[key]
            
            # 检查过期
            if entry.is_expired():
                del self._cache[key]
                self._stats["misses"] += 1
                self._stats["size"] -= 1
                self._stats["memory_usage"] -= entry.size_bytes
                return None
            
            # 更新访问信息
            entry.touch()
            
            # 移动到末尾（最近使用）
            self._cache.move_to_end(key)
            
            self._stats["hits"] += 1
            return entry.value
    
    def put(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> None:
        """设置缓存值"""
        with self._lock:
            # 计算过期时间
            expires_at = None
            if ttl_seconds or self.ttl_seconds:
                ttl = ttl_seconds or self.ttl_seconds
                expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
            # 估算大小
            size_bytes = self._estimate_size(value)
            
            # 创建缓存条目
            entry = CacheEntry(
                value=value,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                size_bytes=size_bytes
            )
            
            # 如果key已存在，更新统计
            if key in self._cache:
                old_entry = self._cache[key]
                self._stats["memory_usage"] -= old_entry.size_bytes
            else:
                self._stats["size"] += 1
            
            self._cache[key] = entry
            self._cache.move_to_end(key)
            self._stats["memory_usage"] += size_bytes
            
            # 检查是否需要清理
            self._evict_if_needed()
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                del self._cache[key]
                self._stats["size"] -= 1
                self._stats["memory_usage"] -= entry.size_bytes
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._stats["size"] = 0
            self._stats["memory_usage"] = 0
    
    def _evict_if_needed(self) -> None:
        """如果需要则清理缓存"""
        while len(self._cache) > self.max_size:
            # 移除最久未使用的项
            key, entry = self._cache.popitem(last=False)
            self._stats["evictions"] += 1
            self._stats["size"] -= 1
            self._stats["memory_usage"] -= entry.size_bytes
    
    def _estimate_size(self, value: Any) -> int:
        """估算对象大小"""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, dict):
                return len(json.dumps(value, ensure_ascii=False).encode('utf-8'))
            elif hasattr(value, '__sizeof__'):
                return value.__sizeof__()
            else:
                return 1024  # 默认估算
        except:
            return 1024
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            hit_rate = self._stats["hits"] / (self._stats["hits"] + self._stats["misses"]) if (self._stats["hits"] + self._stats["misses"]) > 0 else 0
            return {
                **self._stats,
                "hit_rate": hit_rate,
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds
            }


class MultiLevelCache:
    """多级缓存系统"""
    
    def __init__(
        self,
        memory_max_size: int = 1000,
        memory_ttl: int = 300,
        redis_ttl: int = 3600,
        enable_redis: bool = True
    ):
        self.memory_cache = LRUCache[Any](memory_max_size, memory_ttl)
        self.redis_ttl = redis_ttl
        self.enable_redis = enable_redis
        self._redis_client = None
        
    async def _get_redis_client(self):
        """获取Redis客户端"""
        if not self.enable_redis:
            return None
        
        if self._redis_client is None:
            try:
                from .redis import get_redis
                self._redis_client = await get_redis()
            except Exception as e:
                logger.warning(f"Redis连接失败，禁用Redis缓存: {e}")
                self.enable_redis = False
                return None
        
        return self._redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        # 1. 先查内存缓存
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # 2. 查Redis缓存
        if self.enable_redis:
            try:
                redis_client = await self._get_redis_client()
                if redis_client:
                    redis_value = await redis_client.get(key)
                    if redis_value:
                        # 反序列化
                        value = json.loads(redis_value)
                        # 回填到内存缓存
                        self.memory_cache.put(key, value)
                        return value
            except Exception as e:
                logger.warning(f"Redis缓存读取失败: {e}")
        
        return None
    
    async def put(
        self, 
        key: str, 
        value: Any, 
        memory_ttl: Optional[int] = None,
        redis_ttl: Optional[int] = None
    ) -> None:
        """设置缓存值"""
        # 1. 设置内存缓存
        self.memory_cache.put(key, value, memory_ttl)
        
        # 2. 设置Redis缓存
        if self.enable_redis:
            try:
                redis_client = await self._get_redis_client()
                if redis_client:
                    serialized_value = json.dumps(value, ensure_ascii=False, default=str)
                    ttl = redis_ttl or self.redis_ttl
                    await redis_client.setex(key, ttl, serialized_value)
            except Exception as e:
                logger.warning(f"Redis缓存写入失败: {e}")
    
    async def delete(self, key: str) -> None:
        """删除缓存项"""
        # 删除内存缓存
        self.memory_cache.delete(key)
        
        # 删除Redis缓存
        if self.enable_redis:
            try:
                redis_client = await self._get_redis_client()
                if redis_client:
                    await redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis缓存删除失败: {e}")
    
    async def clear(self) -> None:
        """清空所有缓存"""
        self.memory_cache.clear()
        
        if self.enable_redis:
            try:
                redis_client = await self._get_redis_client()
                if redis_client:
                    await redis_client.flushdb()
            except Exception as e:
                logger.warning(f"Redis缓存清空失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "memory_cache": self.memory_cache.get_stats(),
            "redis_enabled": self.enable_redis,
            "redis_ttl": self.redis_ttl
        }


class ConnectionPool:
    """连接池管理器"""
    
    def __init__(
        self,
        max_connections: int = 10,
        min_connections: int = 2,
        connection_timeout: int = 30,
        idle_timeout: int = 300
    ):
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.connection_timeout = connection_timeout
        self.idle_timeout = idle_timeout
        
        self._pool: List[Any] = []
        self._in_use: set = set()
        self._lock = asyncio.Lock()
        self._condition = asyncio.Condition(self._lock)
        self._connection_factory: Optional[Callable] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        self._stats = {
            "created": 0,
            "destroyed": 0,
            "acquired": 0,
            "released": 0,
            "timeouts": 0,
            "current_size": 0,
            "in_use_count": 0
        }
    
    def set_connection_factory(self, factory: Callable) -> None:
        """设置连接工厂函数"""
        self._connection_factory = factory
    
    async def start(self) -> None:
        """启动连接池"""
        if not self._connection_factory:
            raise ValueError("Connection factory not set")
        
        # 创建最小连接数
        async with self._lock:
            for _ in range(self.min_connections):
                try:
                    conn = await self._create_connection()
                    self._pool.append(conn)
                except Exception as e:
                    logger.error(f"创建初始连接失败: {e}")
        
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_idle_connections())
        logger.info(f"连接池启动，初始连接数: {len(self._pool)}")
    
    async def stop(self) -> None:
        """停止连接池"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        async with self._lock:
            # 关闭所有连接
            for conn in self._pool + list(self._in_use):
                try:
                    await self._destroy_connection(conn)
                except Exception as e:
                    logger.error(f"关闭连接失败: {e}")
            
            self._pool.clear()
            self._in_use.clear()
        
        logger.info("连接池已停止")
    
    async def acquire(self, timeout: Optional[int] = None) -> Any:
        """获取连接"""
        timeout = timeout or self.connection_timeout
        
        try:
            async with asyncio.wait_for(self._condition, timeout=timeout):
                async with self._condition:
                    # 等待可用连接
                    while not self._pool and len(self._in_use) >= self.max_connections:
                        await self._condition.wait()
                    
                    # 从池中获取连接
                    if self._pool:
                        conn = self._pool.pop()
                    else:
                        # 创建新连接
                        conn = await self._create_connection()
                    
                    self._in_use.add(conn)
                    self._stats["acquired"] += 1
                    self._stats["in_use_count"] = len(self._in_use)
                    
                    return conn
        
        except asyncio.TimeoutError:
            self._stats["timeouts"] += 1
            raise TimeoutError(f"获取连接超时 ({timeout}s)")
    
    async def release(self, conn: Any) -> None:
        """释放连接"""
        async with self._condition:
            if conn in self._in_use:
                self._in_use.remove(conn)
                
                # 检查连接是否仍然有效
                if await self._is_connection_valid(conn):
                    self._pool.append(conn)
                else:
                    await self._destroy_connection(conn)
                
                self._stats["released"] += 1
                self._stats["in_use_count"] = len(self._in_use)
                self._stats["current_size"] = len(self._pool)
                
                # 通知等待的协程
                self._condition.notify()
    
    async def _create_connection(self) -> Any:
        """创建新连接"""
        conn = await self._connection_factory()
        self._stats["created"] += 1
        self._stats["current_size"] = len(self._pool)
        return conn
    
    async def _destroy_connection(self, conn: Any) -> None:
        """销毁连接"""
        try:
            if hasattr(conn, 'close'):
                await conn.close()
            elif hasattr(conn, 'disconnect'):
                await conn.disconnect()
        except Exception as e:
            logger.warning(f"销毁连接时出错: {e}")
        
        self._stats["destroyed"] += 1
        self._stats["current_size"] = len(self._pool)
    
    async def _is_connection_valid(self, conn: Any) -> bool:
        """检查连接是否有效"""
        try:
            # 这里应该根据具体的连接类型实现健康检查
            if hasattr(conn, 'ping'):
                await conn.ping()
            elif hasattr(conn, 'is_connected'):
                return conn.is_connected()
            return True
        except:
            return False
    
    async def _cleanup_idle_connections(self) -> None:
        """清理空闲连接"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                async with self._lock:
                    # 保持最小连接数
                    while len(self._pool) > self.min_connections:
                        conn = self._pool.pop(0)  # 移除最旧的连接
                        await self._destroy_connection(conn)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理空闲连接时出错: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计"""
        return {
            **self._stats,
            "max_connections": self.max_connections,
            "min_connections": self.min_connections,
            "pool_size": len(self._pool),
            "utilization": len(self._in_use) / self.max_connections if self.max_connections > 0 else 0
        }


class ResourceManager:
    """资源管理器"""
    
    def __init__(self):
        self._resources: Dict[str, Any] = {}
        self._resource_locks: Dict[str, asyncio.Lock] = {}
        self._resource_refs: Dict[str, weakref.ref] = {}
        self._cleanup_tasks: Dict[str, asyncio.Task] = {}
        self._stats = defaultdict(int)
    
    async def get_or_create_resource(
        self,
        resource_id: str,
        factory: Callable,
        cleanup_func: Optional[Callable] = None,
        ttl_seconds: Optional[int] = None
    ) -> Any:
        """获取或创建资源"""
        # 获取或创建锁
        if resource_id not in self._resource_locks:
            self._resource_locks[resource_id] = asyncio.Lock()
        
        async with self._resource_locks[resource_id]:
            # 检查资源是否存在且有效
            if resource_id in self._resources:
                resource = self._resources[resource_id]
                if self._is_resource_valid(resource):
                    self._stats[f"{resource_id}_hits"] += 1
                    return resource
                else:
                    # 资源无效，清理
                    await self._cleanup_resource(resource_id)
            
            # 创建新资源
            try:
                resource = await factory()
                self._resources[resource_id] = resource
                self._stats[f"{resource_id}_created"] += 1
                
                # 设置弱引用
                self._resource_refs[resource_id] = weakref.ref(
                    resource, 
                    lambda ref: asyncio.create_task(self._cleanup_resource(resource_id))
                )
                
                # 设置TTL清理任务
                if ttl_seconds:
                    self._cleanup_tasks[resource_id] = asyncio.create_task(
                        self._schedule_cleanup(resource_id, ttl_seconds)
                    )
                
                logger.info(f"创建资源: {resource_id}")
                return resource
                
            except Exception as e:
                self._stats[f"{resource_id}_errors"] += 1
                logger.error(f"创建资源失败 {resource_id}: {e}")
                raise
    
    async def release_resource(self, resource_id: str) -> None:
        """释放资源"""
        await self._cleanup_resource(resource_id)
    
    async def _cleanup_resource(self, resource_id: str) -> None:
        """清理资源"""
        if resource_id in self._resources:
            resource = self._resources[resource_id]
            
            try:
                # 调用清理函数
                if hasattr(resource, 'cleanup'):
                    await resource.cleanup()
                elif hasattr(resource, 'close'):
                    await resource.close()
            except Exception as e:
                logger.warning(f"清理资源时出错 {resource_id}: {e}")
            
            # 移除资源
            del self._resources[resource_id]
            self._stats[f"{resource_id}_cleaned"] += 1
            logger.info(f"清理资源: {resource_id}")
        
        # 清理相关数据
        self._resource_refs.pop(resource_id, None)
        
        if resource_id in self._cleanup_tasks:
            self._cleanup_tasks[resource_id].cancel()
            del self._cleanup_tasks[resource_id]
        
        if resource_id in self._resource_locks:
            del self._resource_locks[resource_id]
    
    async def _schedule_cleanup(self, resource_id: str, ttl_seconds: int) -> None:
        """调度资源清理"""
        try:
            await asyncio.sleep(ttl_seconds)
            await self._cleanup_resource(resource_id)
        except asyncio.CancelledError:
            pass
    
    def _is_resource_valid(self, resource: Any) -> bool:
        """检查资源是否有效"""
        try:
            if hasattr(resource, 'is_valid'):
                return resource.is_valid()
            elif hasattr(resource, 'is_connected'):
                return resource.is_connected()
            return True
        except:
            return False
    
    async def cleanup_all(self) -> None:
        """清理所有资源"""
        resource_ids = list(self._resources.keys())
        for resource_id in resource_ids:
            await self._cleanup_resource(resource_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取资源统计"""
        return {
            "active_resources": len(self._resources),
            "resource_types": list(self._resources.keys()),
            "stats": dict(self._stats)
        }


class MemoryOptimizer:
    """内存优化器"""
    
    def __init__(self, gc_threshold: int = 100, memory_limit_mb: int = 512):
        self.gc_threshold = gc_threshold
        self.memory_limit_mb = memory_limit_mb
        self._gc_counter = 0
        self._last_gc_time = time.time()
        self._memory_stats = {
            "gc_runs": 0,
            "objects_collected": 0,
            "memory_freed_mb": 0
        }
    
    def check_and_optimize(self) -> Dict[str, Any]:
        """检查并优化内存使用"""
        self._gc_counter += 1
        current_time = time.time()
        
        # 定期运行垃圾回收
        if (self._gc_counter >= self.gc_threshold or 
            current_time - self._last_gc_time > 300):  # 5分钟
            
            return self._run_garbage_collection()
        
        return {"optimized": False}
    
    def _run_garbage_collection(self) -> Dict[str, Any]:
        """运行垃圾回收"""
        import psutil
        import os
        
        # 获取当前内存使用
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # 运行垃圾回收
        collected = gc.collect()
        
        # 获取回收后内存使用
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_freed = memory_before - memory_after
        
        # 更新统计
        self._memory_stats["gc_runs"] += 1
        self._memory_stats["objects_collected"] += collected
        self._memory_stats["memory_freed_mb"] += memory_freed
        
        self._gc_counter = 0
        self._last_gc_time = time.time()
        
        logger.info(f"垃圾回收完成: 回收对象 {collected}, 释放内存 {memory_freed:.2f}MB")
        
        return {
            "optimized": True,
            "objects_collected": collected,
            "memory_freed_mb": memory_freed,
            "memory_before_mb": memory_before,
            "memory_after_mb": memory_after
        }
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent(),
                "available_mb": psutil.virtual_memory().available / 1024 / 1024,
                "gc_stats": self._memory_stats
            }
        except ImportError:
            return {"error": "psutil not available"}
    
    def force_cleanup(self) -> Dict[str, Any]:
        """强制清理内存"""
        return self._run_garbage_collection()


# 全局实例
_cache_manager: Optional[MultiLevelCache] = None
_connection_pools: Dict[str, ConnectionPool] = {}
_resource_manager: Optional[ResourceManager] = None
_memory_optimizer: Optional[MemoryOptimizer] = None


def get_cache_manager() -> MultiLevelCache:
    """获取缓存管理器"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = MultiLevelCache(
            memory_max_size=settings.DATABASE_POOL_SIZE * 10,
            memory_ttl=settings.REDIS_CACHE_TTL,
            redis_ttl=settings.REDIS_CACHE_TTL * 2,
            enable_redis=True
        )
    return _cache_manager


def get_connection_pool(pool_name: str) -> ConnectionPool:
    """获取连接池"""
    global _connection_pools
    if pool_name not in _connection_pools:
        _connection_pools[pool_name] = ConnectionPool(
            max_connections=settings.DATABASE_POOL_SIZE,
            min_connections=max(2, settings.DATABASE_POOL_SIZE // 5),
            connection_timeout=30,
            idle_timeout=300
        )
    return _connection_pools[pool_name]


def get_resource_manager() -> ResourceManager:
    """获取资源管理器"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


def get_memory_optimizer() -> MemoryOptimizer:
    """获取内存优化器"""
    global _memory_optimizer
    if _memory_optimizer is None:
        _memory_optimizer = MemoryOptimizer(
            gc_threshold=100,
            memory_limit_mb=512
        )
    return _memory_optimizer


def cache_result(
    key_prefix: str = "",
    ttl_seconds: int = 300,
    cache_level: CacheLevel = CacheLevel.BOTH
):
    """缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = _generate_cache_key(key_prefix, func.__name__, args, kwargs)
            
            # 尝试从缓存获取
            cache_manager = get_cache_manager()
            cached_result = await cache_manager.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 存储到缓存
            await cache_manager.put(cache_key, result, ttl_seconds, ttl_seconds * 2)
            
            return result
        
        return wrapper
    return decorator


def _generate_cache_key(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """生成缓存键"""
    # 创建参数的哈希
    params_str = f"{args}_{sorted(kwargs.items())}"
    params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
    
    return f"{prefix}:{func_name}:{params_hash}"


async def get_performance_stats() -> Dict[str, Any]:
    """获取性能统计信息"""
    stats = {
        "timestamp": datetime.utcnow().isoformat(),
        "cache": get_cache_manager().get_stats(),
        "connection_pools": {
            name: pool.get_stats() 
            for name, pool in _connection_pools.items()
        },
        "resources": get_resource_manager().get_stats(),
        "memory": get_memory_optimizer().get_memory_usage()
    }
    
    return stats


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self._metrics = defaultdict(list)
        self._start_times = {}
        self._lock = threading.Lock()
        
    def start_timer(self, operation: str) -> str:
        """开始计时"""
        timer_id = f"{operation}_{int(time.time() * 1000000)}"
        self._start_times[timer_id] = time.time()
        return timer_id
    
    def end_timer(self, timer_id: str) -> float:
        """结束计时并记录"""
        if timer_id not in self._start_times:
            return 0.0
        
        duration = time.time() - self._start_times[timer_id]
        del self._start_times[timer_id]
        
        # 提取操作名称
        operation = timer_id.rsplit('_', 1)[0]
        
        with self._lock:
            self._metrics[operation].append({
                'duration': duration,
                'timestamp': time.time()
            })
            
            # 保持最近1000条记录
            if len(self._metrics[operation]) > 1000:
                self._metrics[operation] = self._metrics[operation][-1000:]
        
        return duration
    
    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """记录指标"""
        with self._lock:
            self._metrics[name].append({
                'value': value,
                'timestamp': time.time(),
                'labels': labels or {}
            })
            
            # 保持最近1000条记录
            if len(self._metrics[name]) > 1000:
                self._metrics[name] = self._metrics[name][-1000:]
    
    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            if operation:
                if operation not in self._metrics:
                    return {}
                
                data = self._metrics[operation]
                if not data:
                    return {}
                
                durations = [item.get('duration', item.get('value', 0)) for item in data]
                return {
                    'count': len(durations),
                    'avg': sum(durations) / len(durations),
                    'min': min(durations),
                    'max': max(durations),
                    'recent': durations[-10:] if len(durations) >= 10 else durations
                }
            else:
                stats = {}
                for op, data in self._metrics.items():
                    if data:
                        durations = [item.get('duration', item.get('value', 0)) for item in data]
                        stats[op] = {
                            'count': len(durations),
                            'avg': sum(durations) / len(durations),
                            'min': min(durations),
                            'max': max(durations)
                        }
                return stats


class AsyncBatchProcessor:
    """异步批处理器"""
    
    def __init__(self, batch_size: int = 10, flush_interval: float = 1.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._batch = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._processor_func: Optional[Callable] = None
        
    async def start(self, processor_func: Callable):
        """启动批处理器"""
        self._processor_func = processor_func
        self._flush_task = asyncio.create_task(self._flush_loop())
        
    async def stop(self):
        """停止批处理器"""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # 处理剩余项目
        if self._batch:
            await self._flush_batch()
    
    async def add_item(self, item: Any):
        """添加项目到批处理"""
        async with self._lock:
            self._batch.append(item)
            
            if len(self._batch) >= self.batch_size:
                await self._flush_batch()
    
    async def _flush_batch(self):
        """刷新批处理"""
        if not self._batch or not self._processor_func:
            return
        
        batch_to_process = self._batch.copy()
        self._batch.clear()
        
        try:
            await self._processor_func(batch_to_process)
        except Exception as e:
            logger.error(f"批处理失败: {e}")
    
    async def _flush_loop(self):
        """定期刷新循环"""
        try:
            while True:
                await asyncio.sleep(self.flush_interval)
                async with self._lock:
                    if self._batch:
                        await self._flush_batch()
        except asyncio.CancelledError:
            pass


class CircuitBreaker:
    """熔断器"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._failure_count = 0
        self._last_failure_time = None
        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def __call__(self, func):
        """装饰器用法"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        return wrapper
    
    async def call(self, func, *args, **kwargs):
        """调用函数并应用熔断逻辑"""
        with self._lock:
            if self._state == "OPEN":
                if self._should_attempt_reset():
                    self._state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置"""
        return (
            self._last_failure_time and
            time.time() - self._last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """成功时的处理"""
        with self._lock:
            self._failure_count = 0
            self._state = "CLOSED"
    
    def _on_failure(self):
        """失败时的处理"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._failure_count >= self.failure_threshold:
                self._state = "OPEN"
    
    def get_state(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        with self._lock:
            return {
                "state": self._state,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "last_failure_time": self._last_failure_time,
                "recovery_timeout": self.recovery_timeout
            }


# 全局性能监控器
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def performance_timer(operation: str):
    """性能计时装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            timer_id = monitor.start_timer(operation)
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                monitor.end_timer(timer_id)
        return wrapper
    return decorator


async def cleanup_performance_resources() -> None:
    """清理性能相关资源"""
    # 清理缓存
    if _cache_manager:
        await _cache_manager.clear()
    
    # 停止连接池
    for pool in _connection_pools.values():
        await pool.stop()
    _connection_pools.clear()
    
    # 清理资源管理器
    if _resource_manager:
        await _resource_manager.cleanup_all()
    
    # 强制垃圾回收
    if _memory_optimizer:
        _memory_optimizer.force_cleanup()
    
    logger.info("性能资源清理完成")