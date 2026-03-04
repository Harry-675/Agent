"""Unit tests for NewsCrawler."""

import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import uuid

import pytest
import httpx

from src.crawler.news_crawler import NewsCrawler
from src.models.news_source import NewsSource
from src.models.news_item import NewsItem


@pytest.fixture
def sample_news_source():
    """创建示例新闻源"""
    return NewsSource(
        id=str(uuid.uuid4()),
        name="Test News",
        url="https://example.com/news",
        enabled=True,
        crawl_rules={
            "container": "article.news-item",
            "title": "h2.title",
            "link": "a.link",
            "summary": "p.summary",
            "published_at": "time.published"
        },
        timeout=30
    )


@pytest.fixture
def disabled_news_source():
    """创建禁用的新闻源"""
    return NewsSource(
        id=str(uuid.uuid4()),
        name="Disabled News",
        url="https://example.com/disabled",
        enabled=False,
        crawl_rules={"title": "h1"},
        timeout=30
    )


@pytest.fixture
def sample_html():
    """创建示例HTML内容"""
    return """
    <html>
        <body>
            <article class="news-item">
                <h2 class="title">Test News Title 1</h2>
                <a class="link" href="/news/1">Read more</a>
                <p class="summary">This is a test news summary 1</p>
                <time class="published" datetime="2024-01-15T10:00:00">2024-01-15</time>
            </article>
            <article class="news-item">
                <h2 class="title">Test News Title 2</h2>
                <a class="link" href="https://example.com/news/2">Read more</a>
                <p class="summary">This is a test news summary 2</p>
                <time class="published" datetime="2024-01-15T11:00:00">2024-01-15</time>
            </article>
        </body>
    </html>
    """


class TestNewsCrawler:
    """NewsCrawler单元测试"""
    
    def test_init(self, sample_news_source):
        """测试初始化"""
        crawler = NewsCrawler([sample_news_source])
        
        assert len(crawler.sources) == 1
        assert crawler.timeout == 30
        assert crawler.max_concurrent == 10
        assert len(crawler.error_logs) == 0
    
    def test_init_with_custom_timeout(self, sample_news_source):
        """测试自定义超时时间"""
        crawler = NewsCrawler([sample_news_source], timeout=60)
        
        assert crawler.timeout == 60
    
    @pytest.mark.asyncio
    async def test_crawl_all_filters_disabled_sources(
        self,
        sample_news_source,
        disabled_news_source
    ):
        """测试crawl_all只处理启用的新闻源"""
        crawler = NewsCrawler([sample_news_source, disabled_news_source])
        
        # Mock crawl_source to return empty list
        with patch.object(crawler, 'crawl_source', new_callable=AsyncMock) as mock_crawl:
            mock_crawl.return_value = []
            
            await crawler.crawl_all()
            
            # 应该只调用一次（只处理启用的源）
            assert mock_crawl.call_count == 1
            # 验证调用的是启用的源
            called_source = mock_crawl.call_args[0][0]
            assert called_source.enabled is True
    
    @pytest.mark.asyncio
    async def test_crawl_all_returns_empty_when_no_enabled_sources(
        self,
        disabled_news_source
    ):
        """测试没有启用的新闻源时返回空列表"""
        crawler = NewsCrawler([disabled_news_source])
        
        result = await crawler.crawl_all()
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_crawl_source_success(self, sample_news_source, sample_html):
        """测试成功抓取新闻源"""
        crawler = NewsCrawler([sample_news_source])
        
        # Mock HTTP response
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_response = Mock()
            mock_response.text = sample_html
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = await crawler.crawl_source(sample_news_source)
            
            # 应该返回2条新闻
            assert len(result) == 2
            
            # 验证第一条新闻
            assert result[0].title == "Test News Title 1"
            assert result[0].summary == "This is a test news summary 1"
            assert result[0].url == "https://example.com/news/1"
            assert result[0].source_name == "Test News"
            
            # 验证第二条新闻
            assert result[1].title == "Test News Title 2"
            assert result[1].url == "https://example.com/news/2"
    
    @pytest.mark.asyncio
    async def test_crawl_source_timeout(self, sample_news_source):
        """测试抓取超时处理"""
        crawler = NewsCrawler([sample_news_source])
        
        # Mock timeout
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Timeout")
            
            result = await crawler.crawl_source(sample_news_source)
            
            # 应该返回空列表
            assert result == []
            
            # 应该记录错误日志
            assert len(crawler.error_logs) == 1
            assert crawler.error_logs[0].error_type == "network"
            assert crawler.error_logs[0].component == "crawler"
    
    @pytest.mark.asyncio
    async def test_crawl_source_http_error(self, sample_news_source):
        """测试HTTP错误处理"""
        crawler = NewsCrawler([sample_news_source])
        
        # Mock HTTP error
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection failed")
            
            result = await crawler.crawl_source(sample_news_source)
            
            # 应该返回空列表
            assert result == []
            
            # 应该记录错误日志
            assert len(crawler.error_logs) == 1
            assert crawler.error_logs[0].error_type == "network"
    
    @pytest.mark.asyncio
    async def test_crawl_source_parse_error(self, sample_news_source):
        """测试解析错误处理"""
        crawler = NewsCrawler([sample_news_source])
        
        # Mock invalid HTML
        invalid_html = "<html><body>Invalid content</body></html>"
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_response = Mock()
            mock_response.text = invalid_html
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = await crawler.crawl_source(sample_news_source)
            
            # 应该返回空列表（因为没有匹配的元素）
            assert result == []
    
    @pytest.mark.asyncio
    async def test_crawl_all_continues_on_single_source_failure(
        self,
        sample_news_source,
        sample_html
    ):
        """测试单个源失败不影响其他源"""
        # 创建两个新闻源
        source1 = sample_news_source
        source2 = NewsSource(
            id=str(uuid.uuid4()),
            name="Test News 2",
            url="https://example.com/news2",
            enabled=True,
            crawl_rules={"title": "h1"},
            timeout=30
        )
        
        crawler = NewsCrawler([source1, source2])
        
        # Mock第一个源失败，第二个源成功
        async def mock_crawl_source(source):
            if source.id == source1.id:
                raise Exception("Crawl failed")
            else:
                return [
                    NewsItem(
                        id=str(uuid.uuid4()),
                        title="News from source 2",
                        summary="Summary",
                        url="https://example.com/news2/1",
                        published_at=datetime.now(),
                        source_id=source2.id,
                        source_name=source2.name,
                        source_tags=[source2.name]
                    )
                ]
        
        with patch.object(crawler, 'crawl_source', side_effect=mock_crawl_source):
            result = await crawler.crawl_all()
            
            # 应该返回第二个源的结果
            assert len(result) == 1
            assert result[0].source_name == "Test News 2"
    
    def test_flatten_results(self, sample_news_source):
        """测试结果展平"""
        crawler = NewsCrawler([sample_news_source])
        
        news1 = NewsItem(
            id=str(uuid.uuid4()),
            title="News 1",
            summary="Summary 1",
            url="https://example.com/1",
            published_at=datetime.now(),
            source_id=sample_news_source.id,
            source_name=sample_news_source.name,
            source_tags=[sample_news_source.name]
        )
        
        news2 = NewsItem(
            id=str(uuid.uuid4()),
            title="News 2",
            summary="Summary 2",
            url="https://example.com/2",
            published_at=datetime.now(),
            source_id=sample_news_source.id,
            source_name=sample_news_source.name,
            source_tags=[sample_news_source.name]
        )
        
        # 测试包含列表、异常和None的结果
        results = [
            [news1],
            Exception("Error"),
            None,
            [news2]
        ]
        
        flattened = crawler._flatten_results(results)
        
        assert len(flattened) == 2
        assert flattened[0].title == "News 1"
        assert flattened[1].title == "News 2"
    
    def test_get_error_logs(self, sample_news_source):
        """测试获取错误日志"""
        crawler = NewsCrawler([sample_news_source])
        
        # 添加一些错误日志
        from src.models.error_log import ErrorLog
        
        error1 = ErrorLog.from_exception(
            error_type="network",
            component="crawler",
            operation="test",
            exception=Exception("Test error 1")
        )
        
        crawler.error_logs.append(error1)
        
        logs = crawler.get_error_logs()
        
        assert len(logs) == 1
        assert logs[0].error_type == "network"
    
    def test_clear_error_logs(self, sample_news_source):
        """测试清空错误日志"""
        crawler = NewsCrawler([sample_news_source])
        
        from src.models.error_log import ErrorLog
        
        error1 = ErrorLog.from_exception(
            error_type="network",
            component="crawler",
            operation="test",
            exception=Exception("Test error")
        )
        
        crawler.error_logs.append(error1)
        assert len(crawler.error_logs) == 1
        
        crawler.clear_error_logs()
        assert len(crawler.error_logs) == 0
    
    @pytest.mark.asyncio
    async def test_extract_news_item_with_relative_url(self, sample_news_source):
        """测试提取相对URL的新闻"""
        crawler = NewsCrawler([sample_news_source])
        
        html = """
        <html>
            <body>
                <article class="news-item">
                    <h2 class="title">Test Title</h2>
                    <a class="link" href="/relative/path">Link</a>
                    <p class="summary">Summary</p>
                </article>
            </body>
        </html>
        """
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_response = Mock()
            mock_response.text = html
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = await crawler.crawl_source(sample_news_source)
            
            assert len(result) == 1
            # 相对URL应该被转换为绝对URL
            assert result[0].url == "https://example.com/relative/path"
    
    @pytest.mark.asyncio
    async def test_extract_news_item_without_summary_uses_title(
        self,
        sample_news_source
    ):
        """测试没有摘要时使用标题作为摘要"""
        # 修改规则，移除summary选择器
        source = NewsSource(
            id=sample_news_source.id,
            name=sample_news_source.name,
            url=sample_news_source.url,
            enabled=True,
            crawl_rules={
                "container": "article.news-item",
                "title": "h2.title",
                "link": "a.link"
            },
            timeout=30
        )
        
        crawler = NewsCrawler([source])
        
        html = """
        <html>
            <body>
                <article class="news-item">
                    <h2 class="title">Test Title</h2>
                    <a class="link" href="/news/1">Link</a>
                </article>
            </body>
        </html>
        """
        
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_response = Mock()
            mock_response.text = html
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = await crawler.crawl_source(source)
            
            assert len(result) == 1
            # 摘要应该等于标题
            assert result[0].summary == result[0].title
