"""
Content extraction functionality for URL agent.
"""
import asyncio
import re
import urllib.parse
from datetime import datetime
from typing import Optional
import aiohttp
from bs4 import BeautifulSoup
from readability.readability import Document

from .models import WebContent
from .exceptions import URLValidationError, ContentExtractionError


class ContentExtractor:
    """网页内容提取器"""
    
    def __init__(self, 
                 timeout: int = 30,
                 max_content_length: int = 50000,
                 user_agent: str = "BountyGo-URLAgent/1.0"):
        """
        初始化内容提取器
        
        Args:
            timeout: 请求超时时间(秒)
            max_content_length: 最大内容长度
            user_agent: 用户代理字符串
        """
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.user_agent = user_agent
        
        # 安全的URL模式
        self.allowed_schemes = {'http', 'https'}
        self.blocked_domains = {
            'localhost', '127.0.0.1', '0.0.0.0',
            '10.', '172.16.', '192.168.'  # 内网地址前缀
        }
    
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
                    f"不支持的协议: {parsed.scheme}，仅支持: {', '.join(self.allowed_schemes)}"
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
    
    async def extract_content(self, url: str) -> WebContent:
        """
        提取网页内容
        
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
            # 配置请求头
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # 创建会话并获取内容
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(validated_url) as response:
                    # 检查响应状态
                    if response.status >= 400:
                        raise ContentExtractionError(
                            f"HTTP错误: {response.status}",
                            details=f"服务器返回状态码: {response.status}"
                        )
                    
                    # 检查内容类型
                    content_type = response.headers.get('content-type', '').lower()
                    if 'text/html' not in content_type:
                        raise ContentExtractionError(
                            f"不支持的内容类型: {content_type}",
                            details="仅支持HTML内容"
                        )
                    
                    # 读取HTML内容
                    html_content = await response.text()
                    
                    # 检查内容长度
                    if len(html_content) > self.max_content_length * 2:  # 原始HTML可能更长
                        html_content = html_content[:self.max_content_length * 2]
            
            # 使用readability提取主要内容
            doc = Document(html_content)
            title = doc.title() or "无标题"
            main_content = doc.summary()
            
            # 使用BeautifulSoup进一步清理内容
            cleaned_content = self.clean_content(main_content)
            
            # 提取meta信息
            meta_description = self.extract_meta_description(html_content)
            
            # 限制最终内容长度
            if len(cleaned_content) > self.max_content_length:
                cleaned_content = cleaned_content[:self.max_content_length] + "..."
            
            return WebContent(
                url=validated_url,
                title=title.strip(),
                content=cleaned_content,
                meta_description=meta_description,
                extracted_at=datetime.utcnow()
            )
            
        except aiohttp.ClientError as e:
            raise ContentExtractionError(
                f"网络请求失败: {str(e)}",
                details="请检查网络连接或URL是否可访问"
            )
        except asyncio.TimeoutError:
            raise ContentExtractionError(
                f"请求超时: {self.timeout}秒",
                details="网页响应时间过长"
            )
        except Exception as e:
            raise ContentExtractionError(
                f"内容提取失败: {str(e)}",
                details="处理网页内容时发生未知错误"
            )
    
    def clean_content(self, html_content: str) -> str:
        """
        清理和格式化HTML内容
        
        Args:
            html_content: 原始HTML内容
            
        Returns:
            str: 清理后的文本内容
        """
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
            
            # 移除具有特定class或id的元素（通常是广告或导航）
            unwanted_selectors = [
                '[class*="ad"]', '[class*="advertisement"]', '[class*="banner"]',
                '[class*="nav"]', '[class*="menu"]', '[class*="sidebar"]',
                '[class*="footer"]', '[class*="header"]', '[id*="ad"]',
                '[class*="social"]', '[class*="share"]', '[class*="comment"]'
            ]
            for selector in unwanted_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # 移除注释
            for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
                comment.extract()
            
            # 保留重要的结构化信息
            structured_content = self._extract_structured_content(soup)
            
            # 获取文本内容
            text = soup.get_text(separator=' ', strip=True)
            
            # 应用高级文本清理
            cleaned_text = self._advanced_text_cleaning(text)
            
            # 如果有结构化内容，将其添加到开头
            if structured_content:
                cleaned_text = structured_content + '\n\n' + cleaned_text
            
            return cleaned_text
            
        except Exception as e:
            # 如果清理失败，返回简单的文本提取
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text(strip=True)
    
    def _extract_structured_content(self, soup: BeautifulSoup) -> str:
        """
        提取结构化内容（标题、列表等）
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            str: 结构化内容
        """
        structured_parts = []
        
        # 提取主标题
        main_title = soup.find(['h1'])
        if main_title:
            title_text = main_title.get_text(strip=True)
            if title_text and len(title_text) > 5:
                structured_parts.append(f"标题: {title_text}")
        
        # 提取副标题
        subtitles = soup.find_all(['h2', 'h3'])
        for subtitle in subtitles[:5]:  # 最多5个副标题
            subtitle_text = subtitle.get_text(strip=True)
            if subtitle_text and len(subtitle_text) > 3:
                structured_parts.append(f"- {subtitle_text}")
        
        # 提取重要的列表项
        lists = soup.find_all(['ul', 'ol'])
        for list_elem in lists[:3]:  # 最多3个列表
            items = list_elem.find_all('li')
            for item in items[:10]:  # 每个列表最多10项
                item_text = item.get_text(strip=True)
                if item_text and len(item_text) > 5:
                    structured_parts.append(f"• {item_text}")
        
        return '\n'.join(structured_parts) if structured_parts else ""
    
    def _advanced_text_cleaning(self, text: str) -> str:
        """
        高级文本清理和格式化
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # 移除重复的标点符号
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        # 移除常见的无用文本模式
        useless_patterns = [
            r'点击这里.*?了解更多',
            r'更多信息请.*?访问',
            r'版权所有.*?\d{4}',
            r'Copyright.*?\d{4}',
            r'All rights reserved',
            r'免责声明.*?',
            r'隐私政策.*?',
            r'使用条款.*?',
            r'Cookie.*?政策',
            r'广告.*?',
            r'赞助.*?',
        ]
        
        for pattern in useless_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # 分行处理
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 跳过过短的行
            if len(line) < 10:
                continue
            
            # 跳过可能是导航或菜单的行
            if self._is_navigation_line(line):
                continue
            
            # 跳过重复的行
            if line not in cleaned_lines:
                cleaned_lines.append(line)
        
        # 限制行数
        if len(cleaned_lines) > 100:
            cleaned_lines = cleaned_lines[:100]
        
        return '\n'.join(cleaned_lines).strip()
    
    def _is_navigation_line(self, line: str) -> bool:
        """
        判断是否为导航或菜单行
        
        Args:
            line: 文本行
            
        Returns:
            bool: 是否为导航行
        """
        navigation_keywords = [
            '首页', '主页', '登录', '注册', '搜索', '联系我们',
            '关于我们', '帮助', '支持', '反馈', '设置',
            'Home', 'Login', 'Register', 'Search', 'Contact',
            'About', 'Help', 'Support', 'Settings', 'Menu'
        ]
        
        # 检查是否包含多个导航关键词
        keyword_count = sum(1 for keyword in navigation_keywords if keyword.lower() in line.lower())
        if keyword_count >= 2:
            return True
        
        # 检查是否为链接集合（包含多个分隔符）
        separators = ['|', '·', '•', '>', '<', '/', '\\']
        separator_count = sum(line.count(sep) for sep in separators)
        if separator_count >= 3:
            return True
        
        return False
    
    def truncate_content(self, content: str, max_length: int = None) -> str:
        """
        截断内容到指定长度
        
        Args:
            content: 原始内容
            max_length: 最大长度，默认使用实例配置
            
        Returns:
            str: 截断后的内容
        """
        if max_length is None:
            max_length = self.max_content_length
        
        if len(content) <= max_length:
            return content
        
        # 尝试在句子边界截断
        truncated = content[:max_length]
        
        # 查找最后一个句号、问号或感叹号
        last_sentence_end = max(
            truncated.rfind('.'),
            truncated.rfind('。'),
            truncated.rfind('!'),
            truncated.rfind('！'),
            truncated.rfind('?'),
            truncated.rfind('？')
        )
        
        if last_sentence_end > max_length * 0.8:  # 如果句子边界在80%以后
            return truncated[:last_sentence_end + 1] + "..."
        
        # 否则在词边界截断
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.9:  # 如果空格在90%以后
            return truncated[:last_space] + "..."
        
        return truncated + "..."
    
    def extract_meta_description(self, html_content: str) -> Optional[str]:
        """
        提取meta描述信息
        
        Args:
            html_content: HTML内容
            
        Returns:
            Optional[str]: meta描述，如果没有则返回None
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找meta description标签
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc.get('content').strip()
                if description:
                    return description
            
            # 查找Open Graph描述
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc and og_desc.get('content'):
                description = og_desc.get('content').strip()
                if description:
                    return description
            
            # 查找Twitter描述
            twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
            if twitter_desc and twitter_desc.get('content'):
                description = twitter_desc.get('content').strip()
                if description:
                    return description
            
            return None
            
        except Exception:
            return None
    
    def extract_additional_metadata(self, html_content: str) -> dict:
        """
        提取额外的元数据信息
        
        Args:
            html_content: HTML内容
            
        Returns:
            dict: 包含额外元数据的字典
        """
        metadata = {}
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取关键词
            keywords_meta = soup.find('meta', attrs={'name': 'keywords'})
            if keywords_meta and keywords_meta.get('content'):
                metadata['keywords'] = keywords_meta.get('content').strip()
            
            # 提取作者信息
            author_meta = soup.find('meta', attrs={'name': 'author'})
            if author_meta and author_meta.get('content'):
                metadata['author'] = author_meta.get('content').strip()
            
            # 提取发布日期
            published_meta = soup.find('meta', attrs={'property': 'article:published_time'})
            if published_meta and published_meta.get('content'):
                metadata['published_time'] = published_meta.get('content').strip()
            
            # 提取语言信息
            html_tag = soup.find('html')
            if html_tag and html_tag.get('lang'):
                metadata['language'] = html_tag.get('lang').strip()
            
            # 提取Open Graph图片
            og_image = soup.find('meta', attrs={'property': 'og:image'})
            if og_image and og_image.get('content'):
                metadata['image_url'] = og_image.get('content').strip()
            
        except Exception:
            pass  # 忽略元数据提取错误
        
        return metadata