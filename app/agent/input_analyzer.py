"""
Input Analyzer for Smart Coordinator
输入分析器 - 分析和分类用户输入
"""
import re
import logging
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass
from urllib.parse import urlparse
import base64

logger = logging.getLogger(__name__)


class InputType(str, Enum):
    """输入类型"""
    TEXT = "text"
    URL = "url"
    IMAGE = "image"
    MIXED = "mixed"


class UserIntent(str, Enum):
    """用户意图类型"""
    CREATE_TASK = "create_task"
    ANALYZE_CONTENT = "analyze_content"
    SET_PREFERENCES = "set_preferences"
    GET_STATUS = "get_status"
    CHAT = "chat"
    HELP = "help"


@dataclass
class InputAnalysisResult:
    """输入分析结果"""
    input_type: InputType
    user_intent: UserIntent
    confidence: float
    extracted_data: Optional[Any] = None
    extracted_preferences: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class InputAnalyzer:
    """输入分析器"""
    
    def __init__(self):
        # URL检测正则表达式
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
        # 意图识别关键词
        self.intent_keywords = {
            UserIntent.CREATE_TASK: [
                "创建任务", "create task", "新建任务", "发布任务", "添加任务",
                "make task", "new task", "add task", "post task"
            ],
            UserIntent.ANALYZE_CONTENT: [
                "分析", "analyze", "解析", "parse", "提取", "extract",
                "看看", "check", "识别", "identify", "理解", "understand"
            ],
            UserIntent.SET_PREFERENCES: [
                "设置", "set", "配置", "config", "偏好", "preference",
                "我希望", "i want", "我需要", "i need", "格式", "format",
                "语言", "language", "重点", "focus"
            ],
            UserIntent.GET_STATUS: [
                "状态", "status", "情况", "condition", "运行", "running",
                "健康", "health", "系统", "system", "服务", "service"
            ],

            UserIntent.HELP: [
                "帮助", "help", "怎么", "how", "什么", "what", "指南", "guide",
                "使用", "usage", "说明", "instruction"
            ]
        }
        
        # 偏好设置关键词
        self.preference_keywords = {
            "output_format": ["json", "markdown", "结构化", "structured"],
            "language": ["中文", "english", "chinese", "英文"],
            "analysis_focus": ["技术", "technical", "商业", "business", "时间", "timeline"],
            "quality_threshold": ["高质量", "high quality", "严格", "strict"]
        }
    
    async def analyze_input(self, content: str) -> InputAnalysisResult:
        """
        分析用户输入
        
        Args:
            content: 用户输入内容
            
        Returns:
            InputAnalysisResult: 分析结果
        """
        try:
            # 1. 检测输入类型
            input_type = self._detect_input_type(content)
            
            # 2. 识别用户意图
            user_intent = self._identify_user_intent(content)
            
            # 3. 提取相关数据
            extracted_data = self._extract_data(content, input_type)
            
            # 4. 提取偏好设置
            extracted_preferences = self._extract_preferences(content)
            
            # 5. 计算置信度
            confidence = self._calculate_confidence(content, input_type, user_intent)
            
            # 6. 收集元数据
            metadata = self._collect_metadata(content, input_type)
            
            result = InputAnalysisResult(
                input_type=input_type,
                user_intent=user_intent,
                confidence=confidence,
                extracted_data=extracted_data,
                extracted_preferences=extracted_preferences,
                metadata=metadata
            )
            
            logger.info(f"输入分析完成: {input_type.value} - {user_intent.value} (置信度: {confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"输入分析失败: {e}")
            # 返回默认结果
            return InputAnalysisResult(
                input_type=InputType.TEXT,
                user_intent=UserIntent.CHAT,
                confidence=0.5,
                metadata={"error": str(e)}
            )
    
    def _detect_input_type(self, content: str) -> InputType:
        """检测输入类型"""
        # 检查是否包含URL
        urls = self.url_pattern.findall(content)
        has_url = len(urls) > 0
        
        # 检查是否包含base64图片数据
        has_image = self._detect_image_data(content)
        
        # 检查是否是纯文本但描述了图片
        describes_image = any(keyword in content.lower() for keyword in [
            "图片", "image", "截图", "screenshot", "照片", "photo"
        ])
        
        if has_url and has_image:
            return InputType.MIXED
        elif has_url:
            return InputType.URL
        elif has_image or describes_image:
            return InputType.IMAGE
        else:
            return InputType.TEXT
    
    def _detect_image_data(self, content: str) -> bool:
        """检测是否包含图片数据"""
        # 检查base64图片数据
        if "data:image/" in content:
            return True
        
        # 检查base64编码模式
        if len(content) > 100 and self._is_base64(content):
            return True
        
        return False
    
    def _is_base64(self, s: str) -> bool:
        """检查字符串是否为base64编码"""
        try:
            if len(s) % 4 != 0:
                return False
            base64.b64decode(s, validate=True)
            return True
        except Exception:
            return False
    
    def _identify_user_intent(self, content: str) -> UserIntent:
        """识别用户意图"""
        content_lower = content.lower()
        
        # 计算每个意图的匹配分数
        intent_scores = {}
        
        for intent, keywords in self.intent_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in content_lower:
                    score += 1
            intent_scores[intent] = score
        
        # 特殊规则
        # 如果包含URL，通常是想要分析或创建任务
        if self.url_pattern.search(content):
            if any(word in content_lower for word in ["创建", "create", "新建", "发布"]):
                return UserIntent.CREATE_TASK
            else:
                return UserIntent.ANALYZE_CONTENT
        
        # 如果包含偏好相关词汇
        if any(word in content_lower for word in ["设置", "配置", "偏好", "希望", "需要"]):
            return UserIntent.SET_PREFERENCES
        
        # 如果是问候或简单对话
        if any(word in content_lower for word in ["你好", "hello", "hi", "谢谢", "thank"]):
            return UserIntent.CHAT
        
        # 根据分数选择最高的意图
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            if intent_scores[best_intent] > 0:
                return best_intent
        
        # 默认为聊天
        return UserIntent.CHAT
    
    def _extract_data(self, content: str, input_type: InputType) -> Optional[Any]:
        """根据输入类型提取相关数据"""
        if input_type == InputType.URL:
            urls = self.url_pattern.findall(content)
            return urls[0] if urls else None
        
        elif input_type == InputType.IMAGE:
            # 提取图片数据
            if "data:image/" in content:
                # 提取data URL中的图片数据
                match = re.search(r'data:image/[^;]+;base64,([^"]+)', content)
                if match:
                    return match.group(1)
            
            # 如果是描述图片的文本，返回描述
            return content
        
        elif input_type == InputType.MIXED:
            # 提取URL和图片数据
            urls = self.url_pattern.findall(content)
            image_data = None
            
            if "data:image/" in content:
                match = re.search(r'data:image/[^;]+;base64,([^"]+)', content)
                if match:
                    image_data = match.group(1)
            
            return {
                "urls": urls,
                "image_data": image_data,
                "text": content
            }
        
        else:
            # 文本类型，返回清理后的内容
            return content.strip()
    
    def _extract_preferences(self, content: str) -> Optional[Dict[str, Any]]:
        """提取偏好设置"""
        content_lower = content.lower()
        preferences = {}
        
        # 检查输出格式偏好
        for format_keyword in self.preference_keywords["output_format"]:
            if format_keyword in content_lower:
                if format_keyword in ["json"]:
                    preferences["output_format"] = "JSON"
                elif format_keyword in ["markdown"]:
                    preferences["output_format"] = "MARKDOWN"
                elif format_keyword in ["结构化", "structured"]:
                    preferences["output_format"] = "STRUCTURED"
        
        # 检查语言偏好
        for lang_keyword in self.preference_keywords["language"]:
            if lang_keyword in content_lower:
                if lang_keyword in ["中文", "chinese"]:
                    preferences["language"] = "中文"
                elif lang_keyword in ["english", "英文"]:
                    preferences["language"] = "English"
        
        # 检查分析重点
        for focus_keyword in self.preference_keywords["analysis_focus"]:
            if focus_keyword in content_lower:
                if "analysis_focus" not in preferences:
                    preferences["analysis_focus"] = []
                
                if focus_keyword in ["技术", "technical"]:
                    preferences["analysis_focus"].append("TECHNICAL")
                elif focus_keyword in ["商业", "business"]:
                    preferences["analysis_focus"].append("BUSINESS")
                elif focus_keyword in ["时间", "timeline"]:
                    preferences["analysis_focus"].append("TIMELINE")
        
        # 检查质量阈值
        for quality_keyword in self.preference_keywords["quality_threshold"]:
            if quality_keyword in content_lower:
                preferences["quality_threshold"] = 0.8
        
        return preferences if preferences else None
    
    def _calculate_confidence(self, content: str, input_type: InputType, user_intent: UserIntent) -> float:
        """计算分析置信度"""
        confidence = 0.5  # 基础置信度
        
        # 根据输入类型调整置信度
        if input_type == InputType.URL:
            urls = self.url_pattern.findall(content)
            if urls and self._is_valid_url(urls[0]):
                confidence += 0.3
        
        elif input_type == InputType.IMAGE:
            if "data:image/" in content or self._detect_image_data(content):
                confidence += 0.3
        
        # 根据意图关键词匹配度调整置信度
        content_lower = content.lower()
        intent_keywords = self.intent_keywords.get(user_intent, [])
        
        matched_keywords = sum(1 for keyword in intent_keywords if keyword in content_lower)
        if matched_keywords > 0:
            confidence += min(0.2 * matched_keywords, 0.4)
        
        # 根据内容长度调整置信度
        if len(content.strip()) < 5:
            confidence -= 0.2
        elif len(content.strip()) > 100:
            confidence += 0.1
        
        return min(max(confidence, 0.0), 1.0)
    
    def _is_valid_url(self, url: str) -> bool:
        """验证URL是否有效"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _collect_metadata(self, content: str, input_type: InputType) -> Dict[str, Any]:
        """收集元数据"""
        metadata = {
            "content_length": len(content),
            "word_count": len(content.split()),
            "has_chinese": bool(re.search(r'[\u4e00-\u9fff]', content)),
            "has_english": bool(re.search(r'[a-zA-Z]', content))
        }
        
        if input_type == InputType.URL:
            urls = self.url_pattern.findall(content)
            if urls:
                metadata["url_count"] = len(urls)
                metadata["domains"] = list(set(urlparse(url).netloc for url in urls))
        
        elif input_type == InputType.IMAGE:
            metadata["has_image_data"] = "data:image/" in content
            metadata["possible_base64"] = self._detect_image_data(content)
        
        return metadata
    
    def detect_urls(self, text: str) -> List[str]:
        """检测文本中的URL"""
        return self.url_pattern.findall(text)
    
    def detect_images(self, content: Any) -> List[Dict[str, Any]]:
        """检测图片信息"""
        images = []
        
        if isinstance(content, str):
            # 检测data URL格式的图片
            data_url_pattern = r'data:image/([^;]+);base64,([^"]+)'
            matches = re.finditer(data_url_pattern, content)
            
            for match in matches:
                images.append({
                    "format": match.group(1),
                    "data": match.group(2),
                    "type": "base64"
                })
        
        return images
    
    def classify_intent(self, text: str) -> UserIntent:
        """分类用户意图（便捷方法）"""
        return self._identify_user_intent(text)
    
    def extract_preferences(self, text: str) -> Optional[Dict[str, Any]]:
        """提取用户偏好（便捷方法）"""
        return self._extract_preferences(text)