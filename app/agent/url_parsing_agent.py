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
        self.agent_role = "url_parser"  # 标识这是URL解析代理
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
        return """你是一个专业的URL内容分析专家。你的任务是分析网页内容并提取结构化的任务信息和主办方信息。

请按照以下JSON格式返回提取的信息：
{
    "title": "任务标题",
    "summary": "任务简介（1-2句话概括）",
    "description": "任务详细描述",
    "deadline": 时间戳数字或null,
    "category": "任务分类或null",
    "reward_details": "奖励详情描述或null",
    "reward_type": "奖励分类或null",
    "reward": 奖励金额数字或null,
    "reward_currency": "奖励货币如USD、USDC等或null",
    "tags": ["标签1", "标签2"] 或null,
    "difficulty_level": "难度等级如初级、中级、高级或null",
    "estimated_hours": 预估工时数字或null,
    "organizer_name": "主办方名称或null",
    "external_link": "活动原始链接或null"
}

分析时请注意：
1. 提取准确的任务标题、简介和详细描述
2. 查找截止日期信息，同时提供日期格式和时间戳
3. 根据内容判断任务分类，可以是任何合理的分类名称，建议分类包括：
   - 黑客松: 编程竞赛、开发比赛、技术挑战、Hackathon
   - 征文: 文章写作、内容创作、博客征集、写作比赛
   - Meme创作: 表情包制作、创意图片、幽默内容、设计比赛
   - Web3交互: 区块链操作、DeFi体验、NFT相关、链上交互
   - 社媒抽奖: 社交媒体活动、转发抽奖、关注有奖、Twitter活动
   - 开发实战: 代码实现、技术学习、项目开发、编程练习
   - 交易竞赛：交易比赛、交易竞赛、交易挑战、交易活动
   - 答题竞赛：答题比赛、答题竞赛、答题挑战、答题活动
   - 或其他任何合理的分类名称
4. 提取奖励信息：
   - reward_details: 所有奖励的总数，如"总共10000u"
   - reward_type: 奖励分配方式，可选值：
     * "每人": 每个获奖者都能获得完整奖励
     * "瓜分": 多个获奖者平分总奖励
     * "抽奖": 随机抽取获奖者
     * "积分": 以积分形式发放奖励
     * "权益": 非现金奖励，如NFT、白名单等
5. 识别主办方名称：
   - 从页面内容中推断组织名称、公司名称或个人名称
   - 如果无法确定具体主办方，可以设置为null

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

            # 验证任务分类 - 使用专门的分类验证方法
            category = self._validate_category(validated_data.get("category"))

            # 创建TaskInfo对象
            task_info = TaskInfo(
                title=validated_data["title"],
                summary=validated_data.get("summary"),
                description=validated_data.get("description"),
                deadline=validated_data.get("deadline"),
                category=category, # 使用验证后的分类
                reward_details=validated_data.get("reward_details"),
                reward_type=validated_data.get("reward_type"),
                reward=validated_data.get("reward"),
                reward_currency=validated_data.get("reward_currency"),
                tags=validated_data.get("tags"),
                difficulty_level=validated_data.get("difficulty_level"),
                estimated_hours=validated_data.get("estimated_hours"),
                organizer_name=validated_data.get("organizer_name"),
                external_link=validated_data.get("external_link")
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
        if len(title) > 255:
            logger.warning(f"Title too long, truncating: {title[:50]}...")
            title = title[:255]
        data["title"] = title

        # 验证简介
        if data.get("summary") and isinstance(data["summary"], str):
            summary = data["summary"].strip()
            if len(summary) > 500:
                logger.warning("Summary too long, truncating")
                summary = summary[:500]
            data["summary"] = summary if summary else None

        # 验证描述
        if data.get("description") and isinstance(data["description"], str):
            description = data["description"].strip()
            if len(description) > 10000:
                logger.warning("Description too long, truncating")
                description = description[:10000]
            data["description"] = description if description else None

        # 验证主办方名称
        if data.get("organizer_name") and isinstance(data["organizer_name"], str):
            organizer_name = data["organizer_name"].strip()
            if len(organizer_name) > 255:
                logger.warning("Organizer name too long, truncating")
                organizer_name = organizer_name[:255]
            data["organizer_name"] = organizer_name if organizer_name else None

        # 验证截止日期时间戳
        if data.get("deadline"):
            try:
                timestamp = int(data["deadline"])
                # 验证时间戳是否合理（不能是过去太久或未来太远）
                import time
                current_time = int(time.time())
                if timestamp < current_time - 86400:  # 不能早于昨天
                    logger.warning("Deadline timestamp is in the past, setting to None")
                    data["deadline"] = None
                elif timestamp > current_time + 365 * 24 * 3600:  # 不能超过一年后
                    logger.warning("Deadline timestamp is too far in future, setting to None")
                    data["deadline"] = None
                else:
                    data["deadline"] = timestamp
            except (ValueError, TypeError):
                logger.warning("Invalid deadline timestamp, setting to None")
                data["deadline"] = None

        # 验证奖励详情
        if data.get("reward_details") and isinstance(data["reward_details"], str):
            reward_details = data["reward_details"].strip()
            if len(reward_details) > 1000:
                logger.warning("Reward details too long, truncating")
                reward_details = reward_details[:1000]
            data["reward_details"] = reward_details if reward_details else None

        # 验证奖励分类
        if data.get("reward_type") and isinstance(data["reward_type"], str):
            reward_type = data["reward_type"].strip()
            valid_reward_types = ["每人", "瓜分", "抽奖", "积分", "权益"]
            if reward_type not in valid_reward_types:
                logger.warning(f"Invalid reward type: {reward_type}, setting to None")
                data["reward_type"] = None
            else:
                data["reward_type"] = reward_type

        # 验证奖励金额
        if data.get("reward"):
            try:
                reward = float(data["reward"])
                if reward < 0:
                    logger.warning("Negative reward amount, setting to None")
                    data["reward"] = None
                else:
                    data["reward"] = reward
            except (ValueError, TypeError):
                logger.warning("Invalid reward amount, setting to None")
                data["reward"] = None

        # 验证奖励货币
        if data.get("reward_currency") and isinstance(data["reward_currency"], str):
            currency = data["reward_currency"].strip().upper()
            if len(currency) > 10:
                logger.warning("Currency code too long, truncating")
                currency = currency[:10]
            data["reward_currency"] = currency if currency else None

        # 验证标签
        if data.get("tags") and isinstance(data["tags"], list):
            clean_tags = []
            for tag in data["tags"]:
                if isinstance(tag, str) and tag.strip():
                    clean_tag = tag.strip()[:50]  # 限制标签长度
                    if clean_tag not in clean_tags:
                        clean_tags.append(clean_tag)
            data["tags"] = clean_tags if clean_tags else None

        # 验证难度等级
        if data.get("difficulty_level") and isinstance(data["difficulty_level"], str):
            difficulty = data["difficulty_level"].strip()
            if len(difficulty) > 20:
                logger.warning("Difficulty level too long, truncating")
                difficulty = difficulty[:20]
            data["difficulty_level"] = difficulty if difficulty else None

        # 验证预估工时
        if data.get("estimated_hours"):
            try:
                hours = int(data["estimated_hours"])
                if hours < 0:
                    logger.warning("Negative estimated hours, setting to None")
                    data["estimated_hours"] = None
                elif hours > 10000:  # 防止过大的值
                    logger.warning("Estimated hours too large, setting to None")
                    data["estimated_hours"] = None
                else:
                    data["estimated_hours"] = hours
            except (ValueError, TypeError):
                logger.warning("Invalid estimated hours, setting to None")
                data["estimated_hours"] = None

        # 验证外部链接
        if data.get("external_link") and isinstance(data["external_link"], str):
            link = data["external_link"].strip()
            if len(link) > 2000:
                logger.warning("External link too long, truncating")
                link = link[:2000]
            data["external_link"] = link if link else None

        return data



    def _validate_category(self, category: Optional[str]) -> Optional[str]:
        """验证任务分类 - 只校验是否有分类，不强制要求特定分类"""
        if not category:
            return None

        category_clean = category.strip()
        if len(category_clean) == 0:
            return None

        # 不再强制要求特定分类，只返回清理后的分类名称
        # 限制长度避免过长
        if len(category_clean) > 50:
            logger.warning(f"Category name too long, truncating: {category_clean[:50]}...")
            category_clean = category_clean[:50]

        return category_clean

    async def extract_from_content(self, content: str) -> TaskInfo:
        """
        从文本内容中提取任务信息

        Args:
            content: 要分析的文本内容

        Returns:
            TaskInfo: 提取的任务信息
        """
        try:
            logger.info("Starting content analysis")

            # 构建分析提示
            user_prompt = f"""请分析以下文本内容并提取任务信息：

{content}

请严格按照JSON格式返回结果。"""

            # 构建消息
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": user_prompt}
            ]

            # 调用AI分析
            response = await self.client.chat_completion(messages)

            # 解析响应
            task_info = self._parse_response(response)

            logger.info(f"Content analysis completed: {task_info.title}")
            return task_info

        except Exception as e:
            logger.error(f"Error extracting from content: {str(e)}")
            raise

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