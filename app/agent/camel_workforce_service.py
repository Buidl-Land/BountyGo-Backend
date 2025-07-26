"""
CAMEL-AI Workforce Multi-Agent Service
基于CAMEL-AI框架的多Agent协作服务
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import asdict
import json

try:
    # CAMEL-AI imports - 使用官方文档推荐的导入路径
    from camel.agents import ChatAgent
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType, ModelType, RoleType
    from camel.societies import RolePlaying, BabyAGI
    from camel.societies.workforce import Workforce  # 正确的Workforce导入路径
    from camel.messages import BaseMessage
    from camel.tasks import Task
    
    CAMEL_AVAILABLE = True
except ImportError as e:
    CAMEL_AVAILABLE = False
    logging.warning(f"CAMEL-AI not available: {e}. Multi-agent features will be limited.")

from .unified_config import (
    UnifiedConfigManager, AgentRole, WorkflowConfig, 
    get_config_manager, get_agent_config
)
from .models import TaskInfo, WebContent
from .exceptions import ConfigurationError, ModelAPIError

logger = logging.getLogger(__name__)


class CAMELWorkforceService:
    """CAMEL-AI Workforce多Agent协作服务 - 简化版本"""
    
    def __init__(self, config_manager: Optional[UnifiedConfigManager] = None):
        if not CAMEL_AVAILABLE:
            raise ConfigurationError("CAMEL-AI not available. Please install: pip install camel-ai")
        
        self.config_manager = config_manager or get_config_manager()
        self.workforce: Optional[Workforce] = None
        self.role_playing: Optional[RolePlaying] = None
        self.agents: Dict[AgentRole, ChatAgent] = {}
        self.initialized = False
        
    def initialize(self):
        """初始化Workforce和Agents"""
        try:
            logger.info("Initializing CAMEL Workforce...")
            
            # 创建各个Agent
            self._create_agents()
            
            # 创建协作系统
            workflow_config = self.config_manager.get_workflow_config()
            if workflow_config.mode.value == "workforce":
                self._create_workforce()
            elif workflow_config.mode.value == "role_playing":
                self._create_role_playing()
            
            self.initialized = True
            logger.info(f"CAMEL多Agent系统初始化完成，包含 {len(self.agents)} 个Agent")
            
        except Exception as e:
            logger.error(f"Failed to initialize CAMEL Workforce: {e}")
            raise ConfigurationError(f"Workforce initialization failed: {str(e)}")
    
    def _create_agents(self):
        """创建所有Agent实例"""
        for role, agent_config in self.config_manager.get_all_agent_configs().items():
            try:
                # 转换模型配置为CAMEL格式
                model = self._create_camel_model(agent_config)
                
                # 创建Agent
                agent = ChatAgent(
                    model=model,
                    system_message=agent_config.system_message or f"You are a {role.value} specialist.",
                )
                
                self.agents[role] = agent
                logger.info(f"Created {role.value} agent with model {agent_config.model_name}")
                
            except Exception as e:
                logger.error(f"Failed to create {role.value} agent: {e}")
                raise
    
    def _create_camel_model(self, agent_config):
        """将Agent配置转换为CAMEL模型"""
        # 模型平台映射
        platform_mapping = {
            "ppio": ModelPlatformType.OPENAI,  # PPIO兼容OpenAI API
            "openai": ModelPlatformType.OPENAI,
            "anthropic": ModelPlatformType.ANTHROPIC,
            "google": ModelPlatformType.GOOGLE,
        }
        
        platform = platform_mapping.get(agent_config.provider.value, ModelPlatformType.OPENAI)
        
        # 创建模型配置
        model_config = {
            "model": agent_config.model_name,
            "temperature": agent_config.temperature,
            "max_tokens": agent_config.max_tokens,
        }
        
        # 如果是PPIO，需要设置base_url
        if agent_config.provider.value == "ppio":
            model_config["base_url"] = agent_config.base_url
            model_config["api_key"] = agent_config.api_key
        
        return ModelFactory.create(
            model_platform=platform,
            model_type=ModelType.GPT_4O if agent_config.supports_vision else ModelType.GPT_4,
            model_config_dict=model_config
        )
    
    def _create_workforce(self):
        """创建CAMEL Workforce协作"""
        try:
            # 创建Workforce实例
            self.workforce = Workforce("BountyGo Multi-Agent Workforce")
            
            # 添加各个Agent作为工作节点
            for role, agent in self.agents.items():
                description = self._get_agent_description(role)
                self.workforce.add_single_agent_worker(description, worker=agent)
                logger.info(f"Added {role.value} to workforce: {description}")
            
            logger.info("CAMEL Workforce创建成功")
            
        except Exception as e:
            logger.error(f"Failed to create workforce: {e}")
            raise
    
    def _create_role_playing(self):
        """创建CAMEL RolePlaying协作"""
        try:
            # 选择主要的协作Agent
            if AgentRole.COORDINATOR in self.agents and AgentRole.URL_PARSER in self.agents:
                assistant_agent = self.agents[AgentRole.COORDINATOR]
                user_agent = self.agents[AgentRole.URL_PARSER]
                
                self.role_playing = RolePlaying(
                    assistant_role_name="协调者",
                    user_role_name="专家",
                    assistant_agent=assistant_agent,
                    user_agent=user_agent
                )
                
                logger.info("CAMEL RolePlaying协作创建成功")
            else:
                logger.warning("缺少必要的Agent，跳过RolePlaying创建")
            
        except Exception as e:
            logger.error(f"Failed to create role playing: {e}")
            raise
    
    def _get_agent_description(self, role: AgentRole) -> str:
        """获取Agent的描述，用于Workforce"""
        descriptions = {
            AgentRole.URL_PARSER: "An agent specialized in parsing URLs and extracting web content structure",
            AgentRole.IMAGE_ANALYZER: "An agent with vision capabilities for analyzing images and extracting task information",
            AgentRole.CONTENT_EXTRACTOR: "An agent for extracting and processing web content intelligently",
            AgentRole.TASK_CREATOR: "An agent for creating structured task information from extracted content",
            AgentRole.QUALITY_CHECKER: "An agent for verifying and optimizing task information quality",
            AgentRole.COORDINATOR: "An agent for coordinating and managing multi-agent workflows",
            AgentRole.SPECIALIST: "A general specialist agent for various tasks"
        }
        return descriptions.get(role, f"A specialized agent for {role.value} tasks")
    
    async def process_url_with_workforce(
        self, 
        url: str, 
        additional_context: Optional[Dict[str, Any]] = None
    ) -> TaskInfo:
        """使用Workforce处理URL"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # 创建任务描述
            task_description = f"""
            请协作分析以下URL并提取任务信息：
            URL: {url}
            
            请按照以下步骤进行：
            1. URL解析专家：分析URL结构和基本信息
            2. 内容提取专家：提取网页内容
            3. 任务创建专家：创建结构化任务信息
            4. 质量检查专家：验证和优化结果
            
            最终输出标准JSON格式的任务信息。
            """
            
            if additional_context:
                task_description += f"\n额外上下文：{json.dumps(additional_context, ensure_ascii=False)}"
            
            # 使用Workforce、RolePlaying或流水线模式处理任务
            if self.workforce:
                result = await self._run_workforce_task(task_description)
            elif self.role_playing:
                result = await self._run_role_playing_task(task_description)
            else:
                # 流水线模式处理
                result = await self._run_pipeline_task(url, task_description)
            
            # 解析结果为TaskInfo
            return self._parse_task_info(result)
            
        except Exception as e:
            logger.error(f"Workforce URL processing failed: {e}")
            raise ModelAPIError(f"Multi-agent processing failed: {str(e)}")
    
    async def process_image_with_workforce(
        self, 
        image_data: Union[bytes, str], 
        additional_prompt: Optional[str] = None
    ) -> TaskInfo:
        """使用Workforce处理图片"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # 确保有图片分析Agent
            if AgentRole.IMAGE_ANALYZER not in self.agents:
                raise ConfigurationError("Image analyzer agent not configured")
            
            # 创建任务描述
            task_description = f"""
            请协作分析图片并提取任务信息：
            
            请按照以下步骤进行：
            1. 图片分析专家：分析图片内容，识别文字和视觉元素
            2. 任务创建专家：将分析结果转换为结构化任务信息
            3. 质量检查专家：验证和优化结果
            
            {additional_prompt or ''}
            
            最终输出标准JSON格式的任务信息。
            """
            
            # 使用图片分析流水线
            result = await self._run_image_pipeline(image_data, task_description)
            
            # 解析结果为TaskInfo
            return self._parse_task_info(result)
            
        except Exception as e:
            logger.error(f"Workforce image processing failed: {e}")
            raise ModelAPIError(f"Multi-agent image processing failed: {str(e)}")
    
    async def _run_workforce_task(self, task_description: str) -> str:
        """运行Workforce任务"""
        try:
            # 创建任务对象
            task = Task(
                content=task_description,
                id=f"task_{int(asyncio.get_event_loop().time())}"  # 使用时间戳作为ID
            )
            
            # 使用Workforce处理任务
            processed_task = self.workforce.process_task(task)
            
            # 获取结果
            result = processed_task.result if hasattr(processed_task, 'result') else str(processed_task)
            
            return result or "Workforce处理完成，但未获得有效响应"
            
        except Exception as e:
            logger.error(f"Workforce execution failed: {e}")
            raise
    
    async def _run_role_playing_task(self, task_description: str) -> str:
        """运行RolePlaying任务"""
        try:
            # 初始化对话
            _, input_messages = self.role_playing.init_chat(task_description)
            
            # 运行多轮对话协作
            max_turns = 3  # 限制对话轮数
            response_content = ""
            
            for turn in range(max_turns):
                assistant_response, user_response = self.role_playing.step(input_messages)
                
                if assistant_response and assistant_response.msgs:
                    response_content = assistant_response.msgs[0].content
                    break
                
                if user_response and user_response.msgs:
                    input_messages = user_response.msgs
            
            return response_content or "协作处理完成，但未获得有效响应"
            
        except Exception as e:
            logger.error(f"RolePlaying execution failed: {e}")
            raise
    
    async def _run_pipeline_task(self, url: str, task_description: str) -> str:
        """运行流水线任务处理"""
        try:
            results = {}
            
            # 步骤1: URL解析
            if AgentRole.URL_PARSER in self.agents:
                url_agent = self.agents[AgentRole.URL_PARSER]
                url_result = await self._ask_agent(
                    url_agent, 
                    f"请分析URL结构和基本信息：{url}"
                )
                results["url_analysis"] = url_result
            
            # 步骤2: 内容提取 (这里可以集成现有的content extractor)
            if AgentRole.CONTENT_EXTRACTOR in self.agents:
                content_agent = self.agents[AgentRole.CONTENT_EXTRACTOR]
                content_result = await self._ask_agent(
                    content_agent,
                    f"请提取网页内容并分析任务信息。URL分析结果：{results.get('url_analysis', '')}"
                )
                results["content_extraction"] = content_result
            
            # 步骤3: 任务创建
            if AgentRole.TASK_CREATOR in self.agents:
                creator_agent = self.agents[AgentRole.TASK_CREATOR]
                creation_input = f"""
                基于以下信息创建结构化任务信息：
                URL分析：{results.get('url_analysis', '')}
                内容提取：{results.get('content_extraction', '')}
                
                请输出标准JSON格式的任务信息。
                """
                task_result = await self._ask_agent(creator_agent, creation_input)
                results["task_creation"] = task_result
            
            # 步骤4: 质量检查
            if AgentRole.QUALITY_CHECKER in self.agents:
                checker_agent = self.agents[AgentRole.QUALITY_CHECKER]
                final_result = await self._ask_agent(
                    checker_agent,
                    f"请验证和优化以下任务信息：{results.get('task_creation', '')}"
                )
                return final_result
            
            return results.get("task_creation", "")
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            raise
    
    async def _run_image_pipeline(self, image_data: Union[bytes, str], task_description: str) -> str:
        """运行图片分析流水线"""
        try:
            results = {}
            
            # 步骤1: 图片分析
            if AgentRole.IMAGE_ANALYZER in self.agents:
                image_agent = self.agents[AgentRole.IMAGE_ANALYZER]
                # 注意：这里需要处理图片数据传递给CAMEL Agent
                # 实际实现可能需要将图片转换为base64或使用CAMEL的图片处理方式
                image_result = await self._ask_agent(
                    image_agent,
                    f"请分析图片内容并识别任务相关信息。{task_description}"
                )
                results["image_analysis"] = image_result
            
            # 步骤2: 任务创建
            if AgentRole.TASK_CREATOR in self.agents:
                creator_agent = self.agents[AgentRole.TASK_CREATOR]
                task_result = await self._ask_agent(
                    creator_agent,
                    f"基于图片分析结果创建结构化任务信息：{results.get('image_analysis', '')}"
                )
                results["task_creation"] = task_result
            
            # 步骤3: 质量检查
            if AgentRole.QUALITY_CHECKER in self.agents:
                checker_agent = self.agents[AgentRole.QUALITY_CHECKER]
                final_result = await self._ask_agent(
                    checker_agent,
                    f"请验证和优化以下任务信息：{results.get('task_creation', '')}"
                )
                return final_result
            
            return results.get("task_creation", "")
            
        except Exception as e:
            logger.error(f"Image pipeline execution failed: {e}")
            raise
    
    async def _ask_agent(self, agent: ChatAgent, message: str) -> str:
        """向Agent发送消息并获取响应"""
        try:
            # 创建消息
            user_message = BaseMessage.make_user_message(
                role_name="User",
                content=message
            )
            
            # 获取响应
            response = agent.step(user_message)
            
            # 提取内容
            if hasattr(response, 'msgs') and response.msgs:
                return response.msgs[0].content
            elif hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Agent communication failed: {e}")
            raise
    
    def _parse_task_info(self, result: str) -> TaskInfo:
        """解析Agent结果为TaskInfo对象"""
        try:
            # 清理JSON字符串
            cleaned_result = result.strip()
            if cleaned_result.startswith("```json"):
                cleaned_result = cleaned_result[7:]
            if cleaned_result.endswith("```"):
                cleaned_result = cleaned_result[:-3]
            cleaned_result = cleaned_result.strip()
            
            # 解析JSON
            data = json.loads(cleaned_result)
            
            # 创建TaskInfo对象
            return TaskInfo(
                title=data.get("title", ""),
                description=data.get("description", ""),
                reward=data.get("reward"),
                reward_currency=data.get("reward_currency", "USD"),
                deadline=data.get("deadline"),
                tags=data.get("tags", []),
                difficulty_level=data.get("difficulty_level"),
                estimated_hours=data.get("estimated_hours")
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse agent result as JSON: {e}")
            # 创建默认TaskInfo
            return TaskInfo(
                title="解析失败",
                description=result[:500],  # 截取前500字符作为描述
                reward=None,
                reward_currency="USD",
                deadline=None,
                tags=[],
                difficulty_level=None,
                estimated_hours=None
            )
        except Exception as e:
            logger.error(f"Failed to create TaskInfo: {e}")
            raise ModelAPIError(f"Result parsing failed: {str(e)}")
    
    async def get_workforce_status(self) -> Dict[str, Any]:
        """获取多Agent系统状态"""
        return {
            "initialized": self.initialized,
            "framework": self.config.framework,
            "agents_count": len(self.agents),
            "agents": {role.value: f"{config.provider.value}:{config.model_name}" 
                      for role, config in self.config.agents.items()},
            "collaboration_config": {
                "size": self.config.workforce.workforce_size,
                "mode": self.config.workforce.collaboration_mode,
                "communication": self.config.workforce.communication_protocol,
                "workforce_enabled": self.workforce is not None,
                "role_playing_enabled": self.role_playing is not None
            }
        }
    
    async def cleanup(self):
        """清理资源"""
        if self.workforce:
            # CAMEL Workforce cleanup if needed
            self.workforce = None
        
        if self.role_playing:
            # CAMEL RolePlaying cleanup if needed
            self.role_playing = None
        
        self.agents.clear()
        self.initialized = False
        logger.info("CAMEL多Agent系统已清理")


# 便捷函数
def create_camel_workforce_service() -> CAMELWorkforceService:
    """创建CAMEL Workforce服务的便捷函数"""
    return CAMELWorkforceService()


# 环境检查函数
def check_camel_ai_availability() -> bool:
    """检查CAMEL-AI是否可用"""
    return CAMEL_AVAILABLE 