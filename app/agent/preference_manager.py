"""
Preference Manager for Smart Coordinator
偏好管理器 - 管理用户偏好和个性化设置
"""
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class OutputFormat(str, Enum):
    """输出格式"""
    JSON = "JSON"
    MARKDOWN = "MARKDOWN"
    STRUCTURED = "STRUCTURED"
    PLAIN_TEXT = "PLAIN_TEXT"


class AnalysisFocus(str, Enum):
    """分析重点"""
    TECHNICAL = "TECHNICAL"
    BUSINESS = "BUSINESS"
    TIMELINE = "TIMELINE"
    FINANCIAL = "FINANCIAL"
    QUALITY = "QUALITY"


@dataclass
class UserPreferences:
    """用户偏好设置"""
    user_id: str
    output_format: OutputFormat = OutputFormat.STRUCTURED
    analysis_focus: List[AnalysisFocus] = None
    language: str = "中文"
    task_types: List[str] = None
    quality_threshold: float = 0.7
    auto_create_tasks: bool = False
    notification_enabled: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.analysis_focus is None:
            self.analysis_focus = [AnalysisFocus.TECHNICAL, AnalysisFocus.BUSINESS]
        if self.task_types is None:
            self.task_types = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['analysis_focus'] = [focus.value for focus in self.analysis_focus]
        data['output_format'] = self.output_format.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """从字典创建实例"""
        # 处理枚举类型
        if 'analysis_focus' in data:
            data['analysis_focus'] = [AnalysisFocus(focus) for focus in data['analysis_focus']]
        if 'output_format' in data:
            data['output_format'] = OutputFormat(data['output_format'])
        
        # 处理日期时间
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        return cls(**data)


@dataclass
class UserInteraction:
    """用户交互记录"""
    user_id: str
    input_content: str
    input_type: str
    user_intent: str
    result_success: bool
    processing_time: float
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PreferenceSuggestion:
    """偏好建议"""
    preference_key: str
    suggested_value: Any
    reason: str
    confidence: float


class PreferenceManager:
    """偏好管理器"""
    
    def __init__(self, storage_backend: Optional[str] = None):
        self.storage_backend = storage_backend or "memory"  # memory, file, database
        
        # 内存存储
        self.user_preferences: Dict[str, UserPreferences] = {}
        self.interaction_history: Dict[str, List[UserInteraction]] = {}
        
        # 学习参数
        self.learning_enabled = True
        self.min_interactions_for_learning = 3
        self.preference_update_threshold = 0.6
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化偏好管理器"""
        try:
            if self.storage_backend == "file":
                await self._load_from_file()
            elif self.storage_backend == "database":
                await self._load_from_database()
            
            self._initialized = True
            logger.info("偏好管理器初始化完成")
            
        except Exception as e:
            logger.error(f"偏好管理器初始化失败: {e}")
            raise
    
    async def get_user_preferences(self, user_id: str) -> UserPreferences:
        """获取用户偏好"""
        if user_id not in self.user_preferences:
            # 创建默认偏好
            self.user_preferences[user_id] = UserPreferences(user_id=user_id)
            logger.info(f"为用户 {user_id} 创建默认偏好")
        
        return self.user_preferences[user_id]
    
    async def update_user_preferences(
        self, 
        user_id: str, 
        preferences_update: Dict[str, Any]
    ) -> None:
        """更新用户偏好"""
        try:
            current_preferences = await self.get_user_preferences(user_id)
            
            # 更新偏好设置
            for key, value in preferences_update.items():
                if hasattr(current_preferences, key):
                    if key == 'output_format' and isinstance(value, str):
                        current_preferences.output_format = OutputFormat(value)
                    elif key == 'analysis_focus' and isinstance(value, list):
                        current_preferences.analysis_focus = [
                            AnalysisFocus(focus) if isinstance(focus, str) else focus 
                            for focus in value
                        ]
                    elif key == 'language':
                        current_preferences.language = value
                    elif key == 'quality_threshold':
                        current_preferences.quality_threshold = float(value)
                    elif key == 'auto_create_tasks':
                        current_preferences.auto_create_tasks = bool(value)
                    elif key == 'task_types':
                        current_preferences.task_types = value if isinstance(value, list) else [value]
                    else:
                        setattr(current_preferences, key, value)
            
            # 更新时间戳
            current_preferences.updated_at = datetime.utcnow()
            
            # 保存到存储后端
            await self._save_preferences(user_id, current_preferences)
            
            logger.info(f"用户 {user_id} 偏好更新完成")
            
        except Exception as e:
            logger.error(f"更新用户偏好失败: {e}")
            raise
    
    async def learn_from_interaction(
        self, 
        user_id: str, 
        user_input: Any,
        result: Any
    ) -> None:
        """从用户交互中学习偏好"""
        if not self.learning_enabled:
            return
        
        try:
            # 记录交互
            interaction = UserInteraction(
                user_id=user_id,
                input_content=getattr(user_input, 'content', str(user_input)),
                input_type=getattr(user_input, 'input_type', 'unknown'),
                user_intent=getattr(result, 'user_intent', 'unknown'),
                result_success=getattr(result, 'success', False),
                processing_time=getattr(result, 'processing_time', 0.0),
                timestamp=datetime.utcnow()
            )
            
            if user_id not in self.interaction_history:
                self.interaction_history[user_id] = []
            
            self.interaction_history[user_id].append(interaction)
            
            # 保持历史记录在合理长度内
            if len(self.interaction_history[user_id]) > 100:
                self.interaction_history[user_id] = self.interaction_history[user_id][-100:]
            
            # 如果有足够的交互记录，进行学习
            if len(self.interaction_history[user_id]) >= self.min_interactions_for_learning:
                await self._learn_preferences(user_id)
            
        except Exception as e:
            logger.error(f"从交互学习失败: {e}")
    
    async def suggest_preferences(self, user_id: str) -> List[PreferenceSuggestion]:
        """为用户建议偏好设置"""
        suggestions = []
        
        try:
            if user_id not in self.interaction_history:
                return suggestions
            
            interactions = self.interaction_history[user_id]
            current_preferences = await self.get_user_preferences(user_id)
            
            # 分析输入类型偏好
            input_type_counts = {}
            for interaction in interactions[-20:]:  # 最近20次交互
                input_type = interaction.input_type
                input_type_counts[input_type] = input_type_counts.get(input_type, 0) + 1
            
            # 如果用户经常使用URL输入，建议自动创建任务
            if input_type_counts.get('url', 0) > 5 and not current_preferences.auto_create_tasks:
                suggestions.append(PreferenceSuggestion(
                    preference_key="auto_create_tasks",
                    suggested_value=True,
                    reason="您经常分析URL内容，建议开启自动创建任务功能",
                    confidence=0.8
                ))
            
            # 分析成功率，建议调整质量阈值
            recent_interactions = interactions[-10:]
            success_rate = sum(1 for i in recent_interactions if i.result_success) / len(recent_interactions)
            
            if success_rate < 0.7 and current_preferences.quality_threshold > 0.5:
                suggestions.append(PreferenceSuggestion(
                    preference_key="quality_threshold",
                    suggested_value=0.5,
                    reason="降低质量阈值可能会提高处理成功率",
                    confidence=0.6
                ))
            
            # 分析处理时间，建议优化设置
            avg_processing_time = sum(i.processing_time for i in recent_interactions) / len(recent_interactions)
            if avg_processing_time > 5.0:
                suggestions.append(PreferenceSuggestion(
                    preference_key="analysis_focus",
                    suggested_value=[AnalysisFocus.TECHNICAL],
                    reason="减少分析重点可以提高处理速度",
                    confidence=0.7
                ))
            
        except Exception as e:
            logger.error(f"生成偏好建议失败: {e}")
        
        return suggestions
    
    async def _learn_preferences(self, user_id: str) -> None:
        """学习用户偏好"""
        try:
            interactions = self.interaction_history[user_id]
            current_preferences = await self.get_user_preferences(user_id)
            
            # 分析最近的交互模式
            recent_interactions = interactions[-20:]
            
            # 学习输出格式偏好
            format_preferences = {}
            for interaction in recent_interactions:
                # 这里可以根据用户的反馈或行为模式来推断偏好
                # 简化实现：如果用户经常成功处理某种类型的内容，增加相关偏好
                if interaction.result_success:
                    if interaction.input_type == 'url':
                        format_preferences['structured'] = format_preferences.get('structured', 0) + 1
                    elif interaction.input_type == 'image':
                        format_preferences['json'] = format_preferences.get('json', 0) + 1
            
            # 如果有明显的偏好模式，更新设置
            if format_preferences:
                preferred_format = max(format_preferences, key=format_preferences.get)
                confidence = format_preferences[preferred_format] / len(recent_interactions)
                
                if confidence > self.preference_update_threshold:
                    if preferred_format == 'structured' and current_preferences.output_format != OutputFormat.STRUCTURED:
                        current_preferences.output_format = OutputFormat.STRUCTURED
                        current_preferences.updated_at = datetime.utcnow()
                        logger.info(f"学习更新用户 {user_id} 输出格式偏好: {preferred_format}")
            
            # 学习任务类型偏好
            task_types = set()
            for interaction in recent_interactions:
                if interaction.result_success and 'task_type' in interaction.metadata:
                    task_types.add(interaction.metadata['task_type'])
            
            if task_types and len(task_types) != len(current_preferences.task_types):
                current_preferences.task_types = list(task_types)
                current_preferences.updated_at = datetime.utcnow()
                logger.info(f"学习更新用户 {user_id} 任务类型偏好: {task_types}")
            
        except Exception as e:
            logger.error(f"学习用户偏好失败: {e}")
    
    async def _save_preferences(self, user_id: str, preferences: UserPreferences) -> None:
        """保存偏好到存储后端"""
        if self.storage_backend == "file":
            await self._save_to_file(user_id, preferences)
        elif self.storage_backend == "database":
            await self._save_to_database(user_id, preferences)
        # memory存储不需要额外操作
    
    async def _load_from_file(self) -> None:
        """从文件加载偏好"""
        try:
            import os
            preferences_file = "user_preferences.json"
            
            if os.path.exists(preferences_file):
                with open(preferences_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for user_id, pref_data in data.items():
                    self.user_preferences[user_id] = UserPreferences.from_dict(pref_data)
                
                logger.info(f"从文件加载了 {len(self.user_preferences)} 个用户偏好")
        
        except Exception as e:
            logger.error(f"从文件加载偏好失败: {e}")
    
    async def _save_to_file(self, user_id: str, preferences: UserPreferences) -> None:
        """保存偏好到文件"""
        try:
            preferences_file = "user_preferences.json"
            
            # 读取现有数据
            data = {}
            try:
                with open(preferences_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except FileNotFoundError:
                pass
            
            # 更新数据
            data[user_id] = preferences.to_dict()
            
            # 写入文件
            with open(preferences_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            logger.error(f"保存偏好到文件失败: {e}")
    
    async def _load_from_database(self) -> None:
        """从数据库加载偏好"""
        # TODO: 实现数据库加载逻辑
        logger.warning("数据库存储后端尚未实现")
    
    async def _save_to_database(self, user_id: str, preferences: UserPreferences) -> None:
        """保存偏好到数据库"""
        # TODO: 实现数据库保存逻辑
        logger.warning("数据库存储后端尚未实现")
    
    def get_user_interaction_history(self, user_id: str, limit: int = 50) -> List[UserInteraction]:
        """获取用户交互历史"""
        if user_id not in self.interaction_history:
            return []
        
        return self.interaction_history[user_id][-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_users = len(self.user_preferences)
        total_interactions = sum(len(history) for history in self.interaction_history.values())
        
        # 统计偏好分布
        format_distribution = {}
        language_distribution = {}
        
        for preferences in self.user_preferences.values():
            format_key = preferences.output_format.value
            format_distribution[format_key] = format_distribution.get(format_key, 0) + 1
            
            lang_key = preferences.language
            language_distribution[lang_key] = language_distribution.get(lang_key, 0) + 1
        
        return {
            "total_users": total_users,
            "total_interactions": total_interactions,
            "format_distribution": format_distribution,
            "language_distribution": language_distribution,
            "learning_enabled": self.learning_enabled,
            "storage_backend": self.storage_backend
        }
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


# 全局偏好管理器实例
_preference_manager: Optional[PreferenceManager] = None


async def get_preference_manager() -> PreferenceManager:
    """获取全局偏好管理器实例"""
    global _preference_manager
    
    if _preference_manager is None:
        _preference_manager = PreferenceManager()
        await _preference_manager.initialize()
    
    return _preference_manager