"""Unit tests for CategoryClassifier."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from src.ai.classification import CategoryClassifier, VALID_CATEGORIES
from src.models.news_item import NewsItem


class TestCategoryClassifier:
    """Test cases for CategoryClassifier."""

    def test_init_with_defaults(self):
        """Test initialization with default settings."""
        classifier = CategoryClassifier()
        assert classifier.timeout == 3
        assert classifier.max_categories == 3

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        classifier = CategoryClassifier(
            timeout=10,
            max_categories=2
        )
        assert classifier.timeout == 10
        assert classifier.max_categories == 2

    def test_validate_categories_valid(self):
        """Test _validate_categories with valid categories."""
        classifier = CategoryClassifier()
        result = classifier._validate_categories(["科技", "金融"])
        assert result == ["科技", "金融"]

    def test_validate_categories_exceeds_max(self):
        """Test _validate_categories limits to max."""
        classifier = CategoryClassifier(max_categories=2)
        result = classifier._validate_categories(["科技", "金融", "体育", "娱乐"])
        assert len(result) == 2

    def test_validate_categories_filters_invalid(self):
        """Test _validate_categories filters invalid."""
        classifier = CategoryClassifier()
        result = classifier._validate_categories(["科技", "未知分类", "金融"])
        assert result == ["科技", "金融"]

    def test_validate_categories_empty(self):
        """Test _validate_categories with empty list."""
        classifier = CategoryClassifier()
        result = classifier._validate_categories([])
        assert result == []

    def test_fallback_classify_tech(self):
        """Test fallback classification for tech."""
        classifier = CategoryClassifier()
        item = NewsItem(
            id="1",
            title="人工智能技术发展",
            summary="AI技术取得重大突破",
            url="https://example.com",
            published_at=datetime.now(),
            source_id="s1",
            source_name="Source1"
        )
        result = classifier._fallback_classify(item)
        assert "科技" in result

    def test_fallback_classify_finance(self):
        """Test fallback classification for finance."""
        classifier = CategoryClassifier()
        item = NewsItem(
            id="1",
            title="股市行情上涨",
            summary="股票市场表现强劲",
            url="https://example.com",
            published_at=datetime.now(),
            source_id="s1",
            source_name="Source1"
        )
        result = classifier._fallback_classify(item)
        assert "金融" in result

    def test_fallback_classify_sports(self):
        """Test fallback classification for sports."""
        classifier = CategoryClassifier()
        item = NewsItem(
            id="1",
            title="足球比赛",
            summary="世界杯决赛",
            url="https://example.com",
            published_at=datetime.now(),
            source_id="s1",
            source_name="Source1"
        )
        result = classifier._fallback_classify(item)
        assert "体育" in result

    def test_fallback_classify_entertainment(self):
        """Test fallback classification for entertainment."""
        classifier = CategoryClassifier()
        item = NewsItem(
            id="1",
            title="电影上映",
            summary="新电影票房大卖",
            url="https://example.com",
            published_at=datetime.now(),
            source_id="s1",
            source_name="Source1"
        )
        result = classifier._fallback_classify(item)
        assert "娱乐" in result

    def test_fallback_classify_unknown(self):
        """Test fallback classification for unknown content."""
        classifier = CategoryClassifier()
        item = NewsItem(
            id="1",
            title="随机内容",
            summary="一些未知的话题",
            url="https://example.com",
            published_at=datetime.now(),
            source_id="s1",
            source_name="Source1"
        )
        result = classifier._fallback_classify(item)
        assert result == ["科技"]

    def test_get_valid_categories(self):
        """Test getting valid categories set."""
        classifier = CategoryClassifier()
        categories = classifier.get_valid_categories()
        assert categories == VALID_CATEGORIES
        assert "科技" in categories
        assert "金融" in categories