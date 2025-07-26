"""
Tests for ContentExtractor functionality.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import aiohttp

from app.agent.content_extractor import ContentExtractor
from app.agent.models import WebContent
from app.agent.exceptions import URLValidationError, ContentExtractionError


class TestContentExtractor:
    """ContentExtractor测试类"""
    
    def setup_method(self):
        """设置测试方法"""
        self.extractor = ContentExtractor(
            timeout=10,
            max_content_length=1000,
            user_agent="TestAgent/1.0"
        )
    
    def test_init(self):
        """测试初始化"""
        assert self.extractor.timeout == 10
        assert self.extractor.max_content_length == 1000
        assert self.extractor.user_agent == "TestAgent/1.0"
        assert 'http' in self.extractor.allowed_schemes
        assert 'https' in self.extractor.allowed_schemes
    
    def test_validate_url_valid_http(self):
        """测试有效的HTTP URL验证"""
        url = "http://example.com/page"
        result = self.extractor.validate_url(url)
        assert result == url
    
    def test_validate_url_valid_https(self):
        """测试有效的HTTPS URL验证"""
        url = "https://example.com/page"
        result = self.extractor.validate_url(url)
        assert result == url
    
    def test_validate_url_invalid_scheme(self):
        """测试无效协议的URL"""
        with pytest.raises(URLValidationError) as exc_info:
            self.extractor.validate_url("ftp://example.com")
        assert "不支持的协议" in str(exc_info.value)
    
    def test_validate_url_no_domain(self):
        """测试缺少域名的URL"""
        with pytest.raises(URLValidationError) as exc_info:
            self.extractor.validate_url("http://")
        assert "缺少域名" in str(exc_info.value)
    
    def test_validate_url_localhost_blocked(self):
        """测试本地地址被阻止"""
        with pytest.raises(URLValidationError) as exc_info:
            self.extractor.validate_url("http://localhost:8000")
        assert "内网地址" in str(exc_info.value)
    
    def test_validate_url_private_ip_blocked(self):
        """测试私有IP地址被阻止"""
        private_ips = [
            "http://127.0.0.1:8000",
            "http://192.168.1.1",
            "http://10.0.0.1",
            "http://172.16.0.1"
        ]
        
        for ip in private_ips:
            with pytest.raises(URLValidationError) as exc_info:
                self.extractor.validate_url(ip)
            assert "内网地址" in str(exc_info.value)
    
    def test_clean_content_basic(self):
        """测试基本内容清理"""
        html = """
        <html>
            <head><title>Test</title></head>
            <body>
                <script>alert('test');</script>
                <style>.test { color: red; }</style>
                <h1>Main Title</h1>
                <p>This is a paragraph with useful content.</p>
                <nav>Navigation menu</nav>
                <footer>Footer content</footer>
            </body>
        </html>
        """
        
        result = self.extractor.clean_content(html)
        
        # 应该包含有用内容
        assert "Main Title" in result
        assert "This is a paragraph with useful content." in result
        
        # 不应该包含脚本、样式、导航等
        assert "alert('test')" not in result
        assert "color: red" not in result
        assert "Navigation menu" not in result
        assert "Footer content" not in result
    
    def test_clean_content_with_lists(self):
        """测试包含列表的内容清理"""
        html = """
        <html>
            <body>
                <h1>Task Requirements</h1>
                <ul>
                    <li>Requirement 1: Build a web scraper</li>
                    <li>Requirement 2: Extract structured data</li>
                    <li>Requirement 3: Handle errors gracefully</li>
                </ul>
                <p>Additional details about the task.</p>
            </body>
        </html>
        """
        
        result = self.extractor.clean_content(html)
        
        assert "标题: Task Requirements" in result
        assert "• Requirement 1: Build a web scraper" in result
        assert "• Requirement 2: Extract structured data" in result
        assert "Additional details about the task." in result
    
    def test_extract_meta_description(self):
        """测试meta描述提取"""
        html = """
        <html>
            <head>
                <meta name="description" content="This is a test description">
                <meta property="og:description" content="OpenGraph description">
            </head>
            <body>Content</body>
        </html>
        """
        
        result = self.extractor.extract_meta_description(html)
        assert result == "This is a test description"
    
    def test_extract_meta_description_og_fallback(self):
        """测试OpenGraph描述作为后备"""
        html = """
        <html>
            <head>
                <meta property="og:description" content="OpenGraph description">
            </head>
            <body>Content</body>
        </html>
        """
        
        result = self.extractor.extract_meta_description(html)
        assert result == "OpenGraph description"
    
    def test_extract_meta_description_none(self):
        """测试没有meta描述的情况"""
        html = """
        <html>
            <head><title>Test</title></head>
            <body>Content</body>
        </html>
        """
        
        result = self.extractor.extract_meta_description(html)
        assert result is None
    
    def test_extract_additional_metadata(self):
        """测试额外元数据提取"""
        html = """
        <html lang="en">
            <head>
                <meta name="keywords" content="web scraping, python, automation">
                <meta name="author" content="John Doe">
                <meta property="article:published_time" content="2023-01-01T00:00:00Z">
                <meta property="og:image" content="https://example.com/image.jpg">
            </head>
            <body>Content</body>
        </html>
        """
        
        result = self.extractor.extract_additional_metadata(html)
        
        assert result['keywords'] == "web scraping, python, automation"
        assert result['author'] == "John Doe"
        assert result['published_time'] == "2023-01-01T00:00:00Z"
        assert result['language'] == "en"
        assert result['image_url'] == "https://example.com/image.jpg"
    
    def test_is_navigation_line(self):
        """测试导航行识别"""
        # 应该被识别为导航的行
        nav_lines = [
            "首页 | 登录 | 注册 | 帮助",
            "Home > About > Contact",
            "Menu: Home · Products · Services · Contact"
        ]
        
        for line in nav_lines:
            assert self.extractor._is_navigation_line(line)
        
        # 不应该被识别为导航的行
        content_lines = [
            "This is a normal paragraph with useful content.",
            "The task requires building a web scraper using Python.",
            "Reward: $500 for completing this project."
        ]
        
        for line in content_lines:
            assert not self.extractor._is_navigation_line(line)
    
    def test_truncate_content_no_truncation(self):
        """测试不需要截断的内容"""
        content = "Short content"
        result = self.extractor.truncate_content(content, max_length=100)
        assert result == content
    
    def test_truncate_content_sentence_boundary(self):
        """测试在句子边界截断"""
        content = "This is the first sentence. This is the second sentence. This is a very long third sentence that should be truncated."
        result = self.extractor.truncate_content(content, max_length=60)
        
        # 应该在第二个句子后截断
        assert result.endswith("This is the second sentence....")
    
    def test_truncate_content_word_boundary(self):
        """测试在词边界截断"""
        content = "This is a very long sentence without proper punctuation that needs to be truncated at word boundaries"
        result = self.extractor.truncate_content(content, max_length=50)
        
        # 应该在词边界截断并添加省略号
        assert result.endswith("...")
        assert not result.endswith(" ...")  # 不应该以空格+省略号结尾
    
    @pytest.mark.asyncio
    async def test_extract_content_success(self):
        """测试成功提取内容"""
        test_html = """
        <html>
            <head>
                <title>Test Page</title>
                <meta name="description" content="Test description">
            </head>
            <body>
                <h1>Main Title</h1>
                <p>This is the main content of the page.</p>
            </body>
        </html>
        """
        
        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'content-type': 'text/html; charset=utf-8'}
        mock_response.text = AsyncMock(return_value=test_html)
        
        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await self.extractor.extract_content("https://example.com")
        
        assert isinstance(result, WebContent)
        assert result.url == "https://example.com"
        assert result.title == "Test Page"
        assert "Main Title" in result.content
        assert "This is the main content of the page." in result.content
        assert result.meta_description == "Test description"
        assert isinstance(result.extracted_at, datetime)
    
    @pytest.mark.asyncio
    async def test_extract_content_http_error(self):
        """测试HTTP错误处理"""
        mock_response = AsyncMock()
        mock_response.status = 404
        
        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(ContentExtractionError) as exc_info:
                await self.extractor.extract_content("https://example.com/notfound")
        
        assert "HTTP错误: 404" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_extract_content_wrong_content_type(self):
        """测试错误的内容类型"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'content-type': 'application/json'}
        
        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(ContentExtractionError) as exc_info:
                await self.extractor.extract_content("https://example.com/api")
        
        assert "不支持的内容类型" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_extract_content_network_error(self):
        """测试网络错误处理"""
        mock_session = AsyncMock()
        mock_session.get.side_effect = aiohttp.ClientError("Connection failed")
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(ContentExtractionError) as exc_info:
                await self.extractor.extract_content("https://example.com")
        
        assert "网络请求失败" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_extract_content_timeout(self):
        """测试超时处理"""
        mock_session = AsyncMock()
        mock_session.get.side_effect = asyncio.TimeoutError()
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(ContentExtractionError) as exc_info:
                await self.extractor.extract_content("https://example.com")
        
        assert "请求超时" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_extract_content_long_content_truncation(self):
        """测试长内容截断"""
        # 创建超长的HTML内容
        long_content = "Very long content. " * 1000
        test_html = f"""
        <html>
            <head><title>Long Page</title></head>
            <body>
                <h1>Title</h1>
                <p>{long_content}</p>
            </body>
        </html>
        """
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.text = AsyncMock(return_value=test_html)
        
        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_session
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await self.extractor.extract_content("https://example.com")
        
        # 内容应该被截断
        assert len(result.content) <= self.extractor.max_content_length + 3  # +3 for "..."
        assert result.content.endswith("...")
    
    def test_advanced_text_cleaning(self):
        """测试高级文本清理"""
        text = """
        This is a good sentence.
        
        
        This is another good sentence!!!
        
        Short
        
        点击这里了解更多信息
        
        Copyright 2023 All rights reserved
        
        This is a meaningful paragraph with enough content to be preserved.
        """
        
        result = self.extractor._advanced_text_cleaning(text)
        
        # 应该保留有意义的内容
        assert "This is a good sentence." in result
        assert "This is another good sentence!" in result  # 多个感叹号应该被清理
        assert "This is a meaningful paragraph" in result
        
        # 应该移除无用内容
        assert "Short" not in result  # 太短的行
        assert "点击这里了解更多" not in result  # 无用模式
        assert "Copyright 2023" not in result  # 版权信息
    
    def test_extract_structured_content(self):
        """测试结构化内容提取"""
        from bs4 import BeautifulSoup
        
        html = """
        <h1>Main Project Title</h1>
        <h2>Requirements</h2>
        <h3>Technical Skills</h3>
        <ul>
            <li>Python programming experience</li>
            <li>Web scraping knowledge</li>
            <li>Database design skills</li>
        </ul>
        <ol>
            <li>First step in process</li>
            <li>Second step in process</li>
        </ol>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        result = self.extractor._extract_structured_content(soup)
        
        assert "标题: Main Project Title" in result
        assert "- Requirements" in result
        assert "- Technical Skills" in result
        assert "• Python programming experience" in result
        assert "• First step in process" in result


class TestContentExtractorIntegration:
    """ContentExtractor集成测试"""
    
    def setup_method(self):
        """设置测试方法"""
        self.extractor = ContentExtractor()
    
    @pytest.mark.asyncio
    async def test_real_url_extraction(self):
        """测试真实URL提取（需要网络连接）"""
        # 注意：现在主要使用PlaywrightContentExtractor进行复杂网站的内容提取
        # 这个测试需要真实的网络连接，在CI环境中可能需要跳过
        pytest.skip("需要网络连接的集成测试，主要功能已转移到PlaywrightContentExtractor")
        
        try:
            result = await self.extractor.extract_content("https://httpbin.org/html")
            assert isinstance(result, WebContent)
            assert result.url == "https://httpbin.org/html"
            assert len(result.content) > 0
            assert result.title
        except Exception as e:
            pytest.skip(f"网络连接问题: {e}")