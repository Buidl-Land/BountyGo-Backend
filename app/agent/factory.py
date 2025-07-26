"""
Service factory for URL agent components.
"""
import logging
from functools import lru_cache
from typing import Optional

from sqlalchemy.orm import Session

from .client import PPIOModelClient
from .config import url_agent_settings, PPIOModelConfig
from .unified_config import get_config_manager, AgentRole
from .url_parsing_agent import URLParsingAgent
from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class URLAgentServiceFactory:
    """URL代理服务工厂"""
    
    _ppio_client: Optional[PPIOModelClient] = None
    _url_parsing_agent: Optional[URLParsingAgent] = None
    
    @classmethod
    def get_ppio_client(cls, agent_role: Optional[str] = None) -> PPIOModelClient:
        """获取PPIO模型客户端，支持按角色选择最佳模型"""
        # 为不同角色创建不同的客户端实例
        client_key = agent_role or "default"
        
        if not hasattr(cls, '_ppio_clients'):
            cls._ppio_clients = {}
        
        if client_key not in cls._ppio_clients:
            try:
                # 优先使用统一配置
                config_manager = get_config_manager()
                
                # 根据角色映射到AgentRole
                role_mapping = {
                    "url_parser": AgentRole.URL_PARSER,
                    "image_analyzer": AgentRole.IMAGE_ANALYZER,
                    "content_extractor": AgentRole.CONTENT_EXTRACTOR,
                    "task_creator": AgentRole.TASK_CREATOR,
                    "quality_checker": AgentRole.QUALITY_CHECKER,
                    "coordinator": AgentRole.COORDINATOR
                }
                
                agent_role_enum = role_mapping.get(agent_role, AgentRole.URL_PARSER)
                url_agent_config = config_manager.get_agent_config(agent_role_enum)
                
                if url_agent_config:
                    config = PPIOModelConfig(
                        api_key=url_agent_config.api_key,
                        base_url=url_agent_config.base_url or "https://api.ppinfra.com/v3/openai",
                        model_name=url_agent_config.model_name,
                        max_tokens=url_agent_config.max_tokens,
                        temperature=url_agent_config.temperature,
                        timeout=url_agent_config.timeout,
                        max_retries=url_agent_config.max_retries
                    )
                else:
                    # 回退到传统配置，支持角色特定模型
                    config = url_agent_settings.get_ppio_config(agent_role)
                
                cls._ppio_clients[client_key] = PPIOModelClient(config)
                logger.info(f"PPIO client initialized for {client_key} with model: {config.model_name}")
                
            except ValueError as e:
                logger.warning(f"PPIO client not configured for {client_key}: {e}")
                raise ConfigurationError(f"PPIO client not configured: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to initialize PPIO client for {client_key}: {e}")
                raise ConfigurationError(f"PPIO client initialization failed: {str(e)}")
        
        return cls._ppio_clients[client_key]
    
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
def get_ppio_client(agent_role: Optional[str] = None) -> PPIOModelClient:
    """获取PPIO客户端"""
    return URLAgentServiceFactory.get_ppio_client(agent_role)


def get_ppio_config(agent_role: Optional[str] = None) -> PPIOModelConfig:
    """获取PPIO配置"""
    return url_agent_settings.get_ppio_config(agent_role)


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