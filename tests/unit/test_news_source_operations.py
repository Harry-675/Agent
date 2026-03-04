"""Unit tests for news source CRUD operations."""

import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import IntegrityError

from src.database.connection import Base
from src.database.operations import NewsSourceOperations, generate_source_id
from src.models.news_source import NewsSource


# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def session(engine):
    """Create test database session."""
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sample_news_source():
    """Create a sample news source for testing."""
    return NewsSource(
        id=str(uuid4()),
        name="Test News Source",
        url="https://example.com/news",
        enabled=True,
        crawl_rules={
            "title": ".article-title",
            "summary": ".article-summary",
            "link": ".article-link"
        },
        timeout=30
    )


@pytest.mark.asyncio
class TestNewsSourceOperations:
    """Test suite for NewsSourceOperations."""
    
    async def test_create_news_source(self, session, sample_news_source):
        """Test creating a new news source."""
        ops = NewsSourceOperations(session)
        
        created = await ops.create(sample_news_source)
        await session.commit()
        
        assert created.id == sample_news_source.id
        assert created.name == sample_news_source.name
        assert created.url == sample_news_source.url
        assert created.enabled == sample_news_source.enabled
    
    async def test_create_with_invalid_url(self, session):
        """Test creating a news source with invalid URL."""
        ops = NewsSourceOperations(session)
        
        invalid_source = NewsSource(
            id=str(uuid4()),
            name="Invalid Source",
            url="not-a-valid-url",
            enabled=True,
            crawl_rules={"title": ".title"},
            timeout=30
        )
        
        with pytest.raises(ValueError, match="Invalid URL"):
            await ops.create(invalid_source)
    
    async def test_create_with_invalid_crawl_rules(self, session):
        """Test creating a news source with invalid crawl rules."""
        ops = NewsSourceOperations(session)
        
        invalid_source = NewsSource(
            id=str(uuid4()),
            name="Invalid Source",
            url="https://example.com",
            enabled=True,
            crawl_rules={},  # Missing 'title' key
            timeout=30
        )
        
        with pytest.raises(ValueError, match="Invalid crawl rules"):
            await ops.create(invalid_source)
    
    async def test_create_duplicate_id(self, session, sample_news_source):
        """Test creating a news source with duplicate ID."""
        ops = NewsSourceOperations(session)
        
        # Create first source
        await ops.create(sample_news_source)
        await session.commit()
        
        # Try to create another with same ID
        duplicate = NewsSource(
            id=sample_news_source.id,  # Same ID
            name="Duplicate Source",
            url="https://different.com",
            enabled=True,
            crawl_rules={"title": ".title"},
            timeout=30
        )
        
        with pytest.raises(IntegrityError):
            await ops.create(duplicate)
    
    async def test_get_by_id(self, session, sample_news_source):
        """Test retrieving a news source by ID."""
        ops = NewsSourceOperations(session)
        
        # Create source
        await ops.create(sample_news_source)
        await session.commit()
        
        # Retrieve source
        retrieved = await ops.get_by_id(sample_news_source.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_news_source.id
        assert retrieved.name == sample_news_source.name
        assert retrieved.url == sample_news_source.url
    
    async def test_get_by_id_not_found(self, session):
        """Test retrieving a non-existent news source."""
        ops = NewsSourceOperations(session)
        
        retrieved = await ops.get_by_id("non-existent-id")
        
        assert retrieved is None
    
    async def test_get_all(self, session):
        """Test retrieving all news sources."""
        ops = NewsSourceOperations(session)
        
        # Create multiple sources
        source1 = NewsSource(
            id=str(uuid4()),
            name="Source 1",
            url="https://example1.com",
            enabled=True,
            crawl_rules={"title": ".title"},
            timeout=30
        )
        source2 = NewsSource(
            id=str(uuid4()),
            name="Source 2",
            url="https://example2.com",
            enabled=False,
            crawl_rules={"title": ".title"},
            timeout=30
        )
        
        await ops.create(source1)
        await ops.create(source2)
        await session.commit()
        
        # Get all sources
        all_sources = await ops.get_all()
        
        assert len(all_sources) == 2
        assert any(s.id == source1.id for s in all_sources)
        assert any(s.id == source2.id for s in all_sources)
    
    async def test_get_all_enabled_only(self, session):
        """Test retrieving only enabled news sources."""
        ops = NewsSourceOperations(session)
        
        # Create enabled and disabled sources
        enabled_source = NewsSource(
            id=str(uuid4()),
            name="Enabled Source",
            url="https://enabled.com",
            enabled=True,
            crawl_rules={"title": ".title"},
            timeout=30
        )
        disabled_source = NewsSource(
            id=str(uuid4()),
            name="Disabled Source",
            url="https://disabled.com",
            enabled=False,
            crawl_rules={"title": ".title"},
            timeout=30
        )
        
        await ops.create(enabled_source)
        await ops.create(disabled_source)
        await session.commit()
        
        # Get only enabled sources
        enabled_sources = await ops.get_all(enabled_only=True)
        
        assert len(enabled_sources) == 1
        assert enabled_sources[0].id == enabled_source.id
        assert enabled_sources[0].enabled is True
    
    async def test_update_news_source(self, session, sample_news_source):
        """Test updating a news source."""
        ops = NewsSourceOperations(session)
        
        # Create source
        await ops.create(sample_news_source)
        await session.commit()
        
        # Update source
        updated = await ops.update(
            sample_news_source.id,
            name="Updated Name",
            url="https://updated.com"
        )
        await session.commit()
        
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.url == "https://updated.com"
        assert updated.id == sample_news_source.id
    
    async def test_update_with_invalid_url(self, session, sample_news_source):
        """Test updating a news source with invalid URL."""
        ops = NewsSourceOperations(session)
        
        # Create source
        await ops.create(sample_news_source)
        await session.commit()
        
        # Try to update with invalid URL
        with pytest.raises(ValueError, match="Invalid URL"):
            await ops.update(sample_news_source.id, url="invalid-url")
    
    async def test_update_not_found(self, session):
        """Test updating a non-existent news source."""
        ops = NewsSourceOperations(session)
        
        updated = await ops.update("non-existent-id", name="New Name")
        
        assert updated is None
    
    async def test_delete_news_source(self, session, sample_news_source):
        """Test deleting a news source."""
        ops = NewsSourceOperations(session)
        
        # Create source
        await ops.create(sample_news_source)
        await session.commit()
        
        # Delete source
        deleted = await ops.delete(sample_news_source.id)
        await session.commit()
        
        assert deleted is True
        
        # Verify deletion
        retrieved = await ops.get_by_id(sample_news_source.id)
        assert retrieved is None
    
    async def test_delete_not_found(self, session):
        """Test deleting a non-existent news source."""
        ops = NewsSourceOperations(session)
        
        deleted = await ops.delete("non-existent-id")
        
        assert deleted is False
    
    async def test_toggle_enabled(self, session, sample_news_source):
        """Test toggling the enabled status."""
        ops = NewsSourceOperations(session)
        
        # Create source (enabled=True)
        await ops.create(sample_news_source)
        await session.commit()
        
        # Toggle to disabled
        toggled = await ops.toggle_enabled(sample_news_source.id)
        await session.commit()
        
        assert toggled is not None
        assert toggled.enabled is False
        
        # Toggle back to enabled
        toggled_again = await ops.toggle_enabled(sample_news_source.id)
        await session.commit()
        
        assert toggled_again is not None
        assert toggled_again.enabled is True
    
    async def test_toggle_enabled_not_found(self, session):
        """Test toggling enabled status for non-existent source."""
        ops = NewsSourceOperations(session)
        
        toggled = await ops.toggle_enabled("non-existent-id")
        
        assert toggled is None
    
    async def test_set_enabled(self, session, sample_news_source):
        """Test setting the enabled status."""
        ops = NewsSourceOperations(session)
        
        # Create source (enabled=True)
        await ops.create(sample_news_source)
        await session.commit()
        
        # Set to disabled
        updated = await ops.set_enabled(sample_news_source.id, False)
        await session.commit()
        
        assert updated is not None
        assert updated.enabled is False
        
        # Set to enabled
        updated_again = await ops.set_enabled(sample_news_source.id, True)
        await session.commit()
        
        assert updated_again is not None
        assert updated_again.enabled is True
    
    async def test_set_enabled_not_found(self, session):
        """Test setting enabled status for non-existent source."""
        ops = NewsSourceOperations(session)
        
        updated = await ops.set_enabled("non-existent-id", True)
        
        assert updated is None


def test_generate_source_id():
    """Test generating unique source IDs."""
    id1 = generate_source_id()
    id2 = generate_source_id()
    
    assert id1 != id2
    assert len(id1) == 36  # UUID format
    assert len(id2) == 36
