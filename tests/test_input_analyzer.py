"""
Tests for Input Analyzer
"""
import pytest
from unittest.mock import patch, MagicMock
import base64

from app.agent.input_analyzer import (
    InputAnalyzer, InputType, UserIntent, InputAnalysisResult
)


class TestInputAnalyzer:
    """Test Input Analyzer functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.analyzer = InputAnalyzer()
    
    @pytest.mark.asyncio
    async def test_analyze_url_input(self):
        """Test URL input analysis"""
        url_input = "Please analyze this URL: https://example.com/task"
        
        result = await self.analyzer.analyze_input(url_input)
        
        assert result.input_type == InputType.URL
        assert result.user_intent == UserIntent.ANALYZE_CONTENT
        assert result.extracted_data == "https://example.com/task"
        assert result.confidence > 0.5
        assert "url_count" in result.metadata
    
    @pytest.mark.asyncio
    async def test_analyze_create_task_url_input(self):
        """Test URL input with create task intent"""
        url_input = "创建任务 https://github.com/user/repo"
        
        result = await self.analyzer.analyze_input(url_input)
        
        assert result.input_type == InputType.URL
        assert result.user_intent == UserIntent.CREATE_TASK
        assert result.extracted_data == "https://github.com/user/repo"
        assert result.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_analyze_image_data_input(self):
        """Test image data input analysis"""
        image_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        result = await self.analyzer.analyze_input(image_data)
        
        assert result.input_type == InputType.IMAGE
        assert result.user_intent == UserIntent.ANALYZE_CONTENT
        assert result.extracted_data is not None
        assert result.metadata["has_image_data"] is True
    
    @pytest.mark.asyncio
    async def test_analyze_text_input(self):
        """Test plain text input analysis"""
        text_input = "Hello, how are you?"
        
        result = await self.analyzer.analyze_input(text_input)
        
        assert result.input_type == InputType.TEXT
        assert result.user_intent == UserIntent.CHAT
        assert result.extracted_data == text_input
        assert result.confidence >= 0.5
    
    @pytest.mark.asyncio
    async def test_analyze_preference_setting_input(self):
        """Test preference setting input analysis"""
        pref_input = "设置输出格式为JSON，语言为中文"
        
        result = await self.analyzer.analyze_input(pref_input)
        
        assert result.input_type == InputType.TEXT
        assert result.user_intent == UserIntent.SET_PREFERENCES
        assert result.extracted_preferences is not None
        assert result.extracted_preferences["output_format"] == "JSON"
        assert result.extracted_preferences["language"] == "中文"
    
    @pytest.mark.asyncio
    async def test_analyze_mixed_input(self):
        """Test mixed content input analysis"""
        mixed_input = "分析这个URL https://example.com 和这张图片 data:image/png;base64,test"
        
        result = await self.analyzer.analyze_input(mixed_input)
        
        assert result.input_type == InputType.MIXED
        assert result.user_intent == UserIntent.ANALYZE_CONTENT
        assert isinstance(result.extracted_data, dict)
        assert "urls" in result.extracted_data
        assert "image_data" in result.extracted_data
    
    @pytest.mark.asyncio
    async def test_analyze_help_input(self):
        """Test help request input analysis"""
        help_input = "怎么使用这个系统？"
        
        result = await self.analyzer.analyze_input(help_input)
        
        assert result.input_type == InputType.TEXT
        assert result.user_intent == UserIntent.HELP
        assert result.extracted_data == help_input
    
    @pytest.mark.asyncio
    async def test_analyze_status_input(self):
        """Test status request input analysis"""
        status_input = "系统状态如何？"
        
        result = await self.analyzer.analyze_input(status_input)
        
        assert result.input_type == InputType.TEXT
        assert result.user_intent == UserIntent.GET_STATUS
        assert result.extracted_data == status_input
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in input analysis"""
        # Mock an exception in _detect_input_type
        with patch.object(self.analyzer, '_detect_input_type', side_effect=Exception("Test error")):
            result = await self.analyzer.analyze_input("test input")
            
            assert result.input_type == InputType.TEXT
            assert result.user_intent == UserIntent.CHAT
            assert result.confidence == 0.5
            assert "error" in result.metadata
    
    def test_detect_input_type_url(self):
        """Test URL input type detection"""
        url_content = "Check this out: https://example.com/path?param=value"
        
        input_type = self.analyzer._detect_input_type(url_content)
        
        assert input_type == InputType.URL
    
    def test_detect_input_type_image(self):
        """Test image input type detection"""
        image_content = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD"
        
        input_type = self.analyzer._detect_input_type(image_content)
        
        assert input_type == InputType.IMAGE
    
    def test_detect_input_type_mixed(self):
        """Test mixed input type detection"""
        mixed_content = "URL: https://example.com and image: data:image/png;base64,test"
        
        input_type = self.analyzer._detect_input_type(mixed_content)
        
        assert input_type == InputType.MIXED
    
    def test_detect_input_type_text(self):
        """Test text input type detection"""
        text_content = "This is just plain text without URLs or images"
        
        input_type = self.analyzer._detect_input_type(text_content)
        
        assert input_type == InputType.TEXT
    
    def test_identify_user_intent_create_task(self):
        """Test create task intent identification"""
        create_inputs = [
            "创建任务 https://example.com",
            "create task from this URL",
            "新建任务",
            "发布任务"
        ]
        
        for input_text in create_inputs:
            intent = self.analyzer._identify_user_intent(input_text)
            assert intent == UserIntent.CREATE_TASK
    
    def test_identify_user_intent_analyze(self):
        """Test analyze intent identification"""
        analyze_inputs = [
            "分析这个内容",
            "analyze this URL",
            "解析图片",
            "提取信息"
        ]
        
        for input_text in analyze_inputs:
            intent = self.analyzer._identify_user_intent(input_text)
            assert intent == UserIntent.ANALYZE_CONTENT
    
    def test_identify_user_intent_preferences(self):
        """Test preferences intent identification"""
        pref_inputs = [
            "设置输出格式",
            "配置语言偏好",
            "我希望使用JSON格式",
            "我需要中文输出"
        ]
        
        for input_text in pref_inputs:
            intent = self.analyzer._identify_user_intent(input_text)
            assert intent == UserIntent.SET_PREFERENCES
    
    def test_identify_user_intent_chat(self):
        """Test chat intent identification"""
        chat_inputs = [
            "你好",
            "hello",
            "谢谢",
            "thank you"
        ]
        
        for input_text in chat_inputs:
            intent = self.analyzer._identify_user_intent(input_text)
            assert intent == UserIntent.CHAT
    
    def test_extract_data_url(self):
        """Test URL data extraction"""
        url_content = "Please check https://example.com/path"
        
        data = self.analyzer._extract_data(url_content, InputType.URL)
        
        assert data == "https://example.com/path"
    
    def test_extract_data_image(self):
        """Test image data extraction"""
        image_content = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        data = self.analyzer._extract_data(image_content, InputType.IMAGE)
        
        assert data == "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    def test_extract_data_mixed(self):
        """Test mixed data extraction"""
        mixed_content = "URL: https://example.com and image: data:image/png;base64,test"
        
        data = self.analyzer._extract_data(mixed_content, InputType.MIXED)
        
        assert isinstance(data, dict)
        assert "urls" in data
        assert "image_data" in data
        assert "text" in data
        assert data["urls"] == ["https://example.com"]
    
    def test_extract_preferences_output_format(self):
        """Test output format preference extraction"""
        pref_inputs = [
            ("使用JSON格式", {"output_format": "JSON"}),
            ("输出markdown", {"output_format": "MARKDOWN"}),
            ("结构化输出", {"output_format": "STRUCTURED"})
        ]
        
        for input_text, expected in pref_inputs:
            prefs = self.analyzer._extract_preferences(input_text)
            assert prefs == expected
    
    def test_extract_preferences_language(self):
        """Test language preference extraction"""
        pref_inputs = [
            ("使用中文", {"language": "中文"}),
            ("english output", {"language": "English"}),
            ("chinese language", {"language": "中文"})
        ]
        
        for input_text, expected in pref_inputs:
            prefs = self.analyzer._extract_preferences(input_text)
            assert prefs == expected
    
    def test_extract_preferences_analysis_focus(self):
        """Test analysis focus preference extraction"""
        input_text = "重点关注技术和商业方面"
        
        prefs = self.analyzer._extract_preferences(input_text)
        
        assert "analysis_focus" in prefs
        assert "TECHNICAL" in prefs["analysis_focus"]
        assert "BUSINESS" in prefs["analysis_focus"]
    
    def test_extract_preferences_quality_threshold(self):
        """Test quality threshold preference extraction"""
        input_text = "需要高质量的结果"
        
        prefs = self.analyzer._extract_preferences(input_text)
        
        assert prefs["quality_threshold"] == 0.8
    
    def test_calculate_confidence_url(self):
        """Test confidence calculation for URL input"""
        url_content = "https://valid-url.com/path"
        
        confidence = self.analyzer._calculate_confidence(
            url_content, InputType.URL, UserIntent.ANALYZE_CONTENT
        )
        
        assert confidence > 0.7  # Should be high for valid URL
    
    def test_calculate_confidence_short_text(self):
        """Test confidence calculation for short text"""
        short_text = "hi"
        
        confidence = self.analyzer._calculate_confidence(
            short_text, InputType.TEXT, UserIntent.CHAT
        )
        
        assert confidence < 0.5  # Should be lower for very short text
    
    def test_calculate_confidence_long_text(self):
        """Test confidence calculation for long text"""
        long_text = "This is a much longer text that should have higher confidence because it provides more context and information for analysis."
        
        confidence = self.analyzer._calculate_confidence(
            long_text, InputType.TEXT, UserIntent.ANALYZE_CONTENT
        )
        
        assert confidence > 0.6  # Should be higher for longer text
    
    def test_is_valid_url(self):
        """Test URL validation"""
        valid_urls = [
            "https://example.com",
            "http://test.org/path",
            "https://subdomain.example.com/path?param=value"
        ]
        
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Different scheme
            "https://",  # Missing netloc
            ""
        ]
        
        for url in valid_urls:
            assert self.analyzer._is_valid_url(url), f"Should be valid: {url}"
        
        for url in invalid_urls:
            assert not self.analyzer._is_valid_url(url), f"Should be invalid: {url}"
    
    def test_is_base64(self):
        """Test base64 detection"""
        # Valid base64
        valid_base64 = base64.b64encode(b"test data").decode()
        assert self.analyzer._is_base64(valid_base64)
        
        # Invalid base64
        invalid_base64 = "not-base64-data!"
        assert not self.analyzer._is_base64(invalid_base64)
        
        # Wrong length
        wrong_length = "abc"
        assert not self.analyzer._is_base64(wrong_length)
    
    def test_detect_image_data(self):
        """Test image data detection"""
        # Data URL format
        data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        assert self.analyzer._detect_image_data(data_url)
        
        # Plain text
        plain_text = "This is just text"
        assert not self.analyzer._detect_image_data(plain_text)
    
    def test_collect_metadata(self):
        """Test metadata collection"""
        content = "这是一个包含中文和English的测试内容"
        
        metadata = self.analyzer._collect_metadata(content, InputType.TEXT)
        
        assert "content_length" in metadata
        assert "word_count" in metadata
        assert metadata["has_chinese"] is True
        assert metadata["has_english"] is True
        assert metadata["content_length"] == len(content)
    
    def test_collect_metadata_url(self):
        """Test metadata collection for URL input"""
        url_content = "Check https://example.com and https://test.org"
        
        metadata = self.analyzer._collect_metadata(url_content, InputType.URL)
        
        assert "url_count" in metadata
        assert "domains" in metadata
        assert metadata["url_count"] == 2
        assert "example.com" in metadata["domains"]
        assert "test.org" in metadata["domains"]
    
    def test_collect_metadata_image(self):
        """Test metadata collection for image input"""
        image_content = "data:image/png;base64,test"
        
        metadata = self.analyzer._collect_metadata(image_content, InputType.IMAGE)
        
        assert "has_image_data" in metadata
        assert "possible_base64" in metadata
        assert metadata["has_image_data"] is True
    
    def test_detect_urls_convenience_method(self):
        """Test detect_urls convenience method"""
        text = "Visit https://example.com and http://test.org for more info"
        
        urls = self.analyzer.detect_urls(text)
        
        assert len(urls) == 2
        assert "https://example.com" in urls
        assert "http://test.org" in urls
    
    def test_detect_images_convenience_method(self):
        """Test detect_images convenience method"""
        content = "Image: data:image/jpeg;base64,/9j/test and data:image/png;base64,png_test"
        
        images = self.analyzer.detect_images(content)
        
        assert len(images) == 2
        assert images[0]["format"] == "jpeg"
        assert images[0]["data"] == "/9j/test"
        assert images[1]["format"] == "png"
        assert images[1]["data"] == "png_test"
    
    def test_classify_intent_convenience_method(self):
        """Test classify_intent convenience method"""
        text = "创建新任务"
        
        intent = self.analyzer.classify_intent(text)
        
        assert intent == UserIntent.CREATE_TASK
    
    def test_extract_preferences_convenience_method(self):
        """Test extract_preferences convenience method"""
        text = "设置为JSON格式"
        
        prefs = self.analyzer.extract_preferences(text)
        
        assert prefs["output_format"] == "JSON"


class TestInputAnalysisResult:
    """Test InputAnalysisResult data class"""
    
    def test_input_analysis_result_creation(self):
        """Test InputAnalysisResult creation"""
        result = InputAnalysisResult(
            input_type=InputType.URL,
            user_intent=UserIntent.CREATE_TASK,
            confidence=0.8,
            extracted_data="https://example.com",
            extracted_preferences={"format": "JSON"}
        )
        
        assert result.input_type == InputType.URL
        assert result.user_intent == UserIntent.CREATE_TASK
        assert result.confidence == 0.8
        assert result.extracted_data == "https://example.com"
        assert result.extracted_preferences["format"] == "JSON"
        assert result.metadata == {}  # Should be initialized to empty dict
    
    def test_input_analysis_result_with_metadata(self):
        """Test InputAnalysisResult with metadata"""
        metadata = {"test_key": "test_value"}
        
        result = InputAnalysisResult(
            input_type=InputType.TEXT,
            user_intent=UserIntent.CHAT,
            confidence=0.5,
            metadata=metadata
        )
        
        assert result.metadata == metadata