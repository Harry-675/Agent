"""Unit tests for error handlers."""

import pytest
from datetime import datetime, timedelta
from src.monitoring.error_handlers import (
    CrawlErrorHandler,
    LLMErrorHandler,
    DatabaseErrorHandler,
    ErrorTracker,
    ErrorRecord,
    ALERT_THRESHOLD
)


class TestCrawlErrorHandler:
    """Test cases for CrawlErrorHandler."""

    def test_init(self):
        """Test initialization."""
        handler = CrawlErrorHandler()
        assert handler.errors == []
        assert handler.error_counts == {}

    def test_handle_crawl_error(self):
        """Test handling crawl error."""
        handler = CrawlErrorHandler()
        
        error = Exception("Connection timeout")
        context = {"source_name": "test_source", "operation": "crawl"}
        
        handler.handle(error, context)
        
        assert len(handler.errors) == 1
        assert handler.error_counts["crawl"] == 1

    def test_alert_on_threshold(self):
        """Test alert triggers on threshold."""
        handler = CrawlErrorHandler()
        
        error = Exception("Connection error")
        for i in range(ALERT_THRESHOLD):
            handler.handle(error, {"source_name": "test_source"})
        
        assert handler.error_counts["source_test_source"] == ALERT_THRESHOLD


class TestLLMErrorHandler:
    """Test cases for LLMErrorHandler."""

    def test_init(self):
        """Test initialization."""
        handler = LLMErrorHandler()
        assert handler.fallback_mode is False

    def test_handle_llm_error(self):
        """Test handling LLM error."""
        handler = LLMErrorHandler()
        
        error = Exception("API error")
        context = {"operation": "classify"}
        
        handler.handle(error, context)
        
        assert handler.error_counts["llm"] == 1

    def test_fallback_mode_enabled(self):
        """Test fallback mode enables after threshold."""
        handler = LLMErrorHandler()
        
        error = Exception("API error")
        for i in range(ALERT_THRESHOLD):
            handler.handle(error, {})
        
        assert handler.fallback_mode is True

    def test_is_fallback_mode(self):
        """Test checking fallback mode."""
        handler = LLMErrorHandler()
        assert handler.is_fallback_mode() is False
        
        handler.fallback_mode = True
        assert handler.is_fallback_mode() is True


class TestDatabaseErrorHandler:
    """Test cases for DatabaseErrorHandler."""

    def test_init(self):
        """Test initialization."""
        handler = DatabaseErrorHandler()
        assert handler.errors == []

    def test_handle_db_error(self):
        """Test handling database error."""
        handler = DatabaseErrorHandler()
        
        error = Exception("Connection failed")
        context = {"operation": "query", "table": "news_items"}
        
        handler.handle(error, context)
        
        assert len(handler.errors) == 1
        assert handler.error_counts["database"] == 1


class TestErrorTracker:
    """Test cases for ErrorTracker."""

    def test_init(self):
        """Test initialization."""
        tracker = ErrorTracker()
        assert tracker.crawl_handler is not None
        assert tracker.llm_handler is not None
        assert tracker.db_handler is not None

    def test_track_error_crawl(self):
        """Test tracking crawl error."""
        tracker = ErrorTracker()
        
        error = Exception("timeout")
        tracker.track_error("crawl", error, {"source_name": "test"})
        
        status = tracker.get_system_status()
        assert status["crawl_errors"] >= 1

    def test_track_error_llm(self):
        """Test tracking LLM error."""
        tracker = ErrorTracker()
        
        error = Exception("API failed")
        tracker.track_error("llm", error, {})
        
        status = tracker.get_system_status()
        assert status["llm_errors"] >= 1

    def test_track_error_database(self):
        """Test tracking database error."""
        tracker = ErrorTracker()
        
        error = Exception("DB error")
        tracker.track_error("database", error, {})
        
        status = tracker.get_system_status()
        assert status["database_errors"] >= 1

    def test_get_recent_errors(self):
        """Test getting recent errors."""
        tracker = ErrorTracker()
        
        error = Exception("test")
        tracker.track_error("crawl", error, {})
        
        recent = tracker.get_recent_errors(minutes=60)
        assert len(recent) >= 1


class TestErrorRecord:
    """Test cases for ErrorRecord."""

    def test_init(self):
        """Test initialization."""
        record = ErrorRecord(
            timestamp=datetime.now(),
            error_type="crawl",
            component="crawler",
            message="test error"
        )
        
        assert record.error_type == "crawl"
        assert record.component == "crawler"
        assert record.count == 1