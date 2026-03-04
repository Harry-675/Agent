"""Unit tests for data models."""

import pytest
from datetime import datetime
from src.models import NewsSource, NewsItem, ErrorLog


class TestNewsSource:
    """Tests for NewsSource model."""
    
    def test_valid_news_source(self):
        """Test creating a valid news source."""
        source = NewsSource(
            id="test-source-1",
            name="Test News",
            url="https://example.com/news",
            enabled=True,
            crawl_rules={"title": ".article-title", "summary": ".article-summary"}
        )
        
        assert source.validate()
        assert source.validate_url()
        assert source.validate_crawl_rules()
    
    def test_invalid_url_no_scheme(self):
        """Test URL validation with missing scheme."""
        source = NewsSource(
            id="test-source-2",
            name="Test News",
            url="example.com/news",
            enabled=True,
            crawl_rules={"title": ".title"}
        )
        
        assert not source.validate_url()
        assert not source.validate()
    
    def test_invalid_url_wrong_scheme(self):
        """Test URL validation with wrong scheme."""
        source = NewsSource(
            id="test-source-3",
            name="Test News",
            url="ftp://example.com/news",
            enabled=True,
            crawl_rules={"title": ".title"}
        )
        
        assert not source.validate_url()
        assert not source.validate()
    
    def test_invalid_crawl_rules_missing_title(self):
        """Test crawl rules validation without title."""
        source = NewsSource(
            id="test-source-4",
            name="Test News",
            url="https://example.com/news",
            enabled=True,
            crawl_rules={"summary": ".summary"}
        )
        
        assert not source.validate_crawl_rules()
        assert not source.validate()
    
    def test_invalid_crawl_rules_empty_value(self):
        """Test crawl rules validation with empty value."""
        source = NewsSource(
            id="test-source-5",
            name="Test News",
            url="https://example.com/news",
            enabled=True,
            crawl_rules={"title": ""}
        )
        
        assert not source.validate_crawl_rules()
        assert not source.validate()


class TestNewsItem:
    """Tests for NewsItem model."""
    
    def test_valid_news_item(self):
        """Test creating a valid news item."""
        item = NewsItem(
            id="news-1",
            title="Test News Title",
            summary="This is a test news summary.",
            url="https://example.com/news/1",
            published_at=datetime.now(),
            source_id="source-1",
            source_name="Test Source",
            categories=["科技"],
            source_tags=["Test Source"]
        )
        
        assert item.validate()
        assert item.validate_required_fields()
        assert item.validate_categories()
        assert item.validate_source_tags()
    
    def test_valid_news_item_multiple_categories(self):
        """Test news item with multiple categories."""
        item = NewsItem(
            id="news-2",
            title="Test News",
            summary="Summary",
            url="https://example.com/news/2",
            published_at=datetime.now(),
            source_id="source-1",
            source_name="Test Source",
            categories=["科技", "金融"],
            source_tags=["Test Source"]
        )
        
        assert item.validate()
        assert len(item.categories) == 2
    
    def test_invalid_categories_too_many(self):
        """Test news item with too many categories."""
        item = NewsItem(
            id="news-3",
            title="Test News",
            summary="Summary",
            url="https://example.com/news/3",
            published_at=datetime.now(),
            source_id="source-1",
            source_name="Test Source",
            categories=["科技", "金融", "体育", "娱乐"],
            source_tags=["Test Source"]
        )
        
        assert not item.validate_categories()
        assert not item.validate()
    
    def test_invalid_categories_empty(self):
        """Test news item with no categories."""
        item = NewsItem(
            id="news-4",
            title="Test News",
            summary="Summary",
            url="https://example.com/news/4",
            published_at=datetime.now(),
            source_id="source-1",
            source_name="Test Source",
            categories=[],
            source_tags=["Test Source"]
        )
        
        assert not item.validate_categories()
        assert not item.validate()
    
    def test_invalid_category_not_in_valid_set(self):
        """Test news item with invalid category."""
        item = NewsItem(
            id="news-5",
            title="Test News",
            summary="Summary",
            url="https://example.com/news/5",
            published_at=datetime.now(),
            source_id="source-1",
            source_name="Test Source",
            categories=["无效分类"],
            source_tags=["Test Source"]
        )
        
        assert not item.validate_categories()
        assert not item.validate()
    
    def test_add_source_tag(self):
        """Test adding source tags."""
        item = NewsItem(
            id="news-6",
            title="Test News",
            summary="Summary",
            url="https://example.com/news/6",
            published_at=datetime.now(),
            source_id="source-1",
            source_name="Source 1",
            categories=["科技"],
            source_tags=["Source 1"]
        )
        
        item.add_source_tag("Source 2")
        assert "Source 2" in item.source_tags
        assert len(item.source_tags) == 2
        
        # Adding duplicate should not increase count
        item.add_source_tag("Source 1")
        assert len(item.source_tags) == 2
    
    def test_merge_with(self):
        """Test merging news items."""
        item1 = NewsItem(
            id="news-7",
            title="Test News",
            summary="Summary",
            url="https://example.com/news/7",
            published_at=datetime.now(),
            source_id="source-1",
            source_name="Source 1",
            categories=["科技"],
            source_tags=["Source 1"]
        )
        
        item2 = NewsItem(
            id="news-8",
            title="Test News",
            summary="Summary",
            url="https://example.com/news/8",
            published_at=datetime.now(),
            source_id="source-2",
            source_name="Source 2",
            categories=["科技"],
            source_tags=["Source 2"]
        )
        
        item1.merge_with(item2)
        assert "Source 2" in item1.source_tags
        assert len(item1.source_tags) == 2
        assert item1.duplicate_group_id == item1.id


class TestErrorLog:
    """Tests for ErrorLog model."""
    
    def test_valid_error_log(self):
        """Test creating a valid error log."""
        log = ErrorLog(
            timestamp=datetime.now(),
            error_type="network",
            component="crawler",
            operation="fetch_news",
            error_message="Connection timeout",
            stack_trace="Traceback...",
            context={"url": "https://example.com"}
        )
        
        assert log.validate()
        assert log.validate_error_type()
        assert log.validate_component()
        assert log.validate_required_fields()
    
    def test_invalid_error_type(self):
        """Test error log with invalid error type."""
        log = ErrorLog(
            timestamp=datetime.now(),
            error_type="invalid_type",
            component="crawler",
            operation="fetch_news",
            error_message="Error"
        )
        
        assert not log.validate_error_type()
        assert not log.validate()
    
    def test_invalid_component(self):
        """Test error log with invalid component."""
        log = ErrorLog(
            timestamp=datetime.now(),
            error_type="network",
            component="invalid_component",
            operation="fetch_news",
            error_message="Error"
        )
        
        assert not log.validate_component()
        assert not log.validate()
    
    def test_from_exception(self):
        """Test creating error log from exception."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            log = ErrorLog.from_exception(
                error_type="system",
                component="crawler",
                operation="test_operation",
                exception=e,
                context={"test": "data"}
            )
            
            assert log.error_message == "Test error"
            assert log.error_type == "system"
            assert log.component == "crawler"
            assert "ValueError" in log.stack_trace
            assert log.context["test"] == "data"
    
    def test_to_dict(self):
        """Test converting error log to dictionary."""
        log = ErrorLog(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            error_type="network",
            component="crawler",
            operation="fetch_news",
            error_message="Connection timeout"
        )
        
        result = log.to_dict()
        assert result["error_type"] == "network"
        assert result["component"] == "crawler"
        assert result["operation"] == "fetch_news"
        assert result["error_message"] == "Connection timeout"
        assert "timestamp" in result
