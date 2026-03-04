"""Unit tests for QwenLLMClient."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.ai.llm_client import QwenLLMClient, APIStats


class TestQwenLLMClient:
    """Test cases for QwenLLMClient."""

    def test_init_with_defaults(self):
        """Test initialization with default settings."""
        client = QwenLLMClient()
        assert client.api_key == "dummy"
        assert client.model == "qwen3.5-397b-a17b-fp8"
        assert client.stats.total_calls == 0

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        client = QwenLLMClient(
            api_key="test-key",
            endpoint="https://custom.endpoint.com"
        )
        assert client.api_key == "test-key"
        assert client.endpoint == "https://custom.endpoint.com"

    @pytest.mark.asyncio
    async def test_fallback_similarity_identical(self):
        """Test fallback similarity with identical texts."""
        client = QwenLLMClient()
        score = await client._fallback_similarity(
            "科技新闻",
            "科技新闻"
        )
        assert score > 0.5

    @pytest.mark.asyncio
    async def test_fallback_similarity_different(self):
        """Test fallback similarity with different texts."""
        client = QwenLLMClient()
        score = await client._fallback_similarity(
            "科技新闻",
            "体育比赛"
        )
        assert 0 <= score <= 1

    def test_fallback_classification_tech(self):
        """Test fallback classification for tech news."""
        client = QwenLLMClient()
        categories = client._fallback_classification(
            "人工智能技术发展",
            "AI技术取得重大突破"
        )
        assert "科技" in categories

    def test_fallback_classification_finance(self):
        """Test fallback classification for finance news."""
        client = QwenLLMClient()
        categories = client._fallback_classification(
            "股市行情",
            "股票市场上涨"
        )
        assert "金融" in categories

    def test_fallback_classification_unknown(self):
        """Test fallback classification for unknown category."""
        client = QwenLLMClient()
        categories = client._fallback_classification(
            "随机内容",
            "一些未知的话题"
        )
        assert categories == ["科技"]

    def test_get_stats(self):
        """Test getting API statistics."""
        client = QwenLLMClient()
        client.stats.total_calls = 10
        client.stats.successful_calls = 8
        client.stats.failed_calls = 2
        
        stats = client.get_stats()
        
        assert stats["total_calls"] == 10
        assert stats["successful_calls"] == 8
        assert stats["failed_calls"] == 2
        assert stats["success_rate"] == 0.8


class TestAPIStats:
    """Test cases for APIStats dataclass."""

    def test_default_values(self):
        """Test default stat values."""
        stats = APIStats()
        assert stats.total_calls == 0
        assert stats.successful_calls == 0
        assert stats.failed_calls == 0
        assert stats.total_tokens == 0