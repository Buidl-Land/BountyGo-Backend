"""
Image parsing agent using PPIO vision language models.
"""
import json
import base64
import logging
from io import BytesIO
from typing import Optional, Union, Dict, Any
from PIL import Image
import httpx

from app.agent.config import PPIOModelConfig
from app.agent.client import PPIOModelClient
from app.agent.models import TaskInfo
from app.agent.exceptions import ModelAPIError, ConfigurationError

logger = logging.getLogger(__name__)


class ImageParsingAgent:
    """图片解析代理类，使用PPIO视觉语言模型分析图片内容并提取任务信息"""
    
    def __init__(self, config: PPIOModelConfig):
        """
        初始化图片解析代理
        
        Args:
            config: PPIO模型配置
        """
        self.config = config
        self.client: Optional[PPIOModelClient] = None
        self.agent_role = "image_analyzer"  # 标识这是图片分析代理
        
        # 支持的图片格式
        self.supported_formats = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'}
        
        # 图片大小限制（字节）
        self.max_image_size = 10 * 1024 * 1024  # 10MB
        self.max_image_dimension = 4096  # 最大尺寸
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.client:
            await self.client.close()
    
    async def initialize(self):
        """初始化客户端"""
        try:
            # 确保使用支持视觉的模型
            if not self.config.supports_vision():
                vision_model = self.config.get_preferred_vision_model()
                logger.info(f"当前模型不支持视觉，切换到推荐模型: {vision_model}")
                self.config.model_name = vision_model
            
            self.client = PPIOModelClient(self.config)
            
            # 测试连接
            connection_ok = await self.client.test_connection()
            if not connection_ok:
                raise ConfigurationError("Failed to connect to PPIO API")
            
            logger.info(f"ImageParsingAgent initialized with model: {self.config.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ImageParsingAgent: {e}")
            raise ConfigurationError(f"Agent initialization failed: {str(e)}")
    
    def _get_ocr_prompt(self) -> str:
        """获取OCR文字提取的系统提示词"""
        return """你是一个专业的OCR文字识别专家。请仔细分析图片中的所有文字内容，并按照以下要求提取：

1. 识别图片中的所有可见文字
2. 保持文字的原始格式和结构
3. 如果有表格或列表，请保持其结构
4. 如果文字模糊或不清楚，请标注[不清楚]
5. 按照从上到下、从左到右的顺序提取文字

请只返回提取的文字内容，不要添加任何解释或分析。"""

    def _get_task_analysis_prompt(self) -> str:
        """获取任务信息分析的系统提示词"""
        return """你是一个专业的bounty任务信息分析专家。请根据提供的文字内容，提取其中的任务相关信息。

请按照以下JSON格式返回提取的信息：
{
    "title": "任务标题",
    "description": "任务描述",
    "reward": 金额数字或null,
    "reward_currency": "货币/代币代码",
    "deadline": "YYYY-MM-DDTHH:MM:SS格式的日期时间或null",
    "tags": ["标签1", "标签2"],
    "difficulty_level": "初级/中级/高级或null",
    "estimated_hours": 预估工时数字或null
}

详细分析指南：

**1. 任务标题 (title)**
- 提取主要的活动/比赛/任务名称
- 如果是比赛，包含比赛名称
- 保持简洁明确，去除多余修饰词

**2. 任务描述 (description)**
- 整合所有相关信息：活动内容、参与要求、奖励说明等
- 包含关键的参与条件和要求
- 保持信息完整性和可读性

**3. 奖励金额 (reward)**
- 提取最高奖励金额的数字部分
- 支持各种表达：¥1000、$500、1K、一千等
- 如果有多个奖项，取最高金额
- 只返回数字，不包含货币符号

**4. 奖励货币 (reward_currency)**
- 识别货币类型：CNY(人民币¥)、USD($)、EUR(€)等
- 识别代币：ETH、BTC、USDT、XION等
- 默认为USD如果无法确定

**5. 截止时间 (deadline)**
- 提取明确的截止日期
- 转换相对时间为绝对时间（如"7月4日"转为"2024-07-04T23:59:59"）
- 如果只有日期，默认为当天23:59:59
- 格式：YYYY-MM-DDTHH:MM:SS

**6. 技术标签 (tags)**
- 提取技术栈：开发语言、框架、工具等
- 提取领域标签：移动开发、Web3、区块链、AI等
- 提取活动类型：比赛、开发、创作、设计等
- 每个标签保持简洁（1-3个字）

**7. 难度等级 (difficulty_level)**
- 根据技术要求和复杂度判断：初级、中级、高级
- 考虑目标受众（新手友好=初级，专业开发者=中级/高级）

**8. 预估工时 (estimated_hours)**
- 根据任务复杂度和截止时间估算
- 比赛/创作类：20-80小时
- 简单开发：10-40小时
- 复杂项目：40-200小时

**特殊处理规则：**
- Web3/区块链项目：标签包含"web3"、"区块链"
- 移动开发：标签包含"移动开发"、"app"
- 比赛活动：标签包含"比赛"、"竞赛"
- 内容创作：标签包含"创作"、"内容"

请确保返回的JSON格式正确，不要包含任何额外的文本或解释。"""

    async def analyze_image(
        self, 
        image_data: Union[bytes, str], 
        additional_prompt: Optional[str] = None
    ) -> TaskInfo:
        """
        分析图片内容并提取任务信息（两步处理：OCR + 任务分析）
        
        Args:
            image_data: 图片数据（bytes）或base64字符串
            additional_prompt: 额外的分析提示
            
        Returns:
            TaskInfo: 提取的任务信息
            
        Raises:
            ModelAPIError: 当AI分析失败时
            ConfigurationError: 当配置错误时
        """
        if not self.client:
            raise ConfigurationError("Client not initialized")
        
        try:
            # 步骤1: 使用视觉模型进行OCR文字提取
            logger.info("Step 1: Extracting text from image using vision model")
            extracted_text = await self._extract_text_from_image(image_data, additional_prompt)
            
            if not extracted_text or len(extracted_text.strip()) < 10:
                raise ModelAPIError("No meaningful text extracted from image")
            
            logger.info(f"Extracted text: {extracted_text[:200]}...")
            
            # 步骤2: 使用文本处理模型分析任务信息
            logger.info("Step 2: Analyzing extracted text for task information")
            task_info = await self._analyze_text_for_task_info(extracted_text)
            
            logger.info(f"Successfully extracted task info from image: {task_info.title}")
            return task_info
            
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            raise ModelAPIError(f"Failed to analyze image: {str(e)}")
    
    async def _extract_text_from_image(self, image_data: Union[bytes, str], additional_prompt: Optional[str] = None) -> str:
        """
        第一步：从图片中提取文字内容
        """
        try:
            # 验证和处理图片
            processed_image = await self._process_image(image_data)
            
            # 构建OCR消息（简化格式，只做文字提取）
            prompt = self._get_ocr_prompt()
            if additional_prompt:
                prompt += f"\n\n额外要求：{additional_prompt}"
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{processed_image}"
                            }
                        }
                    ]
                }
            ]
            
            # 获取OCR响应
            response = await self.client.chat_completion(messages)
            
            if not response:
                raise ModelAPIError("No response from vision model for OCR")
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Text extraction from image failed: {e}")
            raise ModelAPIError(f"Failed to extract text from image: {str(e)}")
    
    async def _analyze_text_for_task_info(self, extracted_text: str) -> TaskInfo:
        """
        第二步：分析提取的文字内容，获取任务信息
        """
        try:
            # 使用文本处理专用模型（URL_PARSER_MODEL）进行任务信息分析
            from app.agent.config import url_agent_settings
            from app.agent.client import PPIOModelClient
            
            # 获取文本处理专用配置
            text_config = url_agent_settings.get_ppio_config("url_parser")
            text_client = PPIOModelClient(text_config)
            
            # 构建任务分析消息
            messages = [
                {
                    "role": "system",
                    "content": self._get_task_analysis_prompt()
                },
                {
                    "role": "user", 
                    "content": f"请从以下文字内容中提取任务信息：\n\n{extracted_text}"
                }
            ]
            
            # 获取任务分析响应
            response = await text_client.chat_completion(messages)
            
            if not response:
                raise ModelAPIError("No response from text analysis model")
            
            # 解析响应内容
            task_info = self._parse_response(response)
            
            return task_info
            
        except Exception as e:
            logger.error(f"Text analysis for task info failed: {e}")
            raise ModelAPIError(f"Failed to analyze text for task info: {str(e)}")
    
    async def _process_image(self, image_data: Union[bytes, str]) -> str:
        """
        处理和验证图片数据
        
        Args:
            image_data: 图片数据
            
        Returns:
            str: base64编码的图片数据
        """
        try:
            # 如果是base64字符串，先解码
            if isinstance(image_data, str):
                # 移除可能的data URL前缀
                if image_data.startswith('data:'):
                    image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
            else:
                image_bytes = image_data
            
            # 检查文件大小
            if len(image_bytes) > self.max_image_size:
                raise ValueError(f"Image too large: {len(image_bytes)} bytes (max: {self.max_image_size})")
            
            # 使用PIL验证和处理图片
            with Image.open(BytesIO(image_bytes)) as img:
                # 检查图片格式
                img_format = img.format.lower() if img.format else 'unknown'
                if img_format not in self.supported_formats:
                    raise ValueError(f"Unsupported image format: {img_format}")
                
                # 检查图片尺寸
                width, height = img.size
                if width > self.max_image_dimension or height > self.max_image_dimension:
                    # 等比缩放
                    img.thumbnail((self.max_image_dimension, self.max_image_dimension), Image.Resampling.LANCZOS)
                    logger.info(f"Image resized from {width}x{height} to {img.size}")
                
                # 转换为RGB（如果需要）
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 重新编码为JPEG
                output_buffer = BytesIO()
                img.save(output_buffer, format='JPEG', quality=85, optimize=True)
                processed_bytes = output_buffer.getvalue()
            
            # 返回base64编码
            return base64.b64encode(processed_bytes).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            raise ValueError(f"Invalid image data: {str(e)}")
    
    def _parse_response(self, response_content: str) -> TaskInfo:
        """解析AI响应并创建TaskInfo对象"""
        try:
            # 清理响应内容
            cleaned_content = response_content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]
            cleaned_content = cleaned_content.strip()
            
            # 解析JSON
            response_data = json.loads(cleaned_content)
            
            # 验证必需字段
            if not response_data.get("title"):
                raise ValueError("Missing required field: title")
            
            # 创建TaskInfo对象
            task_info = TaskInfo(
                title=response_data["title"],
                description=response_data.get("description"),
                reward=response_data.get("reward"),
                reward_currency=response_data.get("reward_currency") or "USD",
                deadline=self._parse_deadline(response_data.get("deadline")) if response_data.get("deadline") else None,
                tags=response_data.get("tags", []),
                difficulty_level=response_data.get("difficulty_level"),
                estimated_hours=response_data.get("estimated_hours")
            )
            
            return task_info
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content length: {len(response_content)}")
            raise ModelAPIError(f"Invalid JSON response from vision model: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            raise ModelAPIError(f"Response parsing failed: {str(e)}")
    
    def _parse_deadline(self, deadline_str: str) -> Optional[int]:
        """解析日期字符串为时间戳"""
        if not deadline_str:
            return None
        
        try:
            from datetime import datetime
            import time
            
            # 尝试解析ISO格式
            if 'T' in deadline_str:
                dt = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
            else:
                # 尝试解析日期格式
                dt = datetime.strptime(deadline_str, '%Y-%m-%d')
            
            return int(dt.timestamp())
        except Exception as e:
            logger.warning(f"Failed to parse deadline '{deadline_str}': {e}")
            return None
    
    async def analyze_image_with_context(
        self, 
        image_data: Union[bytes, str],
        context: Dict[str, Any]
    ) -> TaskInfo:
        """
        基于上下文分析图片
        
        Args:
            image_data: 图片数据
            context: 分析上下文，包含额外信息
            
        Returns:
            TaskInfo: 提取的任务信息
        """
        context_prompt = "请分析这张图片中的任务信息"
        
        if context.get("task_type"):
            context_prompt += f"，重点关注{context['task_type']}相关内容"
        
        if context.get("platform"):
            context_prompt += f"，这是来自{context['platform']}平台的图片"
        
        if context.get("language"):
            context_prompt += f"，请用{context['language']}语言理解内容"
        
        return await self.analyze_image(image_data, context_prompt)
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取代理信息"""
        return {
            "role_name": "Image Content Analyzer",
            "model_name": self.config.model_name,
            "supports_vision": self.config.supports_vision(),
            "supported_formats": list(self.supported_formats),
            "max_image_size": self.max_image_size,
            "max_dimension": self.max_image_dimension,
            "initialized": self.client is not None
        } 