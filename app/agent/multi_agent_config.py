"""
Multi-Agent System Configuration for BountyGo
支持CAMEL-AI框架的多Agent协作配置
"""
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from dataclasses import dataclass
import os


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
    CAMEL_AI = "camel-ai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"


@dataclass
class AgentModelConfig:
    """单个Agent的模型配置"""
    provider: ModelProvider
    model_name: str
    api_key: str
    base_url: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4000
    supports_vision: bool = False
    supports_function_calling: bool = True
    supports_structured_output: bool = True
    
    # CAMEL-AI specific settings
    role_type: Optional[str] = None
    system_message: Optional[str] = None
    tools: Optional[List[str]] = None
    
    # 性能配置
    timeout: int = 60
    max_retries: int = 3
    rate_limit_per_minute: int = 60
    
    def __post_init__(self):
        """配置验证"""
        # 验证API密钥
        if not self.api_key or not self.api_key.strip():
            raise ValueError("API密钥不能为空")
        
        if not self.api_key.startswith('sk_'):
            raise ValueError("API密钥格式无效，应以'sk_'开头")
        
        if len(self.api_key) < 10:
            raise ValueError("API密钥长度过短")
        
        # 验证温度参数
        if not 0 <= self.temperature <= 2:
            raise ValueError("温度参数必须在0-2之间")
        
        # 验证最大token数
        if self.max_tokens <= 0 or self.max_tokens > 32000:
            raise ValueError("最大token数必须在1-32000之间")
        
        # 验证模型名称
        if not self.model_name or not self.model_name.strip():
            raise ValueError("模型名称不能为空")


class WorkforceConfig(BaseModel):
    """CAMEL Workforce配置"""
    workforce_size: int = Field(default=3, description="工作组大小")
    collaboration_mode: str = Field(default="hierarchical", description="协作模式: hierarchical, peer_to_peer, pipeline")
    communication_protocol: str = Field(default="async", description="通信协议: sync, async, hybrid")
    task_distribution: str = Field(default="auto", description="任务分配策略: auto, manual, round_robin")
    consensus_threshold: float = Field(default=0.7, description="共识阈值")
    max_iterations: int = Field(default=5, description="最大迭代次数")


class MultiAgentSystemConfig(BaseModel):
    """多Agent系统总配置"""
    # 系统级配置
    system_name: str = "BountyGo-MultiAgent"
    framework: str = "camel-ai"  # camel-ai, autogen, etc.
    
    # Agent配置映射
    agents: Dict[AgentRole, AgentModelConfig] = Field(default_factory=dict)
    
    # CAMEL Workforce配置
    workforce: WorkforceConfig = Field(default_factory=WorkforceConfig)
    
    # 全局模型设置
    default_provider: ModelProvider = ModelProvider.PPIO
    fallback_provider: ModelProvider = ModelProvider.OPENAI
    
    # 协作设置
    enable_cross_agent_communication: bool = True
    enable_memory_sharing: bool = True
    enable_tool_sharing: bool = True
    
    # 性能监控
    enable_metrics: bool = True
    log_agent_interactions: bool = True
    
    class Config:
        use_enum_values = True


class ModelConfigManager:
    """模型配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "multi_agent_config.yaml"
        self.system_config = MultiAgentSystemConfig()
        self._load_from_env()
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        # 基础配置
        if os.getenv("MULTI_AGENT_FRAMEWORK"):
            self.system_config.framework = os.getenv("MULTI_AGENT_FRAMEWORK")
        
        if os.getenv("DEFAULT_MODEL_PROVIDER"):
            self.system_config.default_provider = ModelProvider(os.getenv("DEFAULT_MODEL_PROVIDER"))
    
    def add_agent_config(self, role: AgentRole, config: AgentModelConfig):
        """添加Agent配置"""
        self.system_config.agents[role] = config
    
    def get_agent_config(self, role: AgentRole) -> Optional[AgentModelConfig]:
        """获取Agent配置"""
        return self.system_config.agents.get(role)
    
    def create_ppio_agent_config(
        self, 
        role: AgentRole,
        model_name: str = "moonshotai/kimi-k2-instruct",
        supports_vision: bool = False,
        system_message: Optional[str] = None
    ) -> AgentModelConfig:
        """创建PPIO模型配置"""
        api_key = os.getenv("PPIO_API_KEY")
        if not api_key:
            raise ValueError("PPIO_API_KEY not found in environment variables")
        
        return AgentModelConfig(
            provider=ModelProvider.PPIO,
            model_name=model_name,
            api_key=api_key,
            base_url=os.getenv("PPIO_BASE_URL", "https://api.ppinfra.com/v3/openai"),
            supports_vision=supports_vision,
            system_message=system_message,
            role_type=role.value
        )
    
    def create_camel_workforce_config(
        self,
        size: int = 3,
        mode: str = "hierarchical"
    ) -> WorkforceConfig:
        """创建CAMEL Workforce配置"""
        return WorkforceConfig(
            workforce_size=size,
            collaboration_mode=mode,
            communication_protocol="async",
            task_distribution="auto"
        )
    
    def get_model_for_task(self, task_type: str) -> AgentModelConfig:
        """根据任务类型获取最适合的模型配置"""
        task_role_mapping = {
            "url_parsing": AgentRole.URL_PARSER,
            "image_analysis": AgentRole.IMAGE_ANALYZER,
            "content_extraction": AgentRole.CONTENT_EXTRACTOR,
            "task_creation": AgentRole.TASK_CREATOR,
            "quality_check": AgentRole.QUALITY_CHECKER
        }
        
        role = task_role_mapping.get(task_type, AgentRole.SPECIALIST)
        config = self.get_agent_config(role)
        
        if not config:
            # 返回默认配置
            return self.create_default_config(role)
        
        return config
    
    def create_default_config(self, role: AgentRole) -> AgentModelConfig:
        """创建默认配置"""
        # 视觉任务使用视觉模型
        if role == AgentRole.IMAGE_ANALYZER:
            return self.create_ppio_agent_config(
                role=role,
                model_name="baidu/ernie-4.5-vl-28b-a3b",
                supports_vision=True,
                system_message="你是专业的图片分析专家，能够准确识别和分析图片内容。"
            )
        
        # URL解析使用语言模型
        elif role == AgentRole.URL_PARSER:
            return self.create_ppio_agent_config(
                role=role,
                model_name="qwen/qwen3-coder-480b-a35b-instruct",
                system_message="你是专业的URL内容解析专家，能够准确提取和分析网页内容。"
            )
        
        # 其他任务使用通用模型
        else:
            return self.create_ppio_agent_config(
                role=role,
                model_name="moonshotai/kimi-k2-instruct",
                system_message=f"你是{role.value}专家，请协助完成相关任务。"
            )


# 预定义配置模板
def create_standard_bountygo_config() -> MultiAgentSystemConfig:
    """创建BountyGo标准多Agent配置"""
    manager = ModelConfigManager()
    
    # URL解析Agent - 使用编程优化模型
    manager.add_agent_config(
        AgentRole.URL_PARSER,
        manager.create_ppio_agent_config(
            role=AgentRole.URL_PARSER,
            model_name="qwen/qwen3-coder-480b-a35b-instruct",
            system_message="你是专业的URL内容解析专家，特别擅长分析Web3和区块链相关的任务和赏金信息。"
        )
    )
    
    # 图片分析Agent - 使用视觉模型
    manager.add_agent_config(
        AgentRole.IMAGE_ANALYZER,
        manager.create_ppio_agent_config(
            role=AgentRole.IMAGE_ANALYZER,
            model_name="baidu/ernie-4.5-vl-28b-a3b",
            supports_vision=True,
            system_message="你是专业的图片内容分析专家，能够从图片中准确识别和提取任务相关信息。"
        )
    )
    
    # 内容提取Agent
    manager.add_agent_config(
        AgentRole.CONTENT_EXTRACTOR,
        manager.create_ppio_agent_config(
            role=AgentRole.CONTENT_EXTRACTOR,
            model_name="moonshotai/kimi-k2-instruct",
            system_message="你是内容提取专家，能够从复杂的网页内容中提取结构化信息。"
        )
    )
    
    # 任务创建Agent
    manager.add_agent_config(
        AgentRole.TASK_CREATOR,
        manager.create_ppio_agent_config(
            role=AgentRole.TASK_CREATOR,
            model_name="deepseek/deepseek-r1-0528",
            system_message="你是任务创建专家，能够将提取的信息转换为标准的任务格式。"
        )
    )
    
    # 质量检查Agent
    manager.add_agent_config(
        AgentRole.QUALITY_CHECKER,
        manager.create_ppio_agent_config(
            role=AgentRole.QUALITY_CHECKER,
            model_name="qwen/qwen3-235b-a22b-instruct-2507",
            system_message="你是质量检查专家，负责验证和优化提取的任务信息的准确性和完整性。"
        )
    )
    
    # 协调器Agent
    manager.add_agent_config(
        AgentRole.COORDINATOR,
        manager.create_ppio_agent_config(
            role=AgentRole.COORDINATOR,
            model_name="moonshotai/kimi-k2-instruct",
            system_message="你是多Agent系统的协调器，负责任务分配、进度监控和结果整合。"
        )
    )
    
    # 配置Workforce
    manager.system_config.workforce = WorkforceConfig(
        workforce_size=5,  # 5个Agent协作
        collaboration_mode="workforce",  # 使用CAMEL Workforce模式
        communication_protocol="async",
        task_distribution="auto",
        consensus_threshold=0.8,
        max_iterations=3
    )
    
    return manager.system_config


# 环境变量配置示例
def get_env_config_example() -> str:
    """返回环境变量配置示例"""
    return """
# Multi-Agent System Configuration
MULTI_AGENT_FRAMEWORK=camel-ai
DEFAULT_MODEL_PROVIDER=ppio

# PPIO Models for different agents
PPIO_API_KEY=your_ppio_api_key_here
PPIO_BASE_URL=https://api.ppinfra.com/v3/openai

# URL Parser Agent
URL_PARSER_MODEL=qwen/qwen3-coder-480b-a35b-instruct
URL_PARSER_TEMPERATURE=0.1

# Image Analyzer Agent
IMAGE_ANALYZER_MODEL=baidu/ernie-4.5-vl-28b-a3b
IMAGE_ANALYZER_TEMPERATURE=0.1

# Content Extractor Agent
CONTENT_EXTRACTOR_MODEL=moonshotai/kimi-k2-instruct
CONTENT_EXTRACTOR_TEMPERATURE=0.1

# Task Creator Agent
TASK_CREATOR_MODEL=deepseek/deepseek-r1-0528
TASK_CREATOR_TEMPERATURE=0.0

# Quality Checker Agent
QUALITY_CHECKER_MODEL=qwen/qwen3-235b-a22b-instruct-2507
QUALITY_CHECKER_TEMPERATURE=0.0

# Workforce Configuration
WORKFORCE_SIZE=5
WORKFORCE_MODE=pipeline
WORKFORCE_COMMUNICATION=async
WORKFORCE_CONSENSUS_THRESHOLD=0.8
""" 