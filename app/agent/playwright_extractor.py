"""
Playwright-based content extraction for handling anti-bot websites.
"""
import asyncio
import re
import urllib.parse
from datetime import datetime
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from bs4 import BeautifulSoup
from readability.readability import Document

from .models import WebContent
from .exceptions import URLValidationError, ContentExtractionError


class PlaywrightContentExtractor:
    """基于Playwright的网页内容提取器，可以处理JavaScript渲染和反爬机制"""
    
    def __init__(self, 
                 timeout: int = 30,
                 max_content_length: int = 50000,
                 user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                 headless: bool = True,
                 wait_for_selector: Optional[str] = None,
                 wait_time: int = 3):
        """
        初始化Playwright内容提取器
        
        Args:
            timeout: 页面加载超时时间(秒)
            max_content_length: 最大内容长度
            user_agent: 用户代理字符串
            headless: 是否使用无头模式
            wait_for_selector: 等待特定选择器出现
            wait_time: 页面加载后等待时间(秒)
        """
        self.timeout = timeout * 1000  # Playwright使用毫秒
        self.max_content_length = max_content_length
        self.user_agent = user_agent
        self.headless = headless
        self.wait_for_selector = wait_for_selector
        self.wait_time = wait_time * 1000  # 转换为毫秒
        
        # 安全的URL模式
        self.allowed_schemes = {'http', 'https'}
        self.blocked_domains = {
            'localhost', '127.0.0.1', '0.0.0.0',
            '10.', '172.16.', '192.168.'  # 内网地址前缀
        }
        
        # 浏览器实例缓存
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
    
    def validate_url(self, url: str) -> str:
        """
        验证URL的安全性和有效性
        
        Args:
            url: 要验证的URL
            
        Returns:
            str: 标准化的URL
            
        Raises:
            URLValidationError: URL验证失败
        """
        try:
            # 解析URL
            parsed = urllib.parse.urlparse(url)
            
            # 检查协议
            if parsed.scheme not in self.allowed_schemes:
                raise URLValidationError(
                    f"不支持的协议: {parsed.scheme}",
                    details=f"仅支持: {', '.join(self.allowed_schemes)}"
                )
            
            # 检查域名
            if not parsed.netloc:
                raise URLValidationError("无效的URL: 缺少域名")
            
            # 检查是否为内网地址
            hostname = parsed.hostname
            if hostname:
                hostname_lower = hostname.lower()
                for blocked in self.blocked_domains:
                    if hostname_lower.startswith(blocked):
                        raise URLValidationError(
                            f"不允许访问内网地址: {hostname}",
                            details="出于安全考虑，禁止访问内网地址"
                        )
            
            # 返回标准化的URL
            return urllib.parse.urlunparse(parsed)
            
        except ValueError as e:
            raise URLValidationError(f"URL解析失败: {str(e)}")
    
    async def _get_browser_context(self) -> tuple[Browser, BrowserContext]:
        """获取浏览器和上下文实例"""
        if self._browser is None or self._context is None:
            playwright = await async_playwright().start()
            
            # 启动浏览器 - 增强反爬虫能力
            self._browser = await playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                    '--ignore-ssl-errors',
                    '--ignore-certificate-errors',
                    '--ignore-certificate-errors-spki-list',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-web-security',
                    '--aggressive-cache-discard',
                    # 增强反爬虫检测规避
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=VizDisplayCompositor,VizServiceDisplay',
                    '--disable-ipc-flooding-protection',
                    '--disable-extensions-file-access-check',
                    '--disable-extensions-http-throttling'
                ]
            )
            
            # 创建上下文 - 增强反检测
            self._context = await self._browser.new_context(
                user_agent=self.user_agent,
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                # 模拟真实浏览器行为
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                },
                # 伪装特征
                ignore_https_errors=True,
                java_script_enabled=True,
                permissions=['geolocation', 'notifications']
            )
            
            # 添加反检测脚本
            await self._context.add_init_script("""
                // 移除webdriver痕迹
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                
                // 伪装chrome对象
                window.chrome = { runtime: {} };
                
                // 伪装plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // 伪装languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en']
                });
                
                // 移除自动化痕迹
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """)
            
            # 设置默认超时
            self._context.set_default_timeout(self.timeout)
            self._context.set_default_navigation_timeout(self.timeout)
        
        return self._browser, self._context
    
    async def extract_content(self, url: str) -> WebContent:
        """
        使用Playwright提取网页内容
        
        Args:
            url: 要提取的URL
            
        Returns:
            WebContent: 提取的网页内容
            
        Raises:
            URLValidationError: URL验证失败
            ContentExtractionError: 内容提取失败
        """
        # 验证URL
        validated_url = self.validate_url(url)
        
        try:
            # 获取浏览器实例
            browser, context = await self._get_browser_context()
            
            # 创建新页面
            page = await context.new_page()
            
            try:
                # 设置页面事件监听
                await self._setup_page_listeners(page)
                
                # 导航到页面 - 渐进式等待策略
                print(f"🌐 正在访问: {validated_url}")
                response = None
                
                # 尝试不同的等待策略，从最宽松开始
                wait_strategies = [
                    ('commit', 8000),      # 只等待导航提交
                    ('domcontentloaded', 12000),  # 等待DOM内容
                    ('load', 20000)        # 完全加载（最后尝试）
                ]
                
                for wait_until, timeout in wait_strategies:
                    try:
                        print(f"📡 尝试等待策略: {wait_until} (超时: {timeout}ms)")
                        response = await page.goto(validated_url, wait_until=wait_until, timeout=timeout)
                        print(f"✅ 导航成功，使用策略: {wait_until}")
                        break
                    except Exception as e:
                        print(f"⚠️ 策略 {wait_until} 失败: {str(e)[:100]}")
                        if wait_until == 'load':  # 最后一个策略也失败了
                            raise
                
                if response is None:
                    raise ContentExtractionError("页面导航失败", details="无法访问指定URL")
                
                # 检查响应状态
                if response.status >= 400:
                    raise ContentExtractionError(
                        f"HTTP错误: {response.status}",
                        details=f"服务器返回状态码: {response.status}"
                    )
                
                # 等待页面加载完成
                await self._wait_for_page_load(page)
                
                # 获取页面内容
                html_content = await page.content()
                page_title = await page.title()
                final_url = page.url
                
                print(f"✅ 页面加载成功，内容长度: {len(html_content)}")
                
                # 提取结构化内容
                extracted_content = await self._extract_structured_content(page)
                
                # 使用readability提取主要内容
                doc = Document(html_content)
                title = doc.title() or page_title or "无标题"
                main_content = doc.summary()
                
                # 清理内容
                cleaned_content = self._clean_content(main_content)
                
                # 如果有结构化内容，优先使用
                if extracted_content and len(extracted_content) > len(cleaned_content) * 0.5:
                    final_content = extracted_content
                else:
                    final_content = cleaned_content
                
                # 提取meta信息
                meta_description = await self._extract_meta_description(page)
                
                # 限制最终内容长度
                if len(final_content) > self.max_content_length:
                    final_content = final_content[:self.max_content_length] + "..."
                
                return WebContent(
                    url=final_url,
                    title=title.strip(),
                    content=final_content,
                    meta_description=meta_description,
                    extracted_at=datetime.utcnow()
                )
                
            finally:
                # 关闭页面
                await page.close()
                
        except Exception as e:
            if isinstance(e, (URLValidationError, ContentExtractionError)):
                raise
            else:
                raise ContentExtractionError(
                    f"内容提取失败: {str(e)}",
                    details="使用Playwright提取内容时发生错误"
                )
    
    async def _setup_page_listeners(self, page: Page):
        """设置页面事件监听器"""
        try:
            # 屏蔽不必要的资源类型，提高加载速度
            await page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot}", lambda route: route.abort())
            await page.route("**/*analytics*", lambda route: route.abort())
            await page.route("**/*tracking*", lambda route: route.abort())
            await page.route("**/*ads*", lambda route: route.abort())
            
            # 监听控制台消息（仅记录严重错误）
            page.on("console", lambda msg: None if msg.type in ["log", "info", "warning"] 
                   else print(f"Console: {msg.text}"))
            
            # 监听页面错误（仅记录关键错误）
            page.on("pageerror", lambda error: print(f"Page error: {error}") 
                   if "ERR_SSL" not in str(error) and "ERR_FAILED" not in str(error) else None)
                   
        except Exception as e:
            print(f"⚠️ 页面监听器设置失败: {e}")

    async def _wait_for_page_load(self, page: Page):
        """智能等待页面加载 - 优化版本"""
        try:
            # 先等待DOM内容加载完成
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
            
            # 等待一小段时间让动态内容渲染
            await page.wait_for_timeout(2000)
            
            # 尝试等待网络空闲，但使用较短的超时时间
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except:
                # 如果网络空闲等待超时，继续执行（很多网站有持续的后台请求）
                print("🔄 网络仍有活动，但继续提取内容...")
            
            # 如果指定了选择器，等待其出现
            if self.wait_for_selector:
                try:
                    await page.wait_for_selector(self.wait_for_selector, timeout=5000)
                except:
                    print(f"⚠️ 等待选择器超时: {self.wait_for_selector}")
            
            print("✅ 页面内容已准备就绪")
                
        except Exception as e:
            print(f"⚠️ 页面加载等待异常: {e}")
            # 继续执行，不抛出异常
    
    async def _extract_structured_content(self, page: Page) -> str:
        """提取结构化内容"""
        try:
            # 尝试提取主要内容区域
            content_selectors = [
                'main',
                'article',
                '[role="main"]',
                '.content',
                '.main-content',
                '.post-content',
                '.entry-content',
                '#content',
                '#main-content'
            ]
            
            for selector in content_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text_content = await element.inner_text()
                        if text_content and len(text_content.strip()) > 100:
                            print(f"✅ 使用选择器提取内容: {selector}")
                            return text_content.strip()
                except:
                    continue
            
            # 如果没有找到主要内容区域，提取body内容
            body_element = await page.query_selector('body')
            if body_element:
                body_text = await body_element.inner_text()
                return body_text.strip() if body_text else ""
            
            return ""
            
        except Exception as e:
            print(f"⚠️ 结构化内容提取失败: {e}")
            return ""
    
    async def _extract_meta_description(self, page: Page) -> Optional[str]:
        """提取meta描述信息"""
        try:
            # 尝试多种meta描述选择器
            meta_selectors = [
                'meta[name="description"]',
                'meta[property="og:description"]',
                'meta[name="twitter:description"]'
            ]
            
            for selector in meta_selectors:
                element = await page.query_selector(selector)
                if element:
                    content = await element.get_attribute('content')
                    if content and content.strip():
                        return content.strip()
            
            return None
            
        except Exception:
            return None
    
    def _clean_content(self, html_content: str) -> str:
        """清理HTML内容"""
        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除不需要的标签
            unwanted_tags = [
                'script', 'style', 'nav', 'header', 'footer', 'aside',
                'advertisement', 'ads', 'iframe', 'embed', 'object',
                'form', 'input', 'button', 'select', 'textarea',
                'noscript', 'meta', 'link', 'base'
            ]
            for tag in soup(unwanted_tags):
                tag.decompose()
            
            # 获取文本内容
            text = soup.get_text(separator=' ', strip=True)
            
            # 清理文本
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n\n', text)
            
            return text.strip()
            
        except Exception:
            # 如果清理失败，返回原始内容
            return html_content
    
    async def close(self):
        """关闭浏览器实例"""
        if self._context:
            await self._context.close()
            self._context = None
        
        if self._browser:
            await self._browser.close()
            self._browser = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


class SmartContentExtractor:
    """智能内容提取器，自动选择最佳提取方式"""
    
    def __init__(self, 
                 timeout: int = 30,
                 max_content_length: int = 50000,
                 prefer_playwright: bool = True):
        """
        初始化智能内容提取器
        
        Args:
            timeout: 超时时间
            max_content_length: 最大内容长度
            prefer_playwright: 是否优先使用Playwright
        """
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.prefer_playwright = prefer_playwright
        
        # 需要使用Playwright的域名模式
        self.playwright_domains = {
            # 代码托管平台
            'github.com',
            'gitlab.com',
            'bitbucket.org',
            
            # 开发者社区
            'stackoverflow.com',
            'stackexchange.com',
            'dev.to',
            'hackernoon.com',
            'hashnode.com',
            
            # 博客平台
            'medium.com',
            'substack.com',
            'notion.so',
            
            # 任务/项目平台
            'dorahacks.io',
            'gitcoin.co',
            'upwork.com',
            'freelancer.com',
            'fiverr.com',
            '99designs.com',
            
            # 社交媒体 (反爬虫严格)
            'twitter.com',
            'x.com',
            'facebook.com',
            'linkedin.com',
            'instagram.com',
            'reddit.com',
            'discord.com',
            
            # 其他复杂JavaScript网站
            'notion.site',
            'airtable.com',
            'figma.com',
            'canva.com',
            'trello.com'
        }
    
    def _should_use_playwright(self, url: str) -> bool:
        """判断是否应该使用Playwright"""
        if not self.prefer_playwright:
            return False
        
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.lower()
            
            # 检查是否在需要Playwright的域名列表中
            for playwright_domain in self.playwright_domains:
                if playwright_domain in domain:
                    return True
            
            return False
            
        except:
            return False
    
    async def extract_content(self, url: str) -> WebContent:
        """
        智能提取内容
        
        Args:
            url: 要提取的URL
            
        Returns:
            WebContent: 提取的网页内容
        """
        # 判断使用哪种提取方式
        use_playwright = self._should_use_playwright(url)
        
        if use_playwright:
            print("🎭 使用Playwright提取内容")
            async with PlaywrightContentExtractor(
                timeout=self.timeout,
                max_content_length=self.max_content_length
            ) as extractor:
                return await extractor.extract_content(url)
        else:
            print("🌐 使用传统HTTP方式提取内容")
            # 导入原始的内容提取器
            from .content_extractor import ContentExtractor
            extractor = ContentExtractor(
                timeout=self.timeout,
                max_content_length=self.max_content_length
            )
            return await extractor.extract_content(url)