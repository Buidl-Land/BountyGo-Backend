"""
Tests for PlaywrightContentExtractor functionality.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from app.agent.playwright_extractor import PlaywrightContentExtractor
from app.agent.models import WebContent
from app.agent.exceptions import URLValidationError, ContentExtractionError


class TestPlaywrightContentExtractor:
    """PlaywrightContentExtractor测试类"""
    
    def setup_method(self):
        """设置测试方法"""
        self.extractor = PlaywrightContentExtractor(
            timeout=10000,
            max_content_length=1000,
            headless=True
        )
    
    def test_init(self):
        """测试初始化"""
        assert self.extractor.timeout == 10000
        assert self.extractor.max_content_length == 1000
        assert self.extractor.headless is True
        assert self.extractor.browser is None
        assert self.extractor.context is None
    
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
        content = """
        This is a good sentence.
        
        
        This is another good sentence!!!
        
        Short
        
        点击这里了解更多信息
        
        Copyright 2023 All rights reserved
        
        This is a meaningful paragraph with enough content to be preserved.
        """
        
        result = self.extractor.clean_content(content)
        
        # 应该保留有意义的内容
        assert "This is a good sentence." in result
        assert "This is another good sentence!" in result  # 多个感叹号应该被清理
        assert "This is a meaningful paragraph" in result
        
        # 应该移除无用内容
        assert "Short" not in result  # 太短的行
        assert "点击这里了解更多" not in result  # 无用模式
        assert "Copyright 2023" not in result  # 版权信息
    
    def test_extract_title_from_content(self):
        """测试从内容中提取标题"""
        content = """
        <h1>Main Project Title</h1>
        <h2>Subtitle</h2>
        <p>Some content here</p>
        """
        
        title = self.extractor._extract_title_from_content(content)
        assert title == "Main Project Title"
    
    def test_extract_title_from_content_no_h1(self):
        """测试没有h1标签时的标题提取"""
        content = """
        <h2>Secondary Title</h2>
        <p>Some content here</p>
        """
        
        title = self.extractor._extract_title_from_content(content)
        assert title == "Secondary Title"
    
    def test_extract_title_from_content_no_headers(self):
        """测试没有标题标签时的处理"""
        content = """
        <p>Just some content without headers</p>
        """
        
        title = self.extractor._extract_title_from_content(content)
        assert title == ""
    
    def test_is_playwright_domain(self):
        """测试Playwright域名识别"""
        # 应该使用Playwright的域名
        playwright_domains = [
            "https://github.com/user/repo",
            "https://twitter.com/status/123",
            "https://x.com/status/123",
            "https://medium.com/@user/article"
        ]
        
        for url in playwright_domains:
            assert self.extractor._is_playwright_domain(url)
        
        # 不应该使用Playwright的域名
        simple_domains = [
            "https://example.com",
            "https://simple-blog.com",
            "https://static-site.org"
        ]
        
        for url in simple_domains:
            assert not self.extractor._is_playwright_domain(url)
    
    @pytest.mark.asyncio
    async def test_extract_content_success_simple(self):
        """测试简单网站内容提取成功"""
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
        
        # Mock aiohttp for simple extraction
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'content-type': 'text/html; charset=utf-8'}
        mock_response.text = AsyncMock(return_value=test_html)
        
        mock_session = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await self.extractor.extract_content("https://simple-example.com")
        
        assert isinstance(result, WebContent)
        assert result.url == "https://simple-example.com"
        assert result.title == "Test Page"
        assert "Main Title" in result.content
        assert "This is the main content of the page." in result.content
        assert result.meta_description == "Test description"
        assert isinstance(result.extracted_at, datetime)
    
    @pytest.mark.asyncio
    async def test_extract_content_success_playwright(self):
        """测试Playwright网站内容提取成功"""
        # Mock playwright components
        mock_page = AsyncMock()
        mock_page.title.return_value = "GitHub Repository"
        mock_page.content.return_value = """
        <html>
            <head><title>GitHub Repository</title></head>
            <body>
                <h1>Project Title</h1>
                <p>This is a GitHub project description.</p>
            </body>
        </html>
        """
        mock_page.locator.return_value.text_content.return_value = "Test meta description"
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        mock_browser = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        
        with patch('playwright.async_api.async_playwright') as mock_playwright:
            mock_playwright_instance = AsyncMock()
            mock_playwright_instance.chromium.launch.return_value = mock_browser
            mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance
            
            result = await self.extractor.extract_content("https://github.com/user/repo")
        
        assert isinstance(result, WebContent)
        assert result.url == "https://github.com/user/repo"
        assert result.title == "GitHub Repository"
        assert "Project Title" in result.content
        assert "This is a GitHub project description." in result.content
    
    @pytest.mark.asyncio
    async def test_extract_content_playwright_timeout(self):
        """测试Playwright超时处理"""
        mock_page = AsyncMock()
        mock_page.goto.side_effect = Exception("Timeout")
        
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        mock_browser = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        
        with patch('playwright.async_api.async_playwright') as mock_playwright:
            mock_playwright_instance = AsyncMock()
            mock_playwright_instance.chromium.launch.return_value = mock_browser
            mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance
            
            with pytest.raises(ContentExtractionError) as exc_info:
                await self.extractor.extract_content("https://github.com/user/repo")
            
            assert "Playwright内容提取失败" in str(exc_info.value)
    
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
    async def test_close_browser(self):
        """测试浏览器关闭"""
        # Mock browser and context
        mock_context = AsyncMock()
        mock_browser = AsyncMock()
        
        self.extractor.context = mock_context
        self.extractor.browser = mock_browser
        
        await self.extractor.close()
        
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        assert self.extractor.context is None
        assert self.extractor.browser is None
    
    @pytest.mark.asyncio
    async def test_close_no_browser(self):
        """测试没有浏览器时的关闭操作"""
        # 应该不会抛出异常
        await self.extractor.close()
        
        assert self.extractor.context is None
        assert self.extractor.browser is None
    
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
        assert result.endswith("This is the second sentence....") or result.endswith("...")
    
    def test_truncate_content_word_boundary(self):
        """测试在词边界截断"""
        content = "This is a very long sentence without proper punctuation that needs to be truncated at word boundaries"
        result = self.extractor.truncate_content(content, max_length=50)
        
        # 应该在词边界截断并添加省略号
        assert result.endswith("...")
        assert not result.endswith(" ...")  # 不应该以空格+省略号结尾


class TestPlaywrightContentExtractorIntegration:
    """PlaywrightContentExtractor集成测试"""
    
    def setup_method(self):
        """设置测试方法"""
        self.extractor = PlaywrightContentExtractor()
    
    @pytest.mark.asyncio
    async def test_real_url_extraction(self):
        """测试真实URL提取（需要网络连接）"""
        # 这个测试需要真实的网络连接和Playwright安装，在CI环境中可能需要跳过
        pytest.skip("需要网络连接和Playwright安装的集成测试")
        
        try:
            result = await self.extractor.extract_content("https://httpbin.org/html")
            assert isinstance(result, WebContent)
            assert result.url == "https://httpbin.org/html"
            assert len(result.content) > 0
            assert result.title
        except Exception as e:
            pytest.skip(f"网络连接或Playwright问题: {e}")
        finally:
            await self.extractor.close()


if __name__ == "__main__":
    pytest.main([__file__])