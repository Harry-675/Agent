"""NewsCrawler implementation for fetching news from configured sources."""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from src.models.news_source import NewsSource
from src.models.news_item import NewsItem
from src.models.error_log import ErrorLog
from src.config.settings import get_settings


logger = logging.getLogger(__name__)


class NewsCrawler:
    """新闻爬虫模块
    
    负责从配置的新闻源抓取新闻内容，包括：
    - 异步并发抓取多个新闻源
    - 网页内容解析（标题、摘要、链接、发布时间）
    - 超时控制（30秒超时）
    - 错误处理和日志记录
    
    Attributes:
        sources: 新闻源列表
        timeout: 抓取超时时间（秒）
        max_concurrent: 最大并发抓取数
    """
    
    def __init__(
        self,
        sources: List[NewsSource],
        timeout: Optional[int] = None,
        max_concurrent: Optional[int] = None
    ):
        """初始化新闻爬虫
        
        Args:
            sources: 新闻源列表
            timeout: 超时时间（秒），默认从配置读取
            max_concurrent: 最大并发数，默认从配置读取
        """
        self.sources = sources
        settings = get_settings()
        self.timeout = timeout or settings.crawler_timeout
        self.max_concurrent = max_concurrent or settings.max_concurrent_crawls
        self.error_logs: List[ErrorLog] = []
    
    async def crawl_all(self) -> List[NewsItem]:
        """抓取所有启用的新闻源
        
        并发抓取所有启用的新闻源，收集所有成功抓取的新闻条目。
        如果某个源抓取失败，记录错误但不影响其他源的处理。
        
        Returns:
            List[NewsItem]: 所有成功抓取的新闻条目列表
        """
        # 过滤出启用的新闻源
        enabled_sources = [source for source in self.sources if source.enabled]
        
        if not enabled_sources:
            logger.warning("No enabled news sources found")
            return []
        
        logger.info(f"Starting to crawl {len(enabled_sources)} enabled news sources")
        
        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def crawl_with_semaphore(source: NewsSource) -> List[NewsItem]:
            """带信号量控制的抓取"""
            async with semaphore:
                return await self.crawl_source(source)
        
        # 并发抓取所有源
        tasks = [crawl_with_semaphore(source) for source in enabled_sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 展平结果并过滤异常
        return self._flatten_results(results)
    
    async def crawl_source(self, source: NewsSource) -> List[NewsItem]:
        """抓取单个新闻源
        
        从指定的新闻源抓取新闻内容，解析网页并提取新闻条目。
        
        Args:
            source: 新闻源配置
            
        Returns:
            List[NewsItem]: 抓取到的新闻条目列表，失败时返回空列表
        """
        try:
            logger.info(f"Crawling news source: {source.name} ({source.url})")
            
            crawl_type = source.crawl_rules.get("type", "html") if source.crawl_rules else "html"
            
            if crawl_type == "hn-api":
                news_items = await self._fetch_hackernews(source)
            elif crawl_type == "reddit":
                news_items = await self._fetch_reddit(source)
            elif crawl_type == "rss":
                news_items = await self._fetch_rss(source)
            elif crawl_type == "api":
                news_items = await self._fetch_api(source)
            elif crawl_type.startswith("sina-") or crawl_type.startswith("163-") or crawl_type.startswith("qq-") or crawl_type.startswith("ifeng-") or crawl_type.startswith("sohu-") or crawl_type.startswith("zj-") or crawl_type.startswith("huanqiu-"):
                # Chinese news sites - use HTML parsing with category from config
                news_items = await self._fetch_chinese_news(source)
            else:
                html_content = await self._fetch_html(source)
                
                if not html_content:
                    logger.warning(f"No content fetched from {source.name}")
                    return []
                
                news_items = await self._parse_html(html_content, source)
            
            logger.info(f"Successfully crawled {len(news_items)} items from {source.name}")
            return news_items
            
        except asyncio.TimeoutError:
            error_log = ErrorLog.from_exception(
                error_type="network",
                component="crawler",
                operation="crawl_source",
                exception=asyncio.TimeoutError(f"Timeout after {source.timeout}s"),
                context={"source_id": source.id, "source_name": source.name}
            )
            self.error_logs.append(error_log)
            logger.error(f"Timeout crawling {source.name}: {source.timeout}s exceeded")
            return []
            
        except httpx.HTTPError as e:
            error_log = ErrorLog.from_exception(
                error_type="network",
                component="crawler",
                operation="crawl_source",
                exception=e,
                context={"source_id": source.id, "source_name": source.name}
            )
            self.error_logs.append(error_log)
            logger.error(f"HTTP error crawling {source.name}: {str(e)}")
            return []
            
        except Exception as e:
            error_log = ErrorLog.from_exception(
                error_type="system",
                component="crawler",
                operation="crawl_source",
                exception=e,
                context={"source_id": source.id, "source_name": source.name}
            )
            self.error_logs.append(error_log)
            logger.error(f"Unexpected error crawling {source.name}: {str(e)}")
            return []
    
    async def _fetch_html(self, source: NewsSource) -> Optional[str]:
        """获取网页HTML内容
        
        Args:
            source: 新闻源配置
            
        Returns:
            Optional[str]: HTML内容，失败时返回None
        """
        timeout_config = httpx.Timeout(source.timeout, connect=10.0)
        
        async with httpx.AsyncClient(timeout=timeout_config, follow_redirects=True) as client:
            try:
                response = await client.get(
                    source.url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                )
                response.raise_for_status()
                return response.text
                
            except httpx.TimeoutException:
                raise asyncio.TimeoutError(f"Request timeout after {source.timeout}s")
    
    async def _fetch_api(self, source: NewsSource) -> List[NewsItem]:
        """Fetch news from API endpoint.
        
        Args:
            source: News source configuration
            
        Returns:
            List[NewsItem]: Parsed news items
        """
        try:
            timeout_config = httpx.Timeout(source.timeout, connect=10.0)
            
            async with httpx.AsyncClient(timeout=timeout_config, follow_redirects=True) as client:
                response = await client.get(
                    source.url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/json'
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                rules = source.crawl_rules
                
                return self._parse_api_response(data, source, rules)
                
        except httpx.TimeoutException:
            raise asyncio.TimeoutError(f"API timeout after {source.timeout}s")
        except httpx.HTTPError as e:
            logger.error(f"API error for {source.name}: {e}")
            return []
    
    async def _fetch_hackernews(self, source: NewsSource) -> List[NewsItem]:
        """Fetch news from Hacker News API."""
        try:
            timeout_config = httpx.Timeout(source.timeout, connect=10.0)
            
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.get(source.url)
                response.raise_for_status()
                story_ids = response.json()[:30]
                
                news_items = []
                for story_id in story_ids:
                    item_resp = await client.get(
                        f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    )
                    if item_resp.status_code == 200:
                        story = item_resp.json()
                        if story and story.get("title"):
                            from datetime import datetime
                            published_at = datetime.fromtimestamp(story.get("time", 0))
                            
                            category = source.crawl_rules.get("category", "科技") if source.crawl_rules else "科技"
                            news_item = NewsItem(
                                id=str(uuid.uuid4()),
                                title=story.get("title", "")[:200],
                                summary=story.get("text", "")[:500] if story.get("text") else "",
                                url=story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                                published_at=published_at,
                                source_id=source.id,
                                source_name=source.name,
                                categories=[category],
                                source_tags=[source.name]
                            )
                            news_items.append(news_item)
                
                return news_items
                
        except Exception as e:
            logger.error(f"Hacker News error for {source.name}: {e}")
            return []
    
    async def _fetch_reddit(self, source: NewsSource) -> List[NewsItem]:
        """Fetch news from Reddit API."""
        try:
            timeout_config = httpx.Timeout(source.timeout, connect=10.0)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with httpx.AsyncClient(timeout=timeout_config, headers=headers) as client:
                response = await client.get(source.url)
                response.raise_for_status()
                
                data = response.json()
                children = data.get("data", {}).get("children", [])
                
                news_items = []
                for child in children:
                    post = child.get("data", {})
                    title = post.get("title", "")
                    
                    if not title:
                        continue
                    
                    from datetime import datetime
                    published_at = datetime.fromtimestamp(post.get("created_utc", 0))
                    
                    category = source.crawl_rules.get("category", "科技") if source.crawl_rules else "科技"
                    news_item = NewsItem(
                        id=str(uuid.uuid4()),
                        title=title[:200],
                        summary=post.get("selftext", "")[:500],
                        url=post.get("url", f"https://reddit.com{post.get('permalink', '')}"),
                        published_at=published_at,
                        source_id=source.id,
                        source_name=source.name,
                        categories=[category],
                        source_tags=[source.name]
                    )
                    news_items.append(news_item)
                
                return news_items
                
        except Exception as e:
            logger.error(f"Reddit error for {source.name}: {e}")
            return []
    
    async def _fetch_rss(self, source: NewsSource) -> List[NewsItem]:
        """Fetch news from RSS feed."""
        try:
            timeout_config = httpx.Timeout(source.timeout, connect=10.0)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with httpx.AsyncClient(timeout=timeout_config, headers=headers) as client:
                response = await client.get(source.url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'lxml')
                news_items = []
                
                for item in soup.find_all('item')[:30]:
                    try:
                        title = item.find('title')
                        if not title:
                            continue
                        
                        link = item.find('link')
                        description = item.find('description')
                        pub_date = item.find('pubDate')
                        
                        from datetime import datetime
                        published_at = datetime.now()
                        if pub_date:
                            try:
                                from email.utils import parsedate_to_datetime
                                published_at = parsedate_to_datetime(pub_date.text)
                            except:
                                pass
                        
                        category = source.crawl_rules.get("category", "科技") if source.crawl_rules else "科技"
                        news_item = NewsItem(
                            id=str(uuid.uuid4()),
                            title=title.text[:200],
                            summary=description.text[:500] if description else "",
                            url=link.text if link else "",
                            published_at=published_at,
                            source_id=source.id,
                            source_name=source.name,
                            categories=[category],
                            source_tags=[source.name]
                        )
                        news_items.append(news_item)
                    except Exception:
                        continue
                
                return news_items
                
        except Exception as e:
            logger.error(f"RSS error for {source.name}: {e}")
            return []
    
    async def _fetch_chinese_news(self, source: NewsSource) -> List[NewsItem]:
        """Fetch news from Chinese news sites."""
        try:
            timeout_config = httpx.Timeout(source.timeout, connect=10.0)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            async with httpx.AsyncClient(timeout=timeout_config, headers=headers, follow_redirects=True) as client:
                response = await client.get(source.url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'lxml')
                news_items = []
                
                category = source.crawl_rules.get("category", "科技") if source.crawl_rules else "科技"
                
                # Common patterns for Chinese news sites
                selectors = [
                    ('h3 a', 'a', 'p'),
                    ('.news-title a', '.news-title', '.news-desc'),
                    ('.title a', '.title', '.desc'),
                    ('article h2 a', 'article', '.summary'),
                    ('.item-title a', '.item-title', '.item-desc'),
                    ('li a', 'li', None),
                ]
                
                found_items = set()
                
                for title_sel, container_sel, desc_sel in selectors:
                    for elem in soup.select(title_sel)[:20]:
                        try:
                            title = elem.get_text(strip=True)
                            if not title or len(title) < 5 or title in found_items:
                                continue
                            found_items.add(title)
                            
                            link = elem.get('href', '')
                            if link and not link.startswith('http'):
                                from urllib.parse import urljoin
                                link = urljoin(source.url, link)
                            
                            summary = ""
                            if desc_sel:
                                parent = elem.find_parent(container_sel) if container_sel else elem.parent
                                if parent:
                                    desc_elem = parent.select_one(desc_sel)
                                    if desc_elem:
                                        summary = desc_elem.get_text(strip=True)[:300]
                            
                            news_item = NewsItem(
                                id=str(uuid.uuid4()),
                                title=title[:200],
                                summary=summary,
                                url=link,
                                published_at=datetime.now(),
                                source_id=source.id,
                                source_name=source.name,
                                categories=[category],
                                source_tags=[source.name]
                            )
                            news_items.append(news_item)
                            
                            if len(news_items) >= 20:
                                break
                        except Exception:
                            continue
                    
                    if news_items:
                        break
                
                return news_items[:30]
                
        except Exception as e:
            logger.error(f"Chinese news error for {source.name}: {e}")
            return []
    
    def _parse_api_response(
        self, 
        data: Any, 
        source: NewsSource, 
        rules: dict
    ) -> List[NewsItem]:
        """Parse API JSON response to extract news items.
        
        Args:
            data: API response data
            source: News source configuration
            rules: Crawl rules with JSON paths
            
        Returns:
            List[NewsItem]: Extracted news items
        """
        news_items = []
        
        title_path = rules.get("title", "").split(".")
        summary_path = rules.get("summary", "").split(".")
        link_path = rules.get("link", "").split(".")
        time_path = rules.get("published_at", "").split(".")
        
        items = self._get_nested_value(data, ["data", "list", "items", "newslist", "hot_list"])
        if not items:
            items = [data]
        
        for idx, item in enumerate(items):
            try:
                title = self._extract_by_path(item, title_path)
                summary = self._extract_by_path(item, summary_path)
                link = self._extract_by_path(item, link_path)
                published_at_str = self._extract_by_path(item, time_path)
                
                if not title:
                    continue
                
                if link and not link.startswith("http"):
                    link = f"https://www.zhihu.com/question/{item.get('target', {}).get('id', '')}"
                
                from datetime import datetime
                published_at = datetime.now()
                if published_at_str:
                    try:
                        if isinstance(published_at_str, (int, float)):
                            published_at = datetime.fromtimestamp(published_at_str)
                        else:
                            published_at = datetime.fromisoformat(str(published_at_str).replace('Z', '+08:00'))
                    except:
                        pass
                
                category = source.crawl_rules.get("category", "科技") if source.crawl_rules else "科技"
                news_item = NewsItem(
                    id=str(uuid.uuid4()),
                    title=str(title)[:200],
                    summary=str(summary)[:500] if summary else "",
                    url=str(link) if link else "",
                    published_at=published_at,
                    source_id=source.id,
                    source_name=source.name,
                    categories=[category],
                    source_tags=[source.name]
                )
                news_items.append(news_item)
                
            except Exception as e:
                logger.debug(f"Failed to parse API item {idx}: {e}")
                continue
        
        return news_items
    
    def _get_nested_value(self, data: Any, keys: List[str]) -> Any:
        """Get value from nested dict using list of keys."""
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                idx = int(key)
                current = current[idx] if idx < len(current) else None
            else:
                return None
            if current is None:
                return None
        return current
    
    def _extract_by_path(self, data: Any, path: List[str]) -> Any:
        """Extract value from data using dot-separated path."""
        if not path or path[0] == "":
            return data
        return self._get_nested_value(data, path)
    
    async def _parse_html(self, html_content: str, source: NewsSource) -> List[NewsItem]:
        """解析HTML内容，提取新闻条目
        
        Args:
            html_content: HTML内容
            source: 新闻源配置
            
        Returns:
            List[NewsItem]: 解析出的新闻条目列表
        """
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            news_items = []
            
            # 获取爬取规则
            rules = source.crawl_rules
            
            # 如果有容器选择器，先找到所有新闻容器
            if 'container' in rules:
                containers = soup.select(rules['container'])
            else:
                # 如果没有容器选择器，使用整个页面作为容器
                containers = [soup]
            
            for container in containers:
                try:
                    news_item = self._extract_news_item(container, source, rules)
                    if news_item:
                        news_items.append(news_item)
                except Exception as e:
                    logger.warning(f"Failed to extract news item from container: {str(e)}")
                    continue
            
            return news_items
            
        except Exception as e:
            error_log = ErrorLog.from_exception(
                error_type="parse",
                component="crawler",
                operation="_parse_html",
                exception=e,
                context={"source_id": source.id, "source_name": source.name}
            )
            self.error_logs.append(error_log)
            logger.error(f"Failed to parse HTML from {source.name}: {str(e)}")
            return []
    
    def _extract_news_item(
        self,
        container: BeautifulSoup,
        source: NewsSource,
        rules: dict
    ) -> Optional[NewsItem]:
        """从容器中提取单个新闻条目
        
        Args:
            container: BeautifulSoup容器对象
            source: 新闻源配置
            rules: 爬取规则
            
        Returns:
            Optional[NewsItem]: 新闻条目，提取失败返回None
        """
        try:
            # 提取标题（必需）
            title_element = container.select_one(rules.get('title', ''))
            if not title_element:
                return None
            title = title_element.get_text(strip=True)
            
            if not title:
                return None
            
            # 提取链接（必需）
            link_element = container.select_one(rules.get('link', ''))
            if not link_element:
                return None
            
            # 获取链接URL
            url = link_element.get('href', '')
            if not url:
                return None
            
            # 处理相对URL
            if not url.startswith(('http://', 'https://')):
                url = urljoin(source.url, url)
            
            # 提取摘要（必需）
            summary_selector = rules.get('summary', '')
            if summary_selector:
                summary_element = container.select_one(summary_selector)
                if summary_element:
                    summary = summary_element.get_text(strip=True)
                else:
                    # 如果没有找到摘要元素，使用标题作为摘要
                    summary = title
            else:
                # 如果没有摘要选择器，使用标题作为摘要
                summary = title
            
            # 提取发布时间（必需）
            published_at = self._extract_published_time(container, rules)
            if not published_at:
                # 如果无法提取发布时间，使用当前时间
                published_at = datetime.now()
            
            category = source.crawl_rules.get("category", "科技") if source.crawl_rules else "科技"
            news_item = NewsItem(
                id=str(uuid.uuid4()),
                title=title,
                summary=summary,
                url=url,
                published_at=published_at,
                source_id=source.id,
                source_name=source.name,
                categories=[category],
                source_tags=[source.name],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            return news_item
            
        except Exception as e:
            logger.warning(f"Failed to extract news item: {str(e)}")
            return None
    
    def _extract_published_time(
        self,
        container: BeautifulSoup,
        rules: dict
    ) -> Optional[datetime]:
        """提取发布时间
        
        Args:
            container: BeautifulSoup容器对象
            rules: 爬取规则
            
        Returns:
            Optional[datetime]: 发布时间，提取失败返回None
        """
        try:
            if 'published_at' not in rules:
                return None
            
            time_element = container.select_one(rules['published_at'])
            if not time_element:
                return None
            
            time_text = time_element.get_text(strip=True)
            if not time_text:
                # 尝试从datetime属性获取
                time_text = time_element.get('datetime', '')
            
            if not time_text:
                return None
            
            # 尝试解析时间字符串
            # 这里使用简单的解析逻辑，实际项目中可能需要更复杂的时间解析
            from dateutil import parser
            return parser.parse(time_text)
            
        except Exception as e:
            logger.debug(f"Failed to parse published time: {str(e)}")
            return None
    
    def _flatten_results(self, results: List) -> List[NewsItem]:
        """展平结果并过滤异常
        
        Args:
            results: 抓取结果列表，可能包含异常
            
        Returns:
            List[NewsItem]: 展平后的新闻条目列表
        """
        flattened = []
        
        for result in results:
            # 跳过异常
            if isinstance(result, Exception):
                logger.error(f"Crawl task failed with exception: {str(result)}")
                continue
            
            # 跳过None
            if result is None:
                continue
            
            # 如果是列表，展开
            if isinstance(result, list):
                flattened.extend(result)
            else:
                flattened.append(result)
        
        return flattened
    
    def get_error_logs(self) -> List[ErrorLog]:
        """获取错误日志列表
        
        Returns:
            List[ErrorLog]: 错误日志列表
        """
        return self.error_logs.copy()
    
    def clear_error_logs(self) -> None:
        """清空错误日志"""
        self.error_logs.clear()
