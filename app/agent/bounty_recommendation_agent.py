"""
Bounty Recommendation Agent with RAG
基于RAG的Bounty推荐Agent - 结合用户偏好和任务数据库进行智能推荐
"""
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from .unified_config import get_config_manager, AgentRole
from .preference_manager import UserPreferences, get_preference_manager
from .models import TaskInfo
from .exceptions import ConfigurationError, ModelAPIError

logger = logging.getLogger(__name__)


@dataclass
class BountyRecommendation:
    """Bounty推荐结果"""
    task_id: int
    title: str
    description: str
    reward: Optional[float]
    reward_currency: str
    tags: List[str]
    difficulty_level: Optional[str]
    estimated_hours: Optional[int]
    deadline: Optional[datetime]
    match_score: float
    match_reasons: List[str]
    created_at: datetime


@dataclass
class RecommendationContext:
    """推荐上下文"""
    user_id: str
    user_preferences: UserPreferences
    user_skills: List[str]
    user_interests: List[str]
    recent_interactions: List[Dict[str, Any]]
    exclude_task_ids: List[int] = None
    
    def __post_init__(self):
        if self.exclude_task_ids is None:
            self.exclude_task_ids = []


class BountyRecommendationAgent:
    """基于RAG的Bounty推荐Agent"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.config_manager = get_config_manager()
        self.preference_manager = get_preference_manager()
        
        # RAG相关配置
        self.embedding_model = None  # 将在初始化时设置
        self.vector_store = None     # 向量存储
        self.similarity_threshold = 0.7
        self.max_recommendations = 10
        
        self._initialized = False    
    
    async def initialize(self) -> None:
        """初始化推荐Agent"""
        try:
            # 初始化嵌入模型（使用PPIO的文本嵌入能力）
            await self._initialize_embedding_model()
            
            # 初始化向量存储
            await self._initialize_vector_store()
            
            self._initialized = True
            logger.info("Bounty推荐Agent初始化完成")
            
        except Exception as e:
            logger.error(f"Bounty推荐Agent初始化失败: {e}")
            raise ConfigurationError(f"Recommendation agent initialization failed: {str(e)}")
    
    async def _initialize_embedding_model(self) -> None:
        """初始化嵌入模型"""
        # 获取配置
        coordinator_config = self.config_manager.get_agent_config(AgentRole.COORDINATOR)
        if not coordinator_config:
            raise ConfigurationError("协调器Agent配置未找到")
        
        # 创建PPIO客户端用于文本嵌入
        from .client import PPIOModelClient
        from .config import PPIOModelConfig
        
        ppio_config = PPIOModelConfig(
            api_key=coordinator_config.api_key,
            base_url=coordinator_config.base_url or "https://api.ppinfra.com/v3/openai",
            model_name="text-embedding-ada-002",  # 使用嵌入模型
            temperature=0.0
        )
        
        self.embedding_model = PPIOModelClient(ppio_config)
        logger.info("嵌入模型初始化完成")
    
    async def _initialize_vector_store(self) -> None:
        """初始化向量存储"""
        # 简化实现：使用内存存储
        # 在生产环境中可以使用Chroma、Pinecone等向量数据库
        self.vector_store = {
            "task_embeddings": {},  # task_id -> embedding
            "tag_embeddings": {},   # tag_name -> embedding
            "user_embeddings": {}   # user_id -> embedding
        }
        logger.info("向量存储初始化完成")
    
    async def get_recommendations(
        self, 
        user_id: str, 
        context: Optional[RecommendationContext] = None,
        limit: int = 10
    ) -> List[BountyRecommendation]:
        """
        获取个性化bounty推荐
        
        Args:
            user_id: 用户ID
            context: 推荐上下文
            limit: 推荐数量限制
            
        Returns:
            List[BountyRecommendation]: 推荐结果列表
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 1. 构建推荐上下文
            if not context:
                context = await self._build_recommendation_context(user_id)
            
            # 2. 获取候选任务
            candidate_tasks = await self._get_candidate_tasks(context)
            
            # 3. 计算相似度和匹配分数
            scored_tasks = await self._score_tasks(candidate_tasks, context)
            
            # 4. 排序和过滤
            recommendations = await self._rank_and_filter(scored_tasks, context, limit)
            
            logger.info(f"为用户 {user_id} 生成了 {len(recommendations)} 个推荐")
            return recommendations
            
        except Exception as e:
            logger.error(f"生成推荐失败: {e}")
            raise ModelAPIError(f"Failed to generate recommendations: {str(e)}")
    
    async def _build_recommendation_context(self, user_id: str) -> RecommendationContext:
        """构建推荐上下文"""
        # 获取用户偏好
        user_preferences = await self.preference_manager.get_user_preferences(user_id)
        
        # 获取用户技能和兴趣（从用户交互历史中推断）
        user_skills, user_interests = await self._extract_user_profile(user_id)
        
        # 获取最近的交互记录
        recent_interactions = self.preference_manager.get_user_interaction_history(user_id, 20)
        
        # 获取用户已完成或参与的任务ID（排除推荐）
        exclude_task_ids = await self._get_user_task_history(user_id)
        
        return RecommendationContext(
            user_id=user_id,
            user_preferences=user_preferences,
            user_skills=user_skills,
            user_interests=user_interests,
            recent_interactions=[
                {
                    "input_content": interaction.input_content,
                    "input_type": interaction.input_type,
                    "result_success": interaction.result_success,
                    "timestamp": interaction.timestamp
                }
                for interaction in recent_interactions
            ],
            exclude_task_ids=exclude_task_ids
        )
    
    async def _extract_user_profile(self, user_id: str) -> Tuple[List[str], List[str]]:
        """从用户交互历史中提取技能和兴趣"""
        interactions = self.preference_manager.get_user_interaction_history(user_id, 50)
        
        skills = set()
        interests = set()
        
        # 技能关键词映射
        skill_keywords = {
            "python": ["python", "django", "flask", "fastapi"],
            "javascript": ["javascript", "js", "react", "vue", "node"],
            "solidity": ["solidity", "smart contract", "ethereum", "web3"],
            "rust": ["rust", "substrate", "polkadot"],
            "go": ["golang", "go"],
            "design": ["ui", "ux", "design", "figma", "sketch"],
            "blockchain": ["blockchain", "crypto", "defi", "nft"],
            "ai": ["ai", "ml", "machine learning", "deep learning"]
        }
        
        # 兴趣关键词映射
        interest_keywords = {
            "web3": ["web3", "blockchain", "crypto", "defi"],
            "ai": ["ai", "artificial intelligence", "machine learning"],
            "gaming": ["game", "gaming", "unity", "unreal"],
            "fintech": ["fintech", "finance", "trading", "payment"],
            "social": ["social", "community", "networking"],
            "education": ["education", "learning", "tutorial"]
        }
        
        # 分析交互内容
        for interaction in interactions:
            content_lower = interaction.input_content.lower()
            
            # 提取技能
            for skill, keywords in skill_keywords.items():
                if any(keyword in content_lower for keyword in keywords):
                    skills.add(skill)
            
            # 提取兴趣
            for interest, keywords in interest_keywords.items():
                if any(keyword in content_lower for keyword in keywords):
                    interests.add(interest)
        
        return list(skills), list(interests)
    
    async def _get_user_task_history(self, user_id: str) -> List[int]:
        """获取用户的任务历史（已参与或完成的任务）"""
        try:
            # 这里需要根据实际的数据库模型来查询
            # 简化实现：返回空列表
            return []
            
        except Exception as e:
            logger.warning(f"获取用户任务历史失败: {e}")
            return []
    
    async def _get_candidate_tasks(self, context: RecommendationContext) -> List[Dict[str, Any]]:
        """获取候选任务"""
        try:
            # 模拟任务数据（在实际实现中应该从数据库查询）
            candidate_tasks = [
                {
                    "id": 1,
                    "title": "开发Web3 DeFi协议前端",
                    "description": "使用React和Web3.js开发去中心化金融协议的用户界面",
                    "reward": 5000,
                    "reward_currency": "USDT",
                    "tags": ["react", "web3", "defi", "javascript"],
                    "difficulty_level": "中级",
                    "estimated_hours": 80,
                    "deadline": datetime.utcnow() + timedelta(days=30),
                    "created_at": datetime.utcnow() - timedelta(days=2)
                },
                {
                    "id": 2,
                    "title": "智能合约安全审计",
                    "description": "对Solidity智能合约进行安全审计，识别潜在漏洞",
                    "reward": 8000,
                    "reward_currency": "ETH",
                    "tags": ["solidity", "security", "audit", "blockchain"],
                    "difficulty_level": "高级",
                    "estimated_hours": 120,
                    "deadline": datetime.utcnow() + timedelta(days=21),
                    "created_at": datetime.utcnow() - timedelta(days=1)
                },
                {
                    "id": 3,
                    "title": "AI聊天机器人开发",
                    "description": "使用Python和机器学习技术开发智能客服机器人",
                    "reward": 3000,
                    "reward_currency": "USD",
                    "tags": ["python", "ai", "nlp", "chatbot"],
                    "difficulty_level": "中级",
                    "estimated_hours": 60,
                    "deadline": datetime.utcnow() + timedelta(days=45),
                    "created_at": datetime.utcnow() - timedelta(days=3)
                }
            ]
            
            # 过滤排除的任务
            filtered_tasks = [
                task for task in candidate_tasks 
                if task["id"] not in context.exclude_task_ids
            ]
            
            return filtered_tasks
            
        except Exception as e:
            logger.error(f"获取候选任务失败: {e}")
            return []
    
    async def _score_tasks(
        self, 
        tasks: List[Dict[str, Any]], 
        context: RecommendationContext
    ) -> List[Tuple[Dict[str, Any], float, List[str]]]:
        """为任务计算匹配分数"""
        scored_tasks = []
        
        for task in tasks:
            try:
                score, reasons = await self._calculate_task_score(task, context)
                if score >= self.similarity_threshold:
                    scored_tasks.append((task, score, reasons))
            except Exception as e:
                logger.warning(f"计算任务 {task['id']} 分数失败: {e}")
                continue
        
        return scored_tasks
    
    async def _calculate_task_score(
        self, 
        task: Dict[str, Any], 
        context: RecommendationContext
    ) -> Tuple[float, List[str]]:
        """计算单个任务的匹配分数"""
        score = 0.0
        reasons = []
        
        # 1. 技能匹配 (权重: 0.4)
        skill_score = await self._calculate_skill_match(task, context.user_skills)
        score += skill_score * 0.4
        if skill_score > 0.5:
            reasons.append(f"技能匹配度: {skill_score:.1%}")
        
        # 2. 兴趣匹配 (权重: 0.3)
        interest_score = await self._calculate_interest_match(task, context.user_interests)
        score += interest_score * 0.3
        if interest_score > 0.5:
            reasons.append(f"兴趣匹配度: {interest_score:.1%}")
        
        # 3. 偏好匹配 (权重: 0.2)
        preference_score = await self._calculate_preference_match(task, context.user_preferences)
        score += preference_score * 0.2
        if preference_score > 0.5:
            reasons.append(f"偏好匹配度: {preference_score:.1%}")
        
        # 4. 历史行为匹配 (权重: 0.1)
        behavior_score = await self._calculate_behavior_match(task, context.recent_interactions)
        score += behavior_score * 0.1
        if behavior_score > 0.5:
            reasons.append(f"行为匹配度: {behavior_score:.1%}")
        
        # 5. 奖励吸引力加分
        if task.get("reward") and task["reward"] > 0:
            reward_bonus = min(task["reward"] / 1000, 0.1)  # 最多加10%
            score += reward_bonus
            if reward_bonus > 0.05:
                reasons.append(f"高奖励任务: {task['reward']} {task['reward_currency']}")
        
        # 6. 紧急程度加分
        if task.get("deadline"):
            days_left = (task["deadline"] - datetime.utcnow()).days
            if 1 <= days_left <= 7:  # 1-7天内截止的任务
                urgency_bonus = 0.05
                score += urgency_bonus
                reasons.append(f"即将截止: {days_left}天")
        
        return min(score, 1.0), reasons
    
    async def _calculate_skill_match(self, task: Dict[str, Any], user_skills: List[str]) -> float:
        """计算技能匹配度"""
        if not user_skills:
            return 0.0
        
        task_tags = [tag.lower() for tag in task.get("tags", [])]
        task_content = f"{task.get('title', '')} {task.get('description', '')}".lower()
        
        matches = 0
        for skill in user_skills:
            skill_lower = skill.lower()
            if skill_lower in task_tags or skill_lower in task_content:
                matches += 1
        
        return matches / len(user_skills) if user_skills else 0.0
    
    async def _calculate_interest_match(self, task: Dict[str, Any], user_interests: List[str]) -> float:
        """计算兴趣匹配度"""
        if not user_interests:
            return 0.0
        
        task_tags = [tag.lower() for tag in task.get("tags", [])]
        task_content = f"{task.get('title', '')} {task.get('description', '')}".lower()
        
        matches = 0
        for interest in user_interests:
            interest_lower = interest.lower()
            if interest_lower in task_tags or interest_lower in task_content:
                matches += 1
        
        return matches / len(user_interests) if user_interests else 0.0
    
    async def _calculate_preference_match(self, task: Dict[str, Any], preferences: UserPreferences) -> float:
        """计算偏好匹配度"""
        score = 0.0
        
        # 任务类型偏好
        if preferences.task_types:
            task_tags = [tag.lower() for tag in task.get("tags", [])]
            for task_type in preferences.task_types:
                if task_type.lower() in task_tags:
                    score += 0.5
        
        # 难度偏好（如果用户有历史偏好）
        if task.get("difficulty_level"):
            # 这里可以根据用户历史选择的难度来匹配
            score += 0.3
        
        # 奖励偏好
        if task.get("reward") and task["reward"] > 0:
            score += 0.2
        
        return min(score, 1.0)
    
    async def _calculate_behavior_match(
        self, 
        task: Dict[str, Any], 
        recent_interactions: List[Dict[str, Any]]
    ) -> float:
        """基于最近行为计算匹配度"""
        if not recent_interactions:
            return 0.0
        
        # 分析最近交互的内容类型和成功率
        successful_interactions = [
            interaction for interaction in recent_interactions 
            if interaction.get("result_success", False)
        ]
        
        if not successful_interactions:
            return 0.0
        
        # 简化实现：基于成功交互的内容关键词匹配
        task_content = f"{task.get('title', '')} {task.get('description', '')}".lower()
        
        matches = 0
        for interaction in successful_interactions:
            content = interaction.get("input_content", "").lower()
            # 提取关键词并匹配
            words = content.split()
            for word in words:
                if len(word) > 3 and word in task_content:
                    matches += 1
                    break
        
        return matches / len(successful_interactions)
    
    async def _rank_and_filter(
        self, 
        scored_tasks: List[Tuple[Dict[str, Any], float, List[str]]], 
        context: RecommendationContext,
        limit: int
    ) -> List[BountyRecommendation]:
        """排序和过滤推荐结果"""
        # 按分数排序
        scored_tasks.sort(key=lambda x: x[1], reverse=True)
        
        # 转换为推荐对象
        recommendations = []
        for task, score, reasons in scored_tasks[:limit]:
            try:
                recommendation = BountyRecommendation(
                    task_id=task["id"],
                    title=task["title"],
                    description=task["description"],
                    reward=task.get("reward"),
                    reward_currency=task.get("reward_currency", "USD"),
                    tags=task.get("tags", []),
                    difficulty_level=task.get("difficulty_level"),
                    estimated_hours=task.get("estimated_hours"),
                    deadline=task.get("deadline"),
                    match_score=score,
                    match_reasons=reasons,
                    created_at=task["created_at"]
                )
                recommendations.append(recommendation)
            except Exception as e:
                logger.warning(f"创建推荐对象失败: {e}")
                continue
        
        return recommendations
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


# 全局推荐Agent实例
_recommendation_agent: Optional[BountyRecommendationAgent] = None


async def get_recommendation_agent(db_session: AsyncSession) -> BountyRecommendationAgent:
    """获取全局推荐Agent实例"""
    global _recommendation_agent
    
    if _recommendation_agent is None:
        _recommendation_agent = BountyRecommendationAgent(db_session)
        await _recommendation_agent.initialize()
    
    return _recommendation_agent