"""
Main URL agent service implementation.
"""
import asyncio
import logging
import time
import traceback
from typing import Optional, Dict, Any, Union
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.client import PPIOModelClient
from app.agent.factory import get_ppio_client
from app.agent.content_extractor import ContentExtractor
from app.agent.url_parsing_agent import URLParsingAgent
from app.agent.image_parsing_agent import ImageParsingAgent
from app.agent.task_creator import TaskCreator
from app.agent.models import TaskProcessResult, TaskInfo, WebContent
from app.agent.exceptions import URLAgentError, ConfigurationError, URLValidationError, ContentExtractionError, ModelAPIError, TaskCreationError
from app.agent.config import url_agent_settings
from app.agent.factory import get_ppio_config

logger = logging.getLogger(__name__)

# 性能监控指标
class PerformanceMetrics:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.avg_processing_time = 0.0
        self.content_extraction_time = 0.0
        self.ai_analysis_time = 0.0
        self.task_creation_time = 0.0
        self.error_counts = {}
    
    def record_request(self, success: bool, processing_time: float, error_type: str = None):
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error_type:
                self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # 更新平均处理时间
        self.avg_processing_time = (
            (self.avg_processing_time * (self.total_requests - 1) + processing_time) / 
            self.total_requests
        )
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / max(self.total_requests, 1),
            "avg_processing_time": self.avg_processing_time,
            "content_extraction_time": self.content_extraction_time,
            "ai_analysis_time": self.ai_analysis_time,
            "task_creation_time": self.task_creation_time,
            "error_counts": self.error_counts
        }


class URLAgentService:
    """主要的URL代理服务类"""
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db_session = db_session
        self.settings = url_agent_settings
        
        # 延迟初始化组件
        self._ppio_client: Optional[PPIOModelClient] = None
        self._content_extractor: Optional[ContentExtractor] = None
        self._url_parsing_agent: Optional[URLParsingAgent] = None
        self._image_parsing_agent: Optional[ImageParsingAgent] = None
        self._task_creator: Optional[TaskCreator] = None
        
        # 性能监控
        self.metrics = PerformanceMetrics()
        
        # 重试配置
        self.max_retries = 3
        self.retry_delay = 1.0  # 秒
        
        # 错误恢复配置
        self.enable_fallback = True
    
    @property
    def ppio_client(self) -> PPIOModelClient:
        """获取PPIO客户端（默认）"""
        if self._ppio_client is None:
            self._ppio_client = get_ppio_client()
        return self._ppio_client
    
    def get_specialized_client(self, agent_role: str) -> PPIOModelClient:
        """获取专门角色的PPIO客户端"""
        return get_ppio_client(agent_role)
    
    @property
    def content_extractor(self) -> ContentExtractor:
        """获取智能内容提取器"""
        if self._content_extractor is None:
            self._content_extractor = ContentExtractor(
                timeout=self.settings.content_extraction_timeout,
                max_content_length=self.settings.max_content_length
            )
        return self._content_extractor
    
    @property
    def url_parsing_agent(self) -> URLParsingAgent:
        """获取URL解析代理"""
        if self._url_parsing_agent is None:
            # 使用专门的URL解析模型
            ppio_config = url_agent_settings.get_ppio_config("url_parser")
            self._url_parsing_agent = URLParsingAgent(ppio_config)
        return self._url_parsing_agent
    
    @property
    def image_parsing_agent(self) -> ImageParsingAgent:
        """获取图片解析代理"""
        if self._image_parsing_agent is None:
            # 使用专门的图片分析模型
            ppio_config = url_agent_settings.get_ppio_config("image_analyzer")
            self._image_parsing_agent = ImageParsingAgent(ppio_config)
        return self._image_parsing_agent
    
    @property
    def task_creator(self) -> TaskCreator:
        """获取任务创建器"""
        if self._task_creator is None:
            if not self.db_session:
                raise ConfigurationError("Database session required for task creation")
            self._task_creator = TaskCreator(self.db_session)
        return self._task_creator
    
    async def process_url(self, url: str, user_id: int, auto_create: bool = False) -> TaskProcessResult:
        """
        处理URL并可选择性创建任务
        
        Args:
            url: 要处理的URL
            user_id: 用户ID
            auto_create: 是否自动创建任务
            
        Returns:
            TaskProcessResult: 处理结果
        """
        start_time = time.time()
        request_id = f"req_{int(time.time() * 1000)}"
        
        logger.info(f"[{request_id}] Processing URL: {url} for user: {user_id}, auto_create: {auto_create}")
        
        try:
            # 1. 提取网页内容（带重试）
            content_start = time.time()
            logger.info(f"[{request_id}] Step 1: Extracting web content")
            web_content = await self._extract_content_with_retry(url, request_id)
            content_time = time.time() - content_start
            self.metrics.content_extraction_time = content_time
            logger.info(f"[{request_id}] Content extracted successfully: {web_content.title} (took {content_time:.2f}s)")
            
            # 2. AI分析内容（带重试）
            analysis_start = time.time()
            logger.info(f"[{request_id}] Step 2: Analyzing content with AI")
            task_info = await self._analyze_content_with_retry(web_content, request_id)
            analysis_time = time.time() - analysis_start
            self.metrics.ai_analysis_time = analysis_time
            logger.info(f"[{request_id}] Task info extracted: {task_info.title} (took {analysis_time:.2f}s)")
            
            # 3. 创建任务（如果auto_create=True）
            task_id = None
            if auto_create:
                creation_start = time.time()
                logger.info(f"[{request_id}] Step 3: Creating task")
                task = await self._create_task_with_retry(task_info, user_id, url, request_id)
                task_id = task.id
                creation_time = time.time() - creation_start
                self.metrics.task_creation_time = creation_time
                logger.info(f"[{request_id}] Task created successfully with ID: {task_id} (took {creation_time:.2f}s)")
            else:
                logger.info(f"[{request_id}] Step 3: Skipping task creation (auto_create=False)")
            
            processing_time = time.time() - start_time
            self.metrics.record_request(True, processing_time)
            
            logger.info(f"[{request_id}] Processing completed successfully in {processing_time:.2f}s")
            
            return TaskProcessResult(
                success=True,
                task_id=task_id,
                extracted_info=task_info,
                error_message=None,
                processing_time=processing_time
            )
            
        except URLValidationError as e:
            processing_time = time.time() - start_time
            self.metrics.record_request(False, processing_time, "URLValidationError")
            logger.error(f"[{request_id}] URL validation failed for {url}: {e}")
            
            return TaskProcessResult(
                success=False,
                task_id=None,
                extracted_info=None,
                error_message=f"URL验证失败: {str(e)}",
                processing_time=processing_time
            )
            
        except ContentExtractionError as e:
            processing_time = time.time() - start_time
            self.metrics.record_request(False, processing_time, "ContentExtractionError")
            logger.error(f"[{request_id}] Content extraction failed for {url}: {e}")
            
            return TaskProcessResult(
                success=False,
                task_id=None,
                extracted_info=None,
                error_message=f"内容提取失败: {str(e)}",
                processing_time=processing_time
            )
            
        except ModelAPIError as e:
            processing_time = time.time() - start_time
            self.metrics.record_request(False, processing_time, "ModelAPIError")
            logger.error(f"[{request_id}] AI analysis failed for {url}: {e}")
            
            return TaskProcessResult(
                success=False,
                task_id=None,
                extracted_info=None,
                error_message=f"AI分析失败: {str(e)}",
                processing_time=processing_time
            )
            
        except TaskCreationError as e:
            processing_time = time.time() - start_time
            self.metrics.record_request(False, processing_time, "TaskCreationError")
            logger.error(f"[{request_id}] Task creation failed for {url}: {e}")
            
            return TaskProcessResult(
                success=False,
                task_id=None,
                extracted_info=None,
                error_message=f"任务创建失败: {str(e)}",
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_type = type(e).__name__
            self.metrics.record_request(False, processing_time, error_type)
            
            logger.error(f"[{request_id}] Unexpected error processing URL {url}: {e}")
            logger.error(f"[{request_id}] Error traceback: {traceback.format_exc()}")
            
            return TaskProcessResult(
                success=False,
                task_id=None,
                extracted_info=None,
                error_message=f"处理失败: {str(e)}",
                processing_time=processing_time
            )
    
    async def _extract_content_with_retry(self, url: str, request_id: str) -> WebContent:
        """带重试的内容提取"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"[{request_id}] Content extraction retry attempt {attempt + 1}/{self.max_retries}")
                    await asyncio.sleep(self.retry_delay * attempt)
                
                return await self.content_extractor.extract_content(url)
                
            except (URLValidationError, ContentExtractionError) as e:
                last_exception = e
                logger.warning(f"[{request_id}] Content extraction attempt {attempt + 1} failed: {e}")
                
                # 对于URL验证错误，不重试
                if isinstance(e, URLValidationError):
                    break
                    
            except Exception as e:
                last_exception = e
                logger.warning(f"[{request_id}] Content extraction attempt {attempt + 1} failed with unexpected error: {e}")
        
        # 所有重试都失败了
        logger.error(f"[{request_id}] Content extraction failed after {self.max_retries} attempts")
        raise last_exception
    
    async def _analyze_content_with_retry(self, web_content: WebContent, request_id: str) -> TaskInfo:
        """带重试的AI内容分析"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"[{request_id}] AI analysis retry attempt {attempt + 1}/{self.max_retries}")
                    await asyncio.sleep(self.retry_delay * attempt)
                
                return await self.url_parsing_agent.analyze_content(web_content)
                
            except ModelAPIError as e:
                last_exception = e
                logger.warning(f"[{request_id}] AI analysis attempt {attempt + 1} failed: {e}")
                
                # 检查是否是可重试的错误
                if "timeout" in str(e).lower() or "connection" in str(e).lower():
                    continue
                elif "rate limit" in str(e).lower():
                    # 对于速率限制，等待更长时间
                    await asyncio.sleep(self.retry_delay * (attempt + 1) * 2)
                    continue
                else:
                    # 其他API错误可能不值得重试
                    break
                    
            except Exception as e:
                last_exception = e
                logger.warning(f"[{request_id}] AI analysis attempt {attempt + 1} failed with unexpected error: {e}")
        
        # 所有重试都失败了
        logger.error(f"[{request_id}] AI analysis failed after {self.max_retries} attempts")
        raise last_exception
    
    async def _create_task_with_retry(self, task_info: TaskInfo, user_id: int, source_url: str, request_id: str):
        """带重试的任务创建"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"[{request_id}] Task creation retry attempt {attempt + 1}/{self.max_retries}")
                    await asyncio.sleep(self.retry_delay * attempt)
                
                return await self.task_creator.create_task(task_info, user_id, source_url)
                
            except TaskCreationError as e:
                last_exception = e
                logger.warning(f"[{request_id}] Task creation attempt {attempt + 1} failed: {e}")
                
                # 检查是否是数据库连接问题
                if "connection" in str(e).lower() or "timeout" in str(e).lower():
                    continue
                else:
                    # 其他任务创建错误通常不值得重试
                    break
                    
            except Exception as e:
                last_exception = e
                logger.warning(f"[{request_id}] Task creation attempt {attempt + 1} failed with unexpected error: {e}")
        
        # 所有重试都失败了
        logger.error(f"[{request_id}] Task creation failed after {self.max_retries} attempts")
        raise last_exception
    
    async def extract_task_info(self, url: str) -> TaskInfo:
        """
        从URL提取任务信息（不创建任务）
        
        Args:
            url: 要分析的URL
            
        Returns:
            TaskInfo: 提取的任务信息
            
        Raises:
            URLAgentError: 当提取失败时
        """
        try:
            logger.info(f"Extracting task info from URL: {url}")
            
            # 1. 提取网页内容
            web_content = await self.content_extractor.extract_content(url)
            logger.info(f"Content extracted: {web_content.title}")
            
            # 2. AI分析内容
            task_info = await self.url_parsing_agent.analyze_content(web_content)
            logger.info(f"Task info extracted: {task_info.title}")
            
            return task_info
            
        except URLValidationError as e:
            logger.error(f"URL validation failed: {e}")
            raise URLAgentError(f"URL验证失败: {str(e)}")
            
        except ContentExtractionError as e:
            logger.error(f"Content extraction failed: {e}")
            raise URLAgentError(f"内容提取失败: {str(e)}")
            
        except ModelAPIError as e:
            logger.error(f"AI analysis failed: {e}")
            raise URLAgentError(f"AI分析失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error extracting task info: {e}")
            raise URLAgentError(f"任务信息提取失败: {str(e)}")
    
    async def extract_task_info_from_content(self, content: str) -> TaskInfo:
        """
        从文本内容提取任务信息
        
        Args:
            content: 文本内容
            
        Returns:
            TaskInfo: 提取的任务信息
            
        Raises:
            URLAgentError: 当提取失败时
        """
        try:
            logger.info("Extracting task info from text content")
            
            # 创建WebContent对象
            web_content = WebContent(
                url="",
                title="Direct Content",
                content=content,
                meta_description=None
            )
            
            # AI分析内容
            task_info = await self.url_parsing_agent.analyze_content(web_content)
            logger.info(f"Task info extracted: {task_info.title}")
            
            return task_info
            
        except ModelAPIError as e:
            logger.error(f"AI analysis failed: {e}")
            raise URLAgentError(f"AI分析失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error extracting task info from content: {e}")
            raise URLAgentError(f"任务信息提取失败: {str(e)}")

    async def extract_task_info_from_image(
        self, 
        image_data: Union[bytes, str], 
        additional_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskInfo:
        """
        从图片中提取任务信息
        
        Args:
            image_data: 图片数据（bytes或base64字符串）
            additional_prompt: 额外的分析提示
            context: 分析上下文
            
        Returns:
            TaskInfo: 提取的任务信息
            
        Raises:
            URLAgentError: 当图片解析失败时
        """
        try:
            logger.info("Starting image analysis for task extraction")
            
            # 初始化图片解析代理
            if not self._image_parsing_agent:
                await self.image_parsing_agent.initialize()
            
            # 根据是否有上下文选择解析方法
            if context:
                task_info = await self.image_parsing_agent.analyze_image_with_context(
                    image_data, context
                )
            else:
                task_info = await self.image_parsing_agent.analyze_image(
                    image_data, additional_prompt
                )
            
            logger.info(f"Task info extracted from image: {task_info.title}")
            return task_info
            
        except (ModelAPIError, ConfigurationError) as e:
            logger.error(f"Image analysis failed: {e}")
            raise URLAgentError(f"图片分析失败: {str(e)}")
            
        except ValueError as e:
            logger.error(f"Invalid image data: {e}")
            raise URLAgentError(f"图片数据无效: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error extracting task info from image: {e}")
            raise URLAgentError(f"图片任务信息提取失败: {str(e)}")
    
    async def create_task_from_info(self, task_info: TaskInfo, user_id: int, source_url: Optional[str] = None) -> int:
        """
        从任务信息创建任务
        
        Args:
            task_info: 任务信息
            user_id: 用户ID
            source_url: 源URL
            
        Returns:
            int: 创建的任务ID
            
        Raises:
            URLAgentError: 当创建失败时
        """
        try:
            logger.info(f"Creating task from info for user: {user_id}")
            
            task = await self.task_creator.create_task(task_info, user_id, source_url)
            logger.info(f"Task created successfully with ID: {task.id}")
            
            return task.id
            
        except TaskCreationError as e:
            logger.error(f"Task creation failed: {e}")
            raise URLAgentError(f"任务创建失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error creating task: {e}")
            raise URLAgentError(f"任务创建失败: {str(e)}")
    
    async def test_configuration(self) -> bool:
        """测试配置是否正确"""
        try:
            logger.info("Testing URL agent configuration")
            
            # 测试PPIO连接
            ppio_test = await self.ppio_client.test_connection()
            if not ppio_test:
                logger.error("PPIO client test failed")
                return False
            
            # 测试URL解析代理
            agent_test = await self.url_parsing_agent.test_agent()
            if not agent_test:
                logger.error("URL parsing agent test failed")
                return False
            
            logger.info("All configuration tests passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration test failed: {e}")
            return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.metrics.get_stats()
    
    def reset_metrics(self):
        """重置性能指标"""
        self.metrics.reset()
        logger.info("Performance metrics reset")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {},
            "metrics": self.get_performance_metrics()
        }
        
        try:
            # 检查PPIO客户端
            ppio_healthy = await self.ppio_client.test_connection()
            health_status["components"]["ppio_client"] = {
                "status": "healthy" if ppio_healthy else "unhealthy",
                "initialized": self._ppio_client is not None
            }
            
            # 检查URL解析代理
            agent_healthy = await self.url_parsing_agent.test_agent()
            health_status["components"]["url_parsing_agent"] = {
                "status": "healthy" if agent_healthy else "unhealthy",
                "initialized": self._url_parsing_agent is not None
            }
            
            # 检查数据库连接（如果有）
            if self.db_session:
                try:
                    # 简单的数据库连接测试
                    await self.db_session.execute("SELECT 1")
                    health_status["components"]["database"] = {
                        "status": "healthy",
                        "connected": True
                    }
                except Exception as e:
                    health_status["components"]["database"] = {
                        "status": "unhealthy",
                        "connected": False,
                        "error": str(e)
                    }
                    health_status["status"] = "degraded"
            else:
                health_status["components"]["database"] = {
                    "status": "not_configured",
                    "connected": False
                }
            
            # 检查内容提取器
            health_status["components"]["content_extractor"] = {
                "status": "healthy",
                "initialized": self._content_extractor is not None
            }
            
            # 检查任务创建器
            health_status["components"]["task_creator"] = {
                "status": "healthy" if self.db_session else "not_configured",
                "initialized": self._task_creator is not None
            }
            
            # 如果任何组件不健康，标记整体状态
            if not ppio_healthy or not agent_healthy:
                health_status["status"] = "unhealthy"
                
        except Exception as e:
            health_status["status"] = "error"
            health_status["error"] = str(e)
            logger.error(f"Health check failed: {e}")
        
        return health_status
    
    async def get_service_status(self) -> dict:
        """获取服务状态信息"""
        try:
            status = {
                "service_name": "URLAgentService",
                "components": {
                    "content_extractor": {
                        "initialized": self._content_extractor is not None,
                        "status": "ready"
                    },
                    "url_parsing_agent": {
                        "initialized": self._url_parsing_agent is not None,
                        "status": "ready" if self._url_parsing_agent else "not_initialized"
                    },
                    "image_parsing_agent": {
                        "initialized": self._image_parsing_agent is not None,
                        "status": "ready" if self._image_parsing_agent else "not_initialized"
                    },
                    "task_creator": {
                        "initialized": self._task_creator is not None,
                        "status": "ready" if self._task_creator and self.db_session else "no_db_session"
                    },
                    "ppio_client": {
                        "initialized": self._ppio_client is not None,
                        "status": "ready" if self._ppio_client else "not_initialized"
                    }
                },
                "configuration": {
                    "has_db_session": self.db_session is not None,
                    "settings_loaded": self.settings is not None
                }
            }
            
            # 测试连接状态
            if self._ppio_client:
                try:
                    connection_test = await self.ppio_client.test_connection()
                    status["components"]["ppio_client"]["connection_test"] = connection_test
                except Exception as e:
                    status["components"]["ppio_client"]["connection_error"] = str(e)
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "service_name": "URLAgentService",
                "error": str(e),
                "status": "error"
            }