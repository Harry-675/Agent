"""Unit tests for configuration module."""

import pytest
from src.config import Settings, get_settings


def test_settings_default_values():
    """Test that settings have default values."""
    settings = Settings()
    
    assert settings.db_host == "localhost"
    assert settings.db_port == 5432
    assert settings.redis_host == "localhost"
    assert settings.redis_port == 6379
    assert settings.app_env == "development"
    assert settings.similarity_threshold == 0.85
    assert settings.crawler_timeout == 30


def test_get_settings_returns_same_instance():
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    
    assert settings1 is settings2


def test_settings_validation():
    """Test settings validation."""
    settings = Settings()
    
    # Verify numeric constraints
    assert settings.similarity_threshold >= 0.0
    assert settings.similarity_threshold <= 1.0
    assert settings.crawler_timeout > 0
    assert settings.dedup_timeout > 0
    assert settings.classification_timeout > 0
    assert settings.max_categories > 0
