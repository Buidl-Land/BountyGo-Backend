"""
Service factory for URL agent components.
"""
import logging
from functools import lru_cache
from typing import Optional

from sqlalchemy.orm import Session

from .client import PPIOModelClient
from .config import url_agent_settings, PPIOModelConfig
from .url_parsing_agent import URLParsingAgent
from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class URLAgentServiceFactory:
    """URL代理服务工厂"""
    
    _ppio_client: Optional[PPIOModelClient] = None
    _url_parsing_agent: Optional[URLParsingAgent] = None
    
    @classmethod
    def get_ppio_client(cls) -> PPIOModelClient:
        """获取PPIO模型客户端单例"""
        if cls._ppio_client is None:
            try:
                config = url_agent_settings.get_ppio_config()
                cls._ppio_client = PPIOModelClient(config)
                logger.info(f"PPIO client initialized with model: {config.model_name}")
            except ValueError as e:
                logger.warning(f"PPIO client not configured: {e}")
                raise ConfigurationError(f"PPIO client not configured: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to initialize PPIO client: {e}")
                raise ConfigurationError(f"PPIO client initialization failed: {str(e)}")
        
        return cls._ppio_client
    
    @classmethod
    def get_url_parsing_agent(cls) -> URLParsingAgent:
        """获取URL解析代理单例"""
        if cls._url_parsing_agent is None:
            try:
                config = url_agent_settings.get_ppio_config()
                cls._url_parsing_agent = URLParsingAgent(config)
                logger.info("URL parsing agent initialized")
            except ValueError as e:
                logger.warning(f"URL parsing agent not configured: {e}")
                raise ConfigurationError(f"URL parsing agent not configured: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to initialize URL parsing agent: {e}")
                raise ConfigurationError(f"URL parsing agent initialization failed: {str(e)}")
        
        return cls._url_parsing_agent
    
    @classmethod
    async def test_ppio_connection(cls) -> bool:
        """测试PPIO连接"""
        try:
            client = cls.get_ppio_client()
            return await client.test_connection()
        except Exception as e:
            logger.error(f"PPIO connection test failed: {e}")
            return False
    
    @classmethod
    async def test_url_parsing_agent(cls) -> bool:
        """测试URL解析代理"""
        try:
            agent = cls.get_url_parsing_agent()
            return await agent.test_agent()
        except Exception as e:
            logger.error(f"URL parsing agent test failed: {e}")
            return False
    
    @classmethod
    async def cleanup(cls):
        """清理资源"""
        if cls._ppio_client:
            await cls._ppio_client.close()
            cls._ppio_client = None
        
        if cls._url_parsing_agent:
            cls._url_parsing_agent = None


# 便捷函数
@lru_cache()
def get_ppio_client() -> PPIOModelClient:
    """获取PPIO客户端"""
    return URLAgentServiceFactory.get_ppio_client()


@lru_cache()
def get_ppio_config() -> PPIOModelConfig:
    """获取PPIO配置"""
    return url_agent_settings.get_ppio_config()


@lru_cache()
def get_url_parsing_agent() -> URLParsingAgent:
    """获取URL解析代理"""
    return URLAgentServiceFactory.get_url_parsing_agent()


async def test_ppio_connection() -> bool:
    """测试PPIO连接"""
    return await URLAgentServiceFactory.test_ppio_connection()


async def test_url_parsing_agent() -> bool:
    """测试URL解析代理"""
    return await URLAgentServiceFactory.test_url_parsing_agent()