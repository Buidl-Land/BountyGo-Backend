"""
Unified Configuration Manager for Multi-Agent System
统一的多Agent系统配置管理器 - 整合所有配置逻辑
"""
import os
import logging
from typing import Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Agent角色类型"""
    URL_PARSER = "url_parser"
    IMAGE_ANALYZER = "image_analyzer"
    CONTENT_EXTRACTOR = "content_extractor"
    TASK_CREATOR = "task_creator"
    QUALITY_CHECKER = "quality_checker"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"


class ModelProvider(str, Enum):
    """模型提供商"""
    PPIO = "ppio"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"


class WorkflowMode(str, Enum):
    """工作流模式"""
    WORKFORCE = "workforce"
    ROLE_PLAYING = "role_playing"
    PIPELINE = "pipeline"
    SINGLE_AGENT = "single_agent"


@dataclass
class AgentConfig:
    """单个Agent的配置"""
    role: AgentRole
    provider: ModelProvider
    model_name: str
    api_key: str
    base_url: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout: int = 60
    max_retries: int = 3
    supports_vision: bool = False
    supports_function_calling: bool = True
    supports_structured_output: bool = True
    system_message: Optional[str] = None
    
    def __post_init__(self):
        """配置验证"""
        self._validate_api_key()
        self._validate_temperature()
        self._validate_max_tokens()
        self._validate_model_capabilities()
    
    def _validate_api_key(self):
        """验证API密钥"""
        if not self.api_key or not self.api_key.strip():
            raise ValueError(f"API密钥不能为空 (Agent: {self.role.value})")
        
        if self.provider == ModelProvider.PPIO and not self.api_key.startswith('sk_'):
            raise ValueError(f"PPIO API密钥格式无效，应以'sk_'开头 (Agent: {self.role.value})")
        
        if len(self.api_key) < 10:
            raise ValueError(f"API密钥长度过短 (Agent: {self.role.value})")
    
    def _validate_temperature(self):
        """验证温度参数"""
        if not 0 <= self.temperature <= 2:
            raise ValueError(f"温度参数必须在0-2之间 (Agent: {self.role.value})")
    
    def _validate_max_tokens(self):
        """验证最大token数"""
        if self.max_tokens <= 0 or self.max_tokens > 32000:
            raise ValueError(f"最大token数必须在1-32000之间 (Agent: {self.role.value})")
    
    def _validate_model_capabilities(self):
        """验证模型能力"""
        # 检查视觉模型是否用于图片分析
        if self.role == AgentRole.IMAGE_ANALYZER and not self.supports_vision:
            logger.warning(f"图片分析Agent使用非视觉模型: {self.model_name}")
        
        # 检查模型是否支持声明的功能
        if self.provider == ModelProvider.PPIO:
            actual_capabilities = self._get_ppio_model_capabilities()
            if actual_capabilities:
                self.supports_vision = actual_capabilities.get('vision', False)
                self.supports_function_calling = actual_capabilities.get('function_calling', True)
                self.supports_structured_output = actual_capabilities.get('structured_output', True)
    
    def _get_ppio_model_capabilities(self) -> Optional[Dict[str, bool]]:
        """获取PPIO模型的实际能力"""
        # 视觉模型
        vision_models = {
            "thudm/glm-4.1v-9b-thinking",
            "baidu/ernie-4.5-vl-424b-a47b", 
            "qwen/qwen2.5-vl-72b-instruct",
            "baidu/ernie-4.5-vl-28b-a3b"
        }
        
        # 支持函数调用的模型
        function_calling_models = {
            "deepseek/deepseek-v3-0324",
            "qwen/qwen3-coder-480b-a35b-instruct",
            "moonshotai/kimi-k2-instruct",
            "minimaxai/minimax-m1-80k",
            "qwen/qwen3-235b-a22b-instruct-2507",
            "deepseek/deepseek-r1-turbo",
            "deepseek/deepseek-r1-0528",
            "deepseek/deepseek-v3-turbo",
            "baidu/ernie-4.5-vl-424b-a47b",
            "baidu/ernie-4.5-300b-a47b-paddle",
            "qwen/qwen2.5-72b-instruct",
            "qwen/qwen2.5-32b-instruct",
            "thudm/glm-4-32b-0414",
            "qwen/qwen2.5-7b-instruct",
            "baidu/ernie-4.5-0.3b",
            "baidu/ernie-4.5-21B-a3b",
            "baidu/ernie-4.5-vl-28b-a3b"
        }
        
        # 支持结构化输出的模型
        structured_output_models = {
            "qwen/qwen3-coder-480b-a35b-instruct",
            "moonshotai/kimi-k2-instruct",
            "qwen/qwen3-235b-a22b-instruct-2507",
            "deepseek/deepseek-r1-0528",
            "qwen/qwen2.5-72b-instruct",
            "qwen/qwen2.5-32b-instruct",
            "thudm/glm-4-32b-0414",
            "qwen/qwen2.5-7b-instruct",
            "baidu/ernie-4.5-vl-28b-a3b"
        }
        
        return {
            'vision': self.model_name in vision_models,
            'function_calling': self.model_name in function_calling_models,
            'structured_output': self.model_name in structured_output_models
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentConfig':
        """从字典创建配置"""
        return cls(**data)


@dataclass
class WorkflowConfig:
    """工作流配置"""
    mode: WorkflowMode = WorkflowMode.PIPELINE
    workforce_size: int = 5
    max_iterations: int = 3
    consensus_threshold: float = 0.8
    communication_protocol: str = "async"
    task_distribution: str = "auto"
    enable_cross_agent_communication: bool = True
    enable_memory_sharing: bool = True
    enable_tool_sharing: bool = True


@dataclass
class SystemConfig:
    """系统级配置"""
    framework: str = "camel-ai"
    default_provider: ModelProvider = ModelProvider.PPIO
    fallback_provider: ModelProvider = ModelProvider.OPENAI
    max_concurrent_agents: int = 5
    timeout_seconds: int = 60
    retry_attempts: int = 3
    enable_caching: bool = True
    enable_metrics: bool = True
    log_level: str = "INFO"
    log_agent_interactions: bool = True


class UnifiedConfigManager:
    """统一配置管理器 - 简化版本，直接从环境变量加载"""
    
    def __init__(self):
        self.system_config = SystemConfig()
        self.workflow_config = WorkflowConfig()
        self.agent_configs: Dict[AgentRole, AgentConfig] = {}
        self._initialized = False
        
    def initialize(self) -> None:
        """初始化配置管理器"""
        try:
            # 直接从环境变量加载配置
            self._load_from_env()
            
            # 验证配置
            self._validate_config()
            
            self._initialized = True
            logger.info("统一配置管理器初始化完成")
            
        except Exception as e:
            logger.error(f"配置管理器初始化失败: {e}")
            raise
    
    def _load_from_env(self) -> None:
        """从环境变量加载配置"""
        # 系统配置
        if os.getenv("MULTI_AGENT_FRAMEWORK"):
            self.system_config.framework = os.getenv("MULTI_AGENT_FRAMEWORK")
        
        if os.getenv("DEFAULT_MODEL_PROVIDER"):
            self.system_config.default_provider = ModelProvider(os.getenv("DEFAULT_MODEL_PROVIDER"))
        
        if os.getenv("MAX_CONCURRENT_AGENTS"):
            self.system_config.max_concurrent_agents = int(os.getenv("MAX_CONCURRENT_AGENTS"))
        
        # 工作流配置
        if os.getenv("WORKFORCE_MODE"):
            self.workflow_config.mode = WorkflowMode(os.getenv("WORKFORCE_MODE"))
        
        if os.getenv("WORKFORCE_SIZE"):
            self.workflow_config.workforce_size = int(os.getenv("WORKFORCE_SIZE"))
        
        if os.getenv("WORKFORCE_CONSENSUS_THRESHOLD"):
            self.workflow_config.consensus_threshold = float(os.getenv("WORKFORCE_CONSENSUS_THRESHOLD"))
        
        # Agent配置
        self._load_agent_configs_from_env()
    
    def _load_agent_configs_from_env(self) -> None:
        """从环境变量加载Agent配置"""
        # 基础API配置
        ppio_api_key = os.getenv("PPIO_API_KEY")
        ppio_base_url = os.getenv("PPIO_BASE_URL", "https://api.ppinfra.com/v3/openai")
        
        if not ppio_api_key:
            logger.warning("PPIO_API_KEY未设置，将无法使用PPIO模型")
            return
        
        # Agent角色到环境变量的映射
        agent_env_mapping = {
            AgentRole.URL_PARSER: {
                "model": os.getenv("URL_PARSER_MODEL", "qwen/qwen3-coder-480b-a35b-instruct"),
                "temperature": float(os.getenv("URL_PARSER_TEMPERATURE", "0.1")),
                "system_message": "你是专业的URL内容解析专家，特别擅长分析Web3和区块链相关的任务和赏金信息。"
            },
            AgentRole.IMAGE_ANALYZER: {
                "model": os.getenv("IMAGE_ANALYZER_MODEL", "baidu/ernie-4.5-vl-28b-a3b"),
                "temperature": float(os.getenv("IMAGE_ANALYZER_TEMPERATURE", "0.1")),
                "system_message": "你是专业的图片内容分析专家，能够从图片中准确识别和提取任务相关信息。"
            },
            AgentRole.CONTENT_EXTRACTOR: {
                "model": os.getenv("CONTENT_EXTRACTOR_MODEL", "moonshotai/kimi-k2-instruct"),
                "temperature": float(os.getenv("CONTENT_EXTRACTOR_TEMPERATURE", "0.1")),
                "system_message": "你是内容提取专家，能够从复杂的网页内容中提取结构化信息。"
            },
            AgentRole.TASK_CREATOR: {
                "model": os.getenv("TASK_CREATOR_MODEL", "deepseek/deepseek-r1-0528"),
                "temperature": float(os.getenv("TASK_CREATOR_TEMPERATURE", "0.0")),
                "system_message": "你是任务创建专家，能够将提取的信息转换为标准的任务格式。"
            },
            AgentRole.QUALITY_CHECKER: {
                "model": os.getenv("QUALITY_CHECKER_MODEL", "qwen/qwen3-235b-a22b-instruct-2507"),
                "temperature": float(os.getenv("QUALITY_CHECKER_TEMPERATURE", "0.0")),
                "system_message": "你是质量检查专家，负责验证和优化提取的任务信息的准确性和完整性。"
            },
            AgentRole.COORDINATOR: {
                "model": os.getenv("COORDINATOR_MODEL", "moonshotai/kimi-k2-instruct"),
                "temperature": float(os.getenv("COORDINATOR_TEMPERATURE", "0.2")),
                "system_message": "你是多Agent系统的协调器，负责任务分配、进度监控和结果整合。"
            }
        }
        
        # 创建Agent配置
        for role, config_data in agent_env_mapping.items():
            try:
                agent_config = AgentConfig(
                    role=role,
                    provider=ModelProvider.PPIO,
                    model_name=config_data["model"],
                    api_key=ppio_api_key,
                    base_url=ppio_base_url,
                    temperature=config_data["temperature"],
                    system_message=config_data["system_message"]
                )
                self.agent_configs[role] = agent_config
                logger.info(f"加载Agent配置: {role.value} -> {config_data['model']}")
                
            except Exception as e:
                logger.error(f"加载Agent配置失败 {role.value}: {e}")
    
    def _validate_config(self) -> None:
        """验证配置"""
        # 验证系统配置
        if not self.system_config.framework:
            raise ValueError("系统框架未配置")
        
        # 验证工作流配置
        if self.workflow_config.workforce_size <= 0:
            raise ValueError("工作组大小必须大于0")
        
        if not 0 <= self.workflow_config.consensus_threshold <= 1:
            raise ValueError("共识阈值必须在0-1之间")
        
        # 验证Agent配置
        for role, config in self.agent_configs.items():
            try:
                # AgentConfig的__post_init__会自动验证
                pass
            except Exception as e:
                raise ValueError(f"Agent配置验证失败 {role.value}: {e}")
        
        logger.info("配置验证通过")
    
    def get_agent_config(self, role: AgentRole) -> Optional[AgentConfig]:
        """获取Agent配置"""
        return self.agent_configs.get(role)
    
    def set_agent_config(self, role: AgentRole, config: AgentConfig) -> None:
        """设置Agent配置"""
        self.agent_configs[role] = config
        logger.info(f"更新Agent配置: {role.value}")
    
    def get_system_config(self) -> SystemConfig:
        """获取系统配置"""
        return self.system_config
    
    def get_workflow_config(self) -> WorkflowConfig:
        """获取工作流配置"""
        return self.workflow_config
    
    def get_all_agent_configs(self) -> Dict[AgentRole, AgentConfig]:
        """获取所有Agent配置"""
        return self.agent_configs.copy()
    
    def reload_config(self) -> None:
        """重新加载配置"""
        logger.info("重新加载配置...")
        self._load_from_env()
        self._validate_config()
        logger.info("配置重新加载完成")
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            "system": {
                "framework": self.system_config.framework,
                "default_provider": self.system_config.default_provider.value,
                "max_concurrent_agents": self.system_config.max_concurrent_agents
            },
            "workflow": {
                "mode": self.workflow_config.mode.value,
                "workforce_size": self.workflow_config.workforce_size,
                "consensus_threshold": self.workflow_config.consensus_threshold
            },
            "agents": {
                role.value: {
                    "model": config.model_name,
                    "provider": config.provider.value,
                    "supports_vision": config.supports_vision
                }
                for role, config in self.agent_configs.items()
            },
            "initialized": self._initialized
        }


# 全局配置管理器实例
_config_manager: Optional[UnifiedConfigManager] = None


def get_config_manager() -> UnifiedConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = UnifiedConfigManager()
        _config_manager.initialize()
    
    return _config_manager


def reset_config_manager() -> None:
    """重置全局配置管理器实例（主要用于测试）"""
    global _config_manager
    _config_manager = None


def reset_config_manager() -> None:
    """重置全局配置管理器实例（主要用于测试）"""
    global _config_manager
    _config_manager = None


# 便捷函数
def get_agent_config(role: AgentRole) -> Optional[AgentConfig]:
    """获取Agent配置的便捷函数"""
    config_manager = get_config_manager()
    return config_manager.get_agent_config(role)


def get_system_config() -> SystemConfig:
    """获取系统配置的便捷函数"""
    config_manager = get_config_manager()
    return config_manager.get_system_config()


def get_workflow_config() -> WorkflowConfig:
    """获取工作流配置的便捷函数"""
    config_manager = get_config_manager()
    return config_manager.get_workflow_config()