"""Unit tests for DeduplicationEngine."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from src.ai.deduplication import DeduplicationEngine
from src.models.news_item import NewsItem


class TestDeduplicationEngine:
    """Test cases for DeduplicationEngine."""

    def test_init_with_defaults(self):
        """Test initialization with default settings."""
        engine = DeduplicationEngine()
        assert engine.threshold == 0.85
        assert engine.timeout == 5

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        engine = DeduplicationEngine(
            threshold=0.9,
            timeout=10
        )
        assert engine.threshold == 0.9
        assert engine.timeout == 10

    @pytest.mark.asyncio
    async def test_find_duplicates_empty(self):
        """Test find_duplicates with empty list."""
        engine = DeduplicationEngine()
        result = await engine.find_duplicates([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_find_duplicates_single_item(self):
        """Test find_duplicates with single item."""
        engine = DeduplicationEngine()
        item = NewsItem(
            id="1",
            title="Test",
            summary="Summary",
            url="https://example.com",
            published_at=datetime.now(),
            source_id="s1",
            source_name="Source1"
        )
        result = await engine.find_duplicates([item])
        assert result == {}

    @pytest.mark.asyncio
    async def test_merge_duplicates_empty(self):
        """Test merge_duplicates with empty dict."""
        engine = DeduplicationEngine()
        result = await engine.merge_duplicates({})
        assert result == []

    def test_merge_group_earliest_published(self):
        """Test _merge_group keeps earliest published item."""
        engine = DeduplicationEngine()
        
        old_item = NewsItem(
            id="1",
            title="Test",
            summary="Summary",
            url="https://example.com/old",
            published_at=datetime(2024, 1, 1),
            source_id="s1",
            source_name="Source1",
            source_tags=["Source1"]
        )
        
        new_item = NewsItem(
            id="2",
            title="Test",
            summary="Summary",
            url="https://example.com/new",
            published_at=datetime(2024, 1, 2),
            source_id="s2",
            source_name="Source2",
            source_tags=["Source2"]
        )
        
        merged = engine._merge_group([new_item, old_item])
        
        assert merged.published_at == datetime(2024, 1, 1)
        assert "Source1" in merged.source_tags
        assert "Source2" in merged.source_tags

    def test_is_duplicate_same_group(self):
        """Test is_duplicate with same group."""
        engine = DeduplicationEngine()
        
        item1 = NewsItem(
            id="1",
            title="Test",
            summary="Summary",
            url="https://example.com/1",
            published_at=datetime.now(),
            source_id="s1",
            source_name="Source1",
            duplicate_group_id="group1"
        )
        
        item2 = NewsItem(
            id="2",
            title="Test",
            summary="Summary",
            url="https://example.com/2",
            published_at=datetime.now(),
            source_id="s2",
            source_name="Source2",
            duplicate_group_id="group1"
        )
        
        assert engine.is_duplicate(item1, item2) is True

    def test_is_duplicate_different_group(self):
        """Test is_duplicate with different groups."""
        engine = DeduplicationEngine()
        
        item1 = NewsItem(
            id="1",
            title="Test",
            summary="Summary",
            url="https://example.com/1",
            published_at=datetime.now(),
            source_id="s1",
            source_name="Source1",
            duplicate_group_id="group1"
        )
        
        item2 = NewsItem(
            id="2",
            title="Different",
            summary="Summary",
            url="https://example.com/2",
            published_at=datetime.now(),
            source_id="s2",
            source_name="Source2",
            duplicate_group_id="group2"
        )
        
        assert engine.is_duplicate(item1, item2) is False