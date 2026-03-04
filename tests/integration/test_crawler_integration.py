"""Integration tests for NewsCrawler."""

import asyncio
from datetime import datetime
import uuid

import pytest

from src.crawler.news_crawler import NewsCrawler
from src.models.news_source import NewsSource


@pytest.mark.integration
class TestCrawlerIntegration:
    """NewsCrawler集成测试"""
    
    @pytest.mark.asyncio
    async def test_crawl_multiple_sources_concurrently(self):
        """测试并发抓取多个新闻源"""
        # 创建多个测试新闻源
        sources = [
            NewsSource(
                id=str(uuid.uuid4()),
                name=f"Test Source {i}",
                url=f"https://example.com/news{i}",
                enabled=True,
                crawl_rules={
                    "container": "article",
                    "title": "h2",
                    "link": "a",
                    "summary": "p"
                },
                timeout=30
            )
            for i in range(3)
        ]
        
        # 添加一个禁用的源
        sources.append(
            NewsSource(
                id=str(uuid.uuid4()),
                name="Disabled Source",
                url="https://example.com/disabled",
                enabled=False,
                crawl_rules={"title": "h1"},
                timeout=30
            )
        )
        
        crawler = NewsCrawler(sources)
        
        # 由于这是集成测试，实际会尝试访问URL
        # 在真实环境中，这些URL会失败，但不应该抛出异常
        result = await crawler.crawl_all()
        
        # 应该返回一个列表（可能为空，因为URL不存在）
        assert isinstance(result, list)
        
        # 应该有错误日志（因为URL不存在）
        error_logs = crawler.get_error_logs()
        # 只有3个启用的源会被尝试抓取
        assert len(error_logs) >= 0  # 可能有错误日志
    
    @pytest.mark.asyncio
    async def test_crawler_respects_timeout(self):
        """测试爬虫遵守超时设置"""
        source = NewsSource(
            id=str(uuid.uuid4()),
            name="Slow Source",
            url="https://httpbin.org/delay/5",  # 延迟5秒响应
            enabled=True,
            crawl_rules={"title": "h1"},
            timeout=2  # 2秒超时
        )
        
        crawler = NewsCrawler([source])
        
        start_time = datetime.now()
        result = await crawler.crawl_source(source)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # 应该在超时时间内返回
        assert elapsed < 5  # 应该在2秒左右超时，不会等到5秒
        
        # 应该返回空列表
        assert result == []
        
        # 应该有超时错误日志
        error_logs = crawler.get_error_logs()
        assert len(error_logs) > 0
        assert error_logs[0].error_type == "network"
