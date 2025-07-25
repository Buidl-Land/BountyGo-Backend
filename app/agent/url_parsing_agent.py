"""
URL Parsing Agent implementation using PPIO model client.
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .client import PPIOModelClient
from .config import PPIOModelConfig
from .models import TaskInfo, WebContent
from .exceptions import ModelAPIError, ConfigurationError

logger = logging.getLogger(__name__)


class URLParsingAgent:
    """基于PPIO模型的URL内容解析代理"""
    
    def __init__(self, ppio_config: PPIOModelConfig):
        """
        初始化URL解析代理
        
        Args:
            ppio_config: PPIO模型配置
        """
        self.config = ppio_config
        self.client: Optional[PPIOModelClient] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """初始化PPIO客户端"""
        try:
            self.client = PPIOModelClient(self.config)
            logger.info(f"URLParsingAgent initialized with model: {self.config.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize URLParsingAgent: {e}")
            raise ConfigurationError(f"Agent initialization failed: {str(e)}")
    
    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        return """你是一个专业的URL内容分析专家。你的任务是分析网页内容并提取结构化的任务信息。

请按照以下JSON格式返回提取的信息：
{
    "title": "任务标题",
    "description": "任务描述",
    "reward": 金额数字或null,
    "reward_currency": "货币代码",
    "deadline": "YYYY-MM-DD格式的日期或null",
    "tags": ["标签1", "标签2"],
    "difficulty_level": "初级/中级/高级或null",
    "estimated_hours": 预估工时数字或null
}

分析时请注意：
1. 提取准确的任务标题和描述
2. 识别奖励金额和货币类型（支持USD、CNY、EUR等）
3. 查找截止日期信息，转换为YYYY-MM-DD格式
4. 根据内容推断相关的技能标签（如Python、JavaScript、设计、写作等）
5. 评估任务难度等级（初级、中级、高级）
6. 估算完成任务所需的工时

如果某些信息无法从内容中提取，请设置为null。
请确保返回的JSON格式正确，不要包含任何额外的文本。"""

    async def analyze_content(self, web_content: WebContent) -> TaskInfo:
        """
        分析网页内容并提取任务信息
        
        Args:
            web_content: 网页内容对象
            
        Returns:
            TaskInfo: 提取的任务信息
            
        Raises:
            ModelAPIError: 当AI分析失败时
        """
        if not self.client:
            raise ConfigurationError("Client not initialized")
        
        try:
            # 构建分析内容
            analysis_content = self._build_analysis_content(web_content)
            
            # 构建消息
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": analysis_content}
            ]
            
            # 获取AI响应
            logger.info(f"Analyzing content from URL: {web_content.url}")
            response = await self.client.chat_completion(messages)
            
            if not response:
                raise ModelAPIError("No response from model")
            
            # 解析响应内容 (response is already a string from chat_completion)
            response_content = response
            task_info = self._parse_response(response_content)
            
            logger.info(f"Successfully extracted task info: {task_info.title}")
            return task_info
            
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            raise ModelAPIError(f"Failed to analyze content: {str(e)}")
    
    def _build_analysis_content(self, web_content: WebContent) -> str:
        """构建用于分析的内容"""
        content_parts = [
            f"URL: {web_content.url}",
            f"标题: {web_content.title}",
        ]
        
        if web_content.meta_description:
            content_parts.append(f"Meta描述: {web_content.meta_description}")
        
        content_parts.append(f"内容:\n{web_content.content}")
        
        return "\n\n".join(content_parts)
    
    def _parse_response(self, response_content: str) -> TaskInfo:
        """
        解析AI响应并转换为TaskInfo对象
        
        Args:
            response_content: AI响应内容
            
        Returns:
            TaskInfo: 解析后的任务信息
            
        Raises:
            ModelAPIError: 当解析失败时
        """
        try:
            # 清理响应内容，移除可能的markdown代码块标记
            cleaned_content = response_content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]
            cleaned_content = cleaned_content.strip()
            
            # 尝试解析JSON响应
            response_data = json.loads(cleaned_content)
            
            # 验证响应数据结构
            validated_data = self._validate_response_data(response_data)
            
            # 处理日期字段
            deadline = self._parse_deadline(validated_data.get("deadline"))
            
            # 验证和清理标签
            tags = self._validate_tags(validated_data.get("tags", []))
            
            # 验证难度等级
            difficulty_level = self._validate_difficulty_level(validated_data.get("difficulty_level"))
            
            # 创建TaskInfo对象
            task_info = TaskInfo(
                title=validated_data["title"],
                description=validated_data.get("description"),
                reward=validated_data.get("reward"),
                reward_currency=validated_data.get("reward_currency") or "USD",
                deadline=deadline,
                tags=tags,
                difficulty_level=difficulty_level,
                estimated_hours=validated_data.get("estimated_hours")
            )
            
            # 使用Pydantic验证
            task_info.model_validate(task_info.model_dump())
            
            return task_info
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response_content}")
            raise ModelAPIError(f"Invalid JSON response from AI: {str(e)}")
        
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            raise ModelAPIError(f"Response parsing failed: {str(e)}")
    
    def _validate_response_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证响应数据结构"""
        if not isinstance(data, dict):
            raise ValueError("Response must be a JSON object")
        
        # 验证必需字段
        if not data.get("title") or not isinstance(data["title"], str):
            raise ValueError("Missing or invalid required field: title")
        
        # 清理和验证标题
        title = data["title"].strip()
        if len(title) == 0:
            raise ValueError("Title cannot be empty")
        if len(title) > 200:
            logger.warning(f"Title too long, truncating: {title[:50]}...")
            title = title[:200]
        data["title"] = title
        
        # 验证描述
        if data.get("description") and isinstance(data["description"], str):
            description = data["description"].strip()
            if len(description) > 5000:
                logger.warning("Description too long, truncating")
                description = description[:5000]
            data["description"] = description if description else None
        
        # 验证奖励金额
        if data.get("reward") is not None:
            try:
                reward = float(data["reward"])
                if reward < 0:
                    logger.warning("Negative reward amount, setting to None")
                    data["reward"] = None
                else:
                    data["reward"] = reward
            except (ValueError, TypeError):
                logger.warning(f"Invalid reward amount: {data['reward']}")
                data["reward"] = None
        
        # 验证货币代码
        if data.get("reward_currency"):
            currency = str(data["reward_currency"]).upper()
            valid_currencies = ["USD", "CNY", "EUR", "GBP", "JPY", "KRW"]
            if currency not in valid_currencies:
                logger.warning(f"Unknown currency: {currency}, defaulting to USD")
                data["reward_currency"] = "USD"
            else:
                data["reward_currency"] = currency
        else:
            # 确保reward_currency始终有值
            data["reward_currency"] = "USD"
        
        # 验证预估工时
        if data.get("estimated_hours") is not None:
            try:
                hours = int(data["estimated_hours"])
                if hours < 0:
                    logger.warning("Negative estimated hours, setting to None")
                    data["estimated_hours"] = None
                elif hours > 1000:
                    logger.warning("Estimated hours too large, capping at 1000")
                    data["estimated_hours"] = 1000
                else:
                    data["estimated_hours"] = hours
            except (ValueError, TypeError):
                logger.warning(f"Invalid estimated hours: {data['estimated_hours']}")
                data["estimated_hours"] = None
        
        return data
    
    def _parse_deadline(self, deadline_str: Optional[str]) -> Optional[datetime]:
        """解析截止日期"""
        if not deadline_str:
            return None
        
        try:
            # 支持多种日期格式
            date_formats = [
                "%Y-%m-%d",
                "%Y/%m/%d", 
                "%d/%m/%Y",
                "%d-%m-%Y",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S"
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(str(deadline_str).strip(), fmt)
                except ValueError:
                    continue
            
            logger.warning(f"Unable to parse deadline: {deadline_str}")
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing deadline {deadline_str}: {e}")
            return None
    
    def _validate_tags(self, tags: List[Any]) -> List[str]:
        """验证和清理标签"""
        if not isinstance(tags, list):
            logger.warning("Tags must be a list, ignoring")
            return []
        
        validated_tags = []
        for tag in tags:
            if isinstance(tag, str):
                cleaned_tag = tag.strip().lower()
                if cleaned_tag and len(cleaned_tag) <= 50:
                    validated_tags.append(cleaned_tag)
                elif len(cleaned_tag) > 50:
                    logger.warning(f"Tag too long, ignoring: {cleaned_tag[:20]}...")
            else:
                logger.warning(f"Invalid tag type: {type(tag)}")
        
        # 去重并限制数量
        unique_tags = list(dict.fromkeys(validated_tags))  # 保持顺序的去重
        if len(unique_tags) > 10:
            logger.warning("Too many tags, keeping first 10")
            unique_tags = unique_tags[:10]
        
        return unique_tags
    
    def _validate_difficulty_level(self, difficulty: Optional[str]) -> Optional[str]:
        """验证难度等级"""
        if not difficulty:
            return None
        
        valid_levels = ["初级", "中级", "高级", "beginner", "intermediate", "advanced"]
        difficulty_str = str(difficulty).strip()
        
        # 标准化难度等级
        difficulty_mapping = {
            "beginner": "初级",
            "intermediate": "中级", 
            "advanced": "高级",
            "easy": "初级",
            "medium": "中级",
            "hard": "高级"
        }
        
        difficulty_lower = difficulty_str.lower()
        if difficulty_lower in difficulty_mapping:
            return difficulty_mapping[difficulty_lower]
        elif difficulty_str in valid_levels:
            return difficulty_str
        else:
            logger.warning(f"Invalid difficulty level: {difficulty}, setting to None")
            return None
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取代理信息"""
        return {
            "role_name": "URL Content Analyzer",
            "model_name": self.config.model_name,
            "supports_structured_output": self.config.supports_structured_output(),
            "supports_function_calling": self.config.supports_function_calling(),
            "initialized": self.client is not None
        }
    
    async def test_agent(self) -> bool:
        """测试代理功能"""
        try:
            if not self.client:
                return False
            
            # 创建测试内容
            test_content = WebContent(
                url="https://example.com/test",
                title="Test Task",
                content="This is a test task for Python development. Reward: $100. Deadline: 2024-12-31.",
                meta_description="Test task description",
                extracted_at=datetime.utcnow()
            )
            
            # 测试分析功能
            result = await self.analyze_content(test_content)
            
            # 验证结果
            return (
                result.title is not None and
                len(result.title) > 0
            )
            
        except Exception as e:
            logger.error(f"Agent test failed: {e}")
            return False
    
    def reset_conversation(self) -> None:
        """重置对话历史"""
        # PPIO客户端是无状态的，不需要重置
        logger.info("Agent conversation history reset (no-op for PPIO client)")