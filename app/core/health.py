"""
Health check and monitoring endpoints
健康检查和监控端点
"""
import asyncio
import time
import psutil
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db, db_manager
from .redis import get_redis
from .config import settings
from ..agent.unified_config import get_config_manager
from ..agent.concurrent_processor import get_concurrent_processor
from ..core.performance import get_performance_stats

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """组件健康状态"""
    name: str
    status: HealthStatus
    response_time_ms: float
    details: Dict[str, Any]
    error: Optional[str] = None
    last_check: datetime = None
    
    def __post_init__(self):
        if self.last_check is None:
            self.last_check = datetime.utcnow()


@dataclass
class SystemHealth:
    """系统健康状态"""
    status: HealthStatus
    timestamp: datetime
    uptime_seconds: float
    components: List[ComponentHealth]
    performance_metrics: Dict[str, Any]
    version: str = "1.0.0"
    environment: str = "development"


class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.start_time = time.time()
        self.check_history: List[SystemHealth] = []
        self.max_history = 100
    
    async def check_database_health(self) -> ComponentHealth:
        """检查数据库健康状态"""
        start_time = time.time()
        
        try:
            async with db_manager.get_session() as session:
                # 执行简单查询
                result = await session.execute(text("SELECT 1"))
                result.fetchone()
                
                # 检查连接池状态
                pool_info = {
                    "pool_size": session.bind.pool.size(),
                    "checked_in": session.bind.pool.checkedin(),
                    "checked_out": session.bind.pool.checkedout(),
                    "overflow": session.bind.pool.overflow(),
                    "invalid": session.bind.pool.invalid()
                }
                
                response_time = (time.time() - start_time) * 1000
                
                # 判断健康状态
                if response_time > 1000:  # 超过1秒认为性能下降
                    status = HealthStatus.DEGRADED
                elif pool_info["checked_out"] / session.bind.pool.size() > 0.8:  # 连接池使用率超过80%
                    status = HealthStatus.DEGRADED
                else:
                    status = HealthStatus.HEALTHY
                
                return ComponentHealth(
                    name="database",
                    status=status,
                    response_time_ms=response_time,
                    details={
                        "connection_pool": pool_info,
                        "database_url": settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else "hidden"
                    }
                )
        
        except Exception as e:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                details={},
                error=str(e)
            )
    
    async def check_redis_health(self) -> ComponentHealth:
        """检查Redis健康状态"""
        start_time = time.time()
        
        try:
            redis_client = await get_redis()
            
            # 执行ping命令
            await redis_client.ping()
            
            # 获取Redis信息
            info = await redis_client.info()
            
            response_time = (time.time() - start_time) * 1000
            
            # 判断健康状态
            memory_usage = info.get('used_memory', 0) / info.get('maxmemory', 1) if info.get('maxmemory', 0) > 0 else 0
            
            if response_time > 500:  # 超过500ms认为性能下降
                status = HealthStatus.DEGRADED
            elif memory_usage > 0.9:  # 内存使用率超过90%
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return ComponentHealth(
                name="redis",
                status=status,
                response_time_ms=response_time,
                details={
                    "version": info.get('redis_version', 'unknown'),
                    "connected_clients": info.get('connected_clients', 0),
                    "used_memory_human": info.get('used_memory_human', 'unknown'),
                    "memory_usage_percent": round(memory_usage * 100, 2) if memory_usage else 0,
                    "keyspace_hits": info.get('keyspace_hits', 0),
                    "keyspace_misses": info.get('keyspace_misses', 0)
                }
            )
        
        except Exception as e:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                details={},
                error=str(e)
            )
    
    async def check_agent_system_health(self) -> ComponentHealth:
        """检查Agent系统健康状态"""
        start_time = time.time()
        
        try:
            # 检查配置管理器
            config_manager = get_config_manager()
            
            # 检查并发处理器
            concurrent_processor = await get_concurrent_processor()
            processor_stats = concurrent_processor.get_stats()
            
            response_time = (time.time() - start_time) * 1000
            
            # 判断健康状态
            if not processor_stats.get("initialized", False):
                status = HealthStatus.UNHEALTHY
            elif processor_stats.get("main_pool", {}).get("active_workers", 0) == 0:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return ComponentHealth(
                name="agent_system",
                status=status,
                response_time_ms=response_time,
                details={
                    "config_manager_initialized": config_manager is not None,
                    "concurrent_processor_stats": processor_stats,
                    "available_agents": len(processor_stats.get("agent_pools", {}))
                }
            )
        
        except Exception as e:
            return ComponentHealth(
                name="agent_system",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                details={},
                error=str(e)
            )
    
    async def check_external_services_health(self) -> ComponentHealth:
        """检查外部服务健康状态"""
        start_time = time.time()
        
        try:
            # 这里可以添加对PPIO API等外部服务的健康检查
            # 目前只做基本的配置检查
            
            ppio_config_valid = bool(settings.PPIO_API_KEY and settings.PPIO_API_KEY != "sk_your_ppio_api_key_here")
            google_config_valid = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
            
            response_time = (time.time() - start_time) * 1000
            
            if not ppio_config_valid or not google_config_valid:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return ComponentHealth(
                name="external_services",
                status=status,
                response_time_ms=response_time,
                details={
                    "ppio_configured": ppio_config_valid,
                    "google_oauth_configured": google_config_valid,
                    "ppio_base_url": settings.PPIO_BASE_URL,
                    "ppio_model": settings.PPIO_MODEL_NAME
                }
            )
        
        except Exception as e:
            return ComponentHealth(
                name="external_services",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                details={},
                error=str(e)
            )
    
    def check_system_resources(self) -> ComponentHealth:
        """检查系统资源"""
        start_time = time.time()
        
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            
            # 网络统计
            network = psutil.net_io_counters()
            
            response_time = (time.time() - start_time) * 1000
            
            # 判断健康状态
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                status = HealthStatus.UNHEALTHY
            elif cpu_percent > 70 or memory.percent > 70 or disk.percent > 80:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            
            return ComponentHealth(
                name="system_resources",
                status=status,
                response_time_ms=response_time,
                details={
                    "cpu_percent": cpu_percent,
                    "memory": {
                        "total_gb": round(memory.total / (1024**3), 2),
                        "available_gb": round(memory.available / (1024**3), 2),
                        "percent": memory.percent
                    },
                    "disk": {
                        "total_gb": round(disk.total / (1024**3), 2),
                        "free_gb": round(disk.free / (1024**3), 2),
                        "percent": disk.percent
                    },
                    "network": {
                        "bytes_sent": network.bytes_sent,
                        "bytes_recv": network.bytes_recv,
                        "packets_sent": network.packets_sent,
                        "packets_recv": network.packets_recv
                    }
                }
            )
        
        except Exception as e:
            return ComponentHealth(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                details={},
                error=str(e)
            )
    
    async def perform_full_health_check(self) -> SystemHealth:
        """执行完整的健康检查"""
        check_start = time.time()
        
        # 并发执行所有健康检查
        health_checks = await asyncio.gather(
            self.check_database_health(),
            self.check_redis_health(),
            self.check_agent_system_health(),
            self.check_external_services_health(),
            asyncio.to_thread(self.check_system_resources),
            return_exceptions=True
        )
        
        components = []
        for check in health_checks:
            if isinstance(check, ComponentHealth):
                components.append(check)
            else:
                # 处理异常情况
                logger.error(f"Health check failed: {check}")
                components.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    details={},
                    error=str(check)
                ))
        
        # 确定整体健康状态
        overall_status = self._determine_overall_status(components)
        
        # 获取性能指标
        try:
            performance_metrics = await get_performance_stats()
        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}")
            performance_metrics = {"error": str(e)}
        
        system_health = SystemHealth(
            status=overall_status,
            timestamp=datetime.utcnow(),
            uptime_seconds=time.time() - self.start_time,
            components=components,
            performance_metrics=performance_metrics,
            version=getattr(settings, 'VERSION', '1.0.0'),
            environment=settings.ENVIRONMENT
        )
        
        # 保存到历史记录
        self.check_history.append(system_health)
        if len(self.check_history) > self.max_history:
            self.check_history.pop(0)
        
        logger.info(f"Health check completed in {(time.time() - check_start)*1000:.2f}ms, status: {overall_status}")
        
        return system_health
    
    def _determine_overall_status(self, components: List[ComponentHealth]) -> HealthStatus:
        """确定整体健康状态"""
        if not components:
            return HealthStatus.UNHEALTHY
        
        unhealthy_count = sum(1 for c in components if c.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for c in components if c.status == HealthStatus.DEGRADED)
        
        # 如果有任何组件不健康，整体状态为不健康
        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY
        
        # 如果有组件性能下降，整体状态为性能下降
        if degraded_count > 0:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    async def get_basic_health(self) -> Dict[str, Any]:
        """获取基本健康状态（快速检查）"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - self.start_time,
            "version": getattr(settings, 'VERSION', '1.0.0'),
            "environment": settings.ENVIRONMENT
        }
    
    def get_health_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取健康检查历史"""
        recent_checks = self.check_history[-limit:] if self.check_history else []
        return [asdict(check) for check in recent_checks]
    
    def get_component_health(self, component_name: str) -> Optional[ComponentHealth]:
        """获取特定组件的健康状态"""
        if not self.check_history:
            return None
        
        latest_check = self.check_history[-1]
        for component in latest_check.components:
            if component.name == component_name:
                return component
        
        return None


# 全局健康检查器实例
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """获取健康检查器实例"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


# 便捷函数
async def check_health() -> Dict[str, Any]:
    """执行健康检查并返回结果"""
    health_checker = get_health_checker()
    system_health = await health_checker.perform_full_health_check()
    return asdict(system_health)


async def check_basic_health() -> Dict[str, Any]:
    """执行基本健康检查"""
    health_checker = get_health_checker()
    return await health_checker.get_basic_health()


def get_health_history(limit: int = 10) -> List[Dict[str, Any]]:
    """获取健康检查历史"""
    health_checker = get_health_checker()
    return health_checker.get_health_history(limit)


# 兼容main分支的函数
async def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health status (compatibility function)"""
    return await check_health()