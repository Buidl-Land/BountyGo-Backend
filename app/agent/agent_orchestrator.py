"""
Agent Orchestrator for Multi-Agent System
Agent编排器 - 管理和编排多个agent的协作
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from .unified_config import get_config_manager, AgentRole, AgentConfig
from .url_parsing_agent import URLParsingAgent
from .image_parsing_agent import ImageParsingAgent
from .models import TaskInfo, WebContent
from .content_extractor import ContentExtractor
from .playwright_extractor import PlaywrightContentExtractor
from .preference_manager import UserPreferences
from .exceptions import ConfigurationError, ModelAPIError
from .concurrent_processor import get_concurrent_processor, TaskPriority
from ..core.performance import get_cache_manager, cache_result

logger = logging.getLogger(__name__)


class WorkflowType(str, Enum):
    """工作流类型"""
    URL_PROCESSING = "url_processing"
    IMAGE_PROCESSING = "image_processing"
    TEXT_PROCESSING = "text_processing"
    MIXED_PROCESSING = "mixed_processing"


@dataclass
class AgentResult:
    """Agent执行结果"""
    agent_role: AgentRole
    success: bool
    data: Any
    confidence: float
    processing_time: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WorkflowResult:
    """工作流执行结果"""
    success: bool
    task_info: Optional[TaskInfo] = None
    agent_results: Dict[AgentRole, AgentResult] = None
    processing_time: float = 0.0
    quality_score: float = 0.0
    error_message: Optional[str] = None
    workflow_type: Optional[WorkflowType] = None
    
    def __post_init__(self):
        if self.agent_results is None:
            self.agent_results = {}


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self, orchestrator: 'AgentOrchestrator'):
        self.orchestrator = orchestrator
    
    @cache_result(key_prefix="web_content", ttl_seconds=3600)
    async def _get_cached_content(self, url: str, content_extractor) -> Any:
        """获取缓存的网页内容（支持fallback）"""
        try:
            return await content_extractor.extract_content(url)
        except Exception as e:
            logger.warning(f"HTTP内容提取失败，尝试Playwright fallback: {e}")
            # 使用Playwright作为fallback
            if self.orchestrator.playwright_extractor:
                return await self.orchestrator.playwright_extractor.extract_content(url)
            else:
                raise
    
    async def execute_url_workflow(
        self, 
        url: str, 
        preferences: UserPreferences,
        create_task: bool = True
    ) -> WorkflowResult:
        """执行URL处理工作流"""
        start_time = time.time()
        agent_results = {}
        
        try:
            logger.info(f"开始URL处理工作流: {url}")
            
            # 步骤1: 内容提取（使用缓存）
            content_extractor = self.orchestrator.get_content_extractor()
            web_content = await self._get_cached_content(url, content_extractor)
            
            content_result = AgentResult(
                agent_role=AgentRole.CONTENT_EXTRACTOR,
                success=True,
                data=web_content,
                confidence=0.9,
                processing_time=time.time() - start_time
            )
            agent_results[AgentRole.CONTENT_EXTRACTOR] = content_result
            
            # 步骤2: URL解析Agent分析
            url_agent = self.orchestrator.get_agent(AgentRole.URL_PARSER)
            if not url_agent:
                raise ConfigurationError("URL解析Agent未配置")
            
            analysis_start = time.time()
            task_info = await url_agent.analyze_content(web_content)
            analysis_time = time.time() - analysis_start
            
            url_result = AgentResult(
                agent_role=AgentRole.URL_PARSER,
                success=True,
                data=task_info,
                confidence=0.8,
                processing_time=analysis_time
            )
            agent_results[AgentRole.URL_PARSER] = url_result
            
            # 步骤3: 质量检查（如果配置了质量检查Agent）
            quality_agent = self.orchestrator.get_agent(AgentRole.QUALITY_CHECKER)
            if quality_agent and preferences.quality_threshold > 0.5:
                quality_result = await self._run_quality_check(task_info, preferences)
                agent_results[AgentRole.QUALITY_CHECKER] = quality_result
                
                if not quality_result.success:
                    logger.warning("质量检查未通过，使用原始结果")
            
            # 计算整体质量分数
            quality_score = self._calculate_quality_score(agent_results, preferences)
            
            processing_time = time.time() - start_time
            logger.info(f"URL工作流完成，耗时 {processing_time:.2f}s，质量分数 {quality_score:.2f}")
            
            return WorkflowResult(
                success=True,
                task_info=task_info,
                agent_results=agent_results,
                processing_time=processing_time,
                quality_score=quality_score,
                workflow_type=WorkflowType.URL_PROCESSING
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"URL工作流执行失败: {e}")
            
            return WorkflowResult(
                success=False,
                agent_results=agent_results,
                processing_time=processing_time,
                error_message=str(e),
                workflow_type=WorkflowType.URL_PROCESSING
            )
    
    async def execute_image_workflow(
        self, 
        image_data: Union[bytes, str], 
        preferences: UserPreferences,
        create_task: bool = True
    ) -> WorkflowResult:
        """执行图片处理工作流"""
        start_time = time.time()
        agent_results = {}
        
        try:
            logger.info("开始图片处理工作流")
            
            # 步骤1: 图片分析Agent处理
            image_agent = self.orchestrator.get_agent(AgentRole.IMAGE_ANALYZER)
            if not image_agent:
                raise ConfigurationError("图片分析Agent未配置")
            
            # 确保Agent已初始化
            if not hasattr(image_agent, 'client') or image_agent.client is None:
                await image_agent.initialize()
            
            analysis_start = time.time()
            task_info = await image_agent.analyze_image(image_data)
            analysis_time = time.time() - analysis_start
            
            image_result = AgentResult(
                agent_role=AgentRole.IMAGE_ANALYZER,
                success=True,
                data=task_info,
                confidence=0.7,  # 图片分析置信度通常较低
                processing_time=analysis_time
            )
            agent_results[AgentRole.IMAGE_ANALYZER] = image_result
            
            # 步骤2: 质量检查
            quality_agent = self.orchestrator.get_agent(AgentRole.QUALITY_CHECKER)
            if quality_agent and preferences.quality_threshold > 0.5:
                quality_result = await self._run_quality_check(task_info, preferences)
                agent_results[AgentRole.QUALITY_CHECKER] = quality_result
            
            # 计算质量分数
            quality_score = self._calculate_quality_score(agent_results, preferences)
            
            processing_time = time.time() - start_time
            logger.info(f"图片工作流完成，耗时 {processing_time:.2f}s，质量分数 {quality_score:.2f}")
            
            return WorkflowResult(
                success=True,
                task_info=task_info,
                agent_results=agent_results,
                processing_time=processing_time,
                quality_score=quality_score,
                workflow_type=WorkflowType.IMAGE_PROCESSING
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"图片工作流执行失败: {e}")
            
            return WorkflowResult(
                success=False,
                agent_results=agent_results,
                processing_time=processing_time,
                error_message=str(e),
                workflow_type=WorkflowType.IMAGE_PROCESSING
            )
    
    async def execute_text_workflow(
        self, 
        text_content: str, 
        preferences: UserPreferences,
        create_task: bool = True
    ) -> WorkflowResult:
        """执行文本处理工作流"""
        start_time = time.time()
        agent_results = {}
        
        try:
            logger.info("开始文本处理工作流")
            
            # 创建虚拟的WebContent对象
            web_content = WebContent(
                url="",
                title="Direct Text Input",
                content=text_content,
                meta_description=None,
                extracted_at=datetime.utcnow()
            )
            
            # 使用URL解析Agent处理文本内容
            url_agent = self.orchestrator.get_agent(AgentRole.URL_PARSER)
            if not url_agent:
                raise ConfigurationError("URL解析Agent未配置")
            
            analysis_start = time.time()
            task_info = await url_agent.analyze_content(web_content)
            analysis_time = time.time() - analysis_start
            
            text_result = AgentResult(
                agent_role=AgentRole.URL_PARSER,
                success=True,
                data=task_info,
                confidence=0.6,  # 纯文本分析置信度中等
                processing_time=analysis_time
            )
            agent_results[AgentRole.URL_PARSER] = text_result
            
            # 质量检查
            quality_agent = self.orchestrator.get_agent(AgentRole.QUALITY_CHECKER)
            if quality_agent and preferences.quality_threshold > 0.5:
                quality_result = await self._run_quality_check(task_info, preferences)
                agent_results[AgentRole.QUALITY_CHECKER] = quality_result
            
            quality_score = self._calculate_quality_score(agent_results, preferences)
            
            processing_time = time.time() - start_time
            logger.info(f"文本工作流完成，耗时 {processing_time:.2f}s，质量分数 {quality_score:.2f}")
            
            return WorkflowResult(
                success=True,
                task_info=task_info,
                agent_results=agent_results,
                processing_time=processing_time,
                quality_score=quality_score,
                workflow_type=WorkflowType.TEXT_PROCESSING
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"文本工作流执行失败: {e}")
            
            return WorkflowResult(
                success=False,
                agent_results=agent_results,
                processing_time=processing_time,
                error_message=str(e),
                workflow_type=WorkflowType.TEXT_PROCESSING
            )
    
    async def execute_mixed_workflow(
        self, 
        mixed_data: Dict[str, Any], 
        preferences: UserPreferences,
        create_task: bool = True
    ) -> WorkflowResult:
        """执行混合内容处理工作流"""
        start_time = time.time()
        agent_results = {}
        
        try:
            logger.info("开始混合内容处理工作流")
            
            # 提取混合数据
            urls = mixed_data.get('urls', [])
            image_data = mixed_data.get('image_data')
            text_content = mixed_data.get('text', '')
            
            task_infos = []
            
            # 处理URL
            if urls:
                for url in urls[:3]:  # 限制处理前3个URL
                    try:
                        url_result = await self.execute_url_workflow(url, preferences, False)
                        if url_result.success:
                            task_infos.append(url_result.task_info)
                            agent_results[f"url_{len(agent_results)}"] = url_result.agent_results.get(AgentRole.URL_PARSER)
                    except Exception as e:
                        logger.warning(f"处理URL失败 {url}: {e}")
            
            # 处理图片
            if image_data:
                try:
                    image_result = await self.execute_image_workflow(image_data, preferences, False)
                    if image_result.success:
                        task_infos.append(image_result.task_info)
                        agent_results[AgentRole.IMAGE_ANALYZER] = image_result.agent_results.get(AgentRole.IMAGE_ANALYZER)
                except Exception as e:
                    logger.warning(f"处理图片失败: {e}")
            
            # 处理文本
            if text_content:
                try:
                    text_result = await self.execute_text_workflow(text_content, preferences, False)
                    if text_result.success:
                        task_infos.append(text_result.task_info)
                        agent_results[f"text_{len(agent_results)}"] = text_result.agent_results.get(AgentRole.URL_PARSER)
                except Exception as e:
                    logger.warning(f"处理文本失败: {e}")
            
            # 合并结果
            if task_infos:
                merged_task_info = await self._merge_task_infos(task_infos)
                quality_score = self._calculate_quality_score(agent_results, preferences)
                
                processing_time = time.time() - start_time
                logger.info(f"混合工作流完成，耗时 {processing_time:.2f}s，质量分数 {quality_score:.2f}")
                
                return WorkflowResult(
                    success=True,
                    task_info=merged_task_info,
                    agent_results=agent_results,
                    processing_time=processing_time,
                    quality_score=quality_score,
                    workflow_type=WorkflowType.MIXED_PROCESSING
                )
            else:
                raise Exception("所有内容处理都失败了")
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"混合工作流执行失败: {e}")
            
            return WorkflowResult(
                success=False,
                agent_results=agent_results,
                processing_time=processing_time,
                error_message=str(e),
                workflow_type=WorkflowType.MIXED_PROCESSING
            )
    
    async def _run_quality_check(self, task_info: TaskInfo, preferences: UserPreferences) -> AgentResult:
        """运行质量检查"""
        start_time = time.time()
        
        try:
            # 简化的质量检查逻辑
            quality_score = 0.0
            issues = []
            
            # 检查必需字段
            if not task_info.title or len(task_info.title.strip()) < 5:
                issues.append("标题过短或缺失")
            else:
                quality_score += 0.3
            
            if not task_info.description or len(task_info.description.strip()) < 20:
                issues.append("描述过短或缺失")
            else:
                quality_score += 0.3
            
            # 检查奖励信息
            if task_info.reward and task_info.reward > 0:
                quality_score += 0.2
            
            # 检查标签
            if task_info.tags and len(task_info.tags) > 0:
                quality_score += 0.1
            
            # 检查截止日期
            if task_info.deadline:
                quality_score += 0.1
            
            success = quality_score >= preferences.quality_threshold
            
            return AgentResult(
                agent_role=AgentRole.QUALITY_CHECKER,
                success=success,
                data={"quality_score": quality_score, "issues": issues},
                confidence=quality_score,
                processing_time=time.time() - start_time,
                metadata={"threshold": preferences.quality_threshold}
            )
            
        except Exception as e:
            return AgentResult(
                agent_role=AgentRole.QUALITY_CHECKER,
                success=False,
                data=None,
                confidence=0.0,
                processing_time=time.time() - start_time,
                error_message=str(e)
            )
    
    def _calculate_quality_score(self, agent_results: Dict[str, AgentResult], preferences: UserPreferences) -> float:
        """计算整体质量分数"""
        if not agent_results:
            return 0.0
        
        total_confidence = 0.0
        total_weight = 0.0
        
        for result in agent_results.values():
            if isinstance(result, AgentResult) and result.success:
                weight = 1.0
                # 质量检查Agent的权重更高
                if result.agent_role == AgentRole.QUALITY_CHECKER:
                    weight = 2.0
                
                total_confidence += result.confidence * weight
                total_weight += weight
        
        return total_confidence / total_weight if total_weight > 0 else 0.0
    
    async def _merge_task_infos(self, task_infos: List[TaskInfo]) -> TaskInfo:
        """合并多个TaskInfo"""
        if not task_infos:
            raise ValueError("没有TaskInfo可以合并")
        
        if len(task_infos) == 1:
            return task_infos[0]
        
        # 选择最完整的TaskInfo作为基础
        base_task = max(task_infos, key=lambda t: len(t.description or '') + len(t.tags or []))
        
        # 合并其他信息
        all_tags = set(base_task.tags or [])
        for task in task_infos:
            if task.tags:
                all_tags.update(task.tags)
        
        # 选择最高的奖励
        max_reward = base_task.reward
        reward_currency = base_task.reward_currency
        
        for task in task_infos:
            if task.reward and (not max_reward or task.reward > max_reward):
                max_reward = task.reward
                reward_currency = task.reward_currency
        
        # 选择最早的截止日期
        earliest_deadline = base_task.deadline
        for task in task_infos:
            if task.deadline and (not earliest_deadline or task.deadline < earliest_deadline):
                earliest_deadline = task.deadline
        
        # 创建合并后的TaskInfo
        merged_task = TaskInfo(
            title=base_task.title,
            description=base_task.description,
            reward=max_reward,
            reward_currency=reward_currency,
            deadline=earliest_deadline,
            tags=list(all_tags),
            difficulty_level=base_task.difficulty_level,
            estimated_hours=base_task.estimated_hours
        )
        
        return merged_task


class AgentOrchestrator:
    """Agent编排器"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.agents: Dict[AgentRole, Any] = {}
        self.workflow_engine = WorkflowEngine(self)
        self.content_extractor: Optional[ContentExtractor] = None
        self.playwright_extractor: Optional[PlaywrightContentExtractor] = None
        self.cache_manager = get_cache_manager()
        self.concurrent_processor = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化编排器"""
        try:
            # 初始化内容提取器（使用真实浏览器User-Agent）
            self.content_extractor = ContentExtractor(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            # 初始化Playwright提取器作为fallback
            self.playwright_extractor = PlaywrightContentExtractor()
            
            # 初始化并发处理器
            self.concurrent_processor = await get_concurrent_processor()
            
            # 初始化各个Agent
            await self._initialize_agents()
            
            self._initialized = True
            logger.info(f"Agent编排器初始化完成，包含 {len(self.agents)} 个Agent")
            
        except Exception as e:
            logger.error(f"Agent编排器初始化失败: {e}")
            raise ConfigurationError(f"Agent orchestrator initialization failed: {str(e)}")
    
    async def _initialize_agents(self) -> None:
        """初始化所有Agent"""
        agent_configs = self.config_manager.get_all_agent_configs()
        logger.info(f"开始初始化Agents，配置数量: {len(agent_configs)}")
        
        for role, config in agent_configs.items():
            try:
                logger.info(f"正在创建Agent: {role.value}")
                agent = await self._create_agent(role, config)
                if agent:
                    self.agents[role] = agent
                    logger.info(f"✅ 初始化Agent成功: {role.value}")
                else:
                    logger.warning(f"❌ Agent创建返回None: {role.value}")
            except Exception as e:
                logger.error(f"❌ 初始化Agent失败 {role.value}: {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    async def _create_agent(self, role: AgentRole, config: AgentConfig) -> Optional[Any]:
        """创建Agent实例"""
        try:
            # 转换配置格式
            from .config import PPIOModelConfig
            
            ppio_config = PPIOModelConfig(
                api_key=config.api_key,
                base_url=config.base_url or "https://api.ppinfra.com/v3/openai",
                model_name=config.model_name,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                timeout=config.timeout,
                max_retries=config.max_retries
            )
            
            if role == AgentRole.URL_PARSER:
                logger.info(f"创建URLParsingAgent，配置: {ppio_config.model_name}")
                agent = URLParsingAgent(ppio_config)
                logger.info(f"URLParsingAgent创建成功")
                return agent
            elif role == AgentRole.IMAGE_ANALYZER:
                agent = ImageParsingAgent(ppio_config)
                # 图片分析Agent需要异步初始化
                await agent.initialize()
                return agent
            else:
                # 其他Agent类型暂时返回None
                logger.warning(f"Agent类型 {role.value} 暂未实现")
                return None
                
        except Exception as e:
            logger.error(f"创建Agent失败 {role.value}: {e}")
            return None
    
    def get_agent(self, role: AgentRole) -> Optional[Any]:
        """获取Agent实例"""
        return self.agents.get(role)
    
    def get_content_extractor(self) -> ContentExtractor:
        """获取内容提取器"""
        if not self.content_extractor:
            self.content_extractor = ContentExtractor(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
        return self.content_extractor
    
    async def execute_workflow(
        self,
        workflow_type: WorkflowType,
        input_data: Any,
        preferences: UserPreferences,
        create_task: bool = True
    ) -> WorkflowResult:
        """执行指定的工作流"""
        if not self._initialized:
            raise ConfigurationError("Agent编排器未初始化")
        
        try:
            if workflow_type == WorkflowType.URL_PROCESSING:
                return await self.workflow_engine.execute_url_workflow(input_data, preferences, create_task)
            elif workflow_type == WorkflowType.IMAGE_PROCESSING:
                return await self.workflow_engine.execute_image_workflow(input_data, preferences, create_task)
            elif workflow_type == WorkflowType.TEXT_PROCESSING:
                return await self.workflow_engine.execute_text_workflow(input_data, preferences, create_task)
            elif workflow_type == WorkflowType.MIXED_PROCESSING:
                return await self.workflow_engine.execute_mixed_workflow(input_data, preferences, create_task)
            else:
                raise ValueError(f"不支持的工作流类型: {workflow_type}")
                
        except Exception as e:
            logger.error(f"工作流执行失败 {workflow_type}: {e}")
            return WorkflowResult(
                success=False,
                error_message=str(e),
                workflow_type=workflow_type
            )
    
    async def get_status(self) -> Dict[str, Any]:
        """获取编排器状态"""
        return {
            "initialized": self._initialized,
            "agent_count": len(self.agents),
            "available_agents": [role.value for role in self.agents.keys()],
            "content_extractor_available": self.content_extractor is not None
        }
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


# 全局编排器实例
_agent_orchestrator: Optional[AgentOrchestrator] = None


async def get_agent_orchestrator() -> AgentOrchestrator:
    """获取全局Agent编排器实例"""
    global _agent_orchestrator
    
    if _agent_orchestrator is None:
        _agent_orchestrator = AgentOrchestrator()
        await _agent_orchestrator.initialize()
    
    return _agent_orchestrator