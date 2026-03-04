"""Database CRUD operations for news sources and items."""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.models.news_source import NewsSource
from src.models.news_item import NewsItem
from src.database.models import NewsSourceModel, NewsItemModel


class NewsSourceOperations:
    """CRUD operations for news sources."""
    
    def __init__(self, session: AsyncSession):
        """Initialize with database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.session = session
    
    async def create(self, news_source: NewsSource) -> NewsSource:
        """Create a new news source.
        
        Args:
            news_source: NewsSource object to create
            
        Returns:
            Created NewsSource object
            
        Raises:
            ValueError: If URL validation fails
            IntegrityError: If news source with same ID already exists
        """
        # Validate URL before creating
        if not news_source.validate_url():
            raise ValueError(f"Invalid URL: {news_source.url}")
        
        # Validate crawl rules
        if not news_source.validate_crawl_rules():
            raise ValueError("Invalid crawl rules")
        
        try:
            # Create ORM model
            db_source = NewsSourceModel(
                id=news_source.id,
                name=news_source.name,
                url=news_source.url,
                enabled=news_source.enabled,
                crawl_rules=news_source.crawl_rules,
                timeout=news_source.timeout,
                created_at=news_source.created_at,
                updated_at=news_source.updated_at
            )
            
            self.session.add(db_source)
            await self.session.flush()
            
            return news_source
        except IntegrityError as e:
            await self.session.rollback()
            raise IntegrityError(
                f"News source with ID {news_source.id} already exists",
                params=None,
                orig=e.orig
            )
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(f"Database error: {str(e)}")
    
    async def get_by_id(self, source_id: str) -> Optional[NewsSource]:
        """Get a news source by ID.
        
        Args:
            source_id: News source ID
            
        Returns:
            NewsSource object if found, None otherwise
        """
        try:
            stmt = select(NewsSourceModel).where(NewsSourceModel.id == source_id)
            result = await self.session.execute(stmt)
            db_source = result.scalar_one_or_none()
            
            if db_source is None:
                return None
            
            return self._to_domain_model(db_source)
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")
    
    async def get_all(self, enabled_only: bool = False) -> List[NewsSource]:
        """Get all news sources.
        
        Args:
            enabled_only: If True, only return enabled sources
            
        Returns:
            List of NewsSource objects
        """
        try:
            stmt = select(NewsSourceModel)
            if enabled_only:
                stmt = stmt.where(NewsSourceModel.enabled == True)
            
            result = await self.session.execute(stmt)
            db_sources = result.scalars().all()
            
            return [self._to_domain_model(db_source) for db_source in db_sources]
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")
    
    async def update(self, source_id: str, **kwargs) -> Optional[NewsSource]:
        """Update a news source.
        
        Args:
            source_id: News source ID
            **kwargs: Fields to update (name, url, enabled, crawl_rules, timeout)
            
        Returns:
            Updated NewsSource object if found, None otherwise
            
        Raises:
            ValueError: If URL validation fails
        """
        try:
            # Get existing source
            existing = await self.get_by_id(source_id)
            if existing is None:
                return None
            
            # Validate URL if being updated
            if 'url' in kwargs:
                # Create temporary source to validate URL
                temp_source = NewsSource(
                    id=source_id,
                    name=existing.name,
                    url=kwargs['url'],
                    enabled=existing.enabled,
                    crawl_rules=existing.crawl_rules,
                    timeout=existing.timeout
                )
                if not temp_source.validate_url():
                    raise ValueError(f"Invalid URL: {kwargs['url']}")
            
            # Validate crawl rules if being updated
            if 'crawl_rules' in kwargs:
                temp_source = NewsSource(
                    id=source_id,
                    name=existing.name,
                    url=existing.url,
                    enabled=existing.enabled,
                    crawl_rules=kwargs['crawl_rules'],
                    timeout=existing.timeout
                )
                if not temp_source.validate_crawl_rules():
                    raise ValueError("Invalid crawl rules")
            
            # Update timestamp
            kwargs['updated_at'] = datetime.now()
            
            # Perform update
            stmt = (
                update(NewsSourceModel)
                .where(NewsSourceModel.id == source_id)
                .values(**kwargs)
            )
            await self.session.execute(stmt)
            await self.session.flush()
            
            # Return updated source
            return await self.get_by_id(source_id)
        except ValueError:
            raise
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(f"Database error: {str(e)}")
    
    async def delete(self, source_id: str) -> bool:
        """Delete a news source.
        
        Args:
            source_id: News source ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            stmt = delete(NewsSourceModel).where(NewsSourceModel.id == source_id)
            result = await self.session.execute(stmt)
            await self.session.flush()
            
            return result.rowcount > 0
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(f"Database error: {str(e)}")
    
    async def toggle_enabled(self, source_id: str) -> Optional[NewsSource]:
        """Toggle the enabled status of a news source.
        
        Args:
            source_id: News source ID
            
        Returns:
            Updated NewsSource object if found, None otherwise
        """
        try:
            # Get current source
            existing = await self.get_by_id(source_id)
            if existing is None:
                return None
            
            # Toggle enabled status
            new_enabled = not existing.enabled
            return await self.update(source_id, enabled=new_enabled)
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(f"Database error: {str(e)}")
    
    async def set_enabled(self, source_id: str, enabled: bool) -> Optional[NewsSource]:
        """Set the enabled status of a news source.
        
        Args:
            source_id: News source ID
            enabled: New enabled status
            
        Returns:
            Updated NewsSource object if found, None otherwise
        """
        return await self.update(source_id, enabled=enabled)
    
    def _to_domain_model(self, db_source: NewsSourceModel) -> NewsSource:
        """Convert ORM model to domain model.
        
        Args:
            db_source: NewsSourceModel ORM object
            
        Returns:
            NewsSource domain object
        """
        return NewsSource(
            id=db_source.id,
            name=db_source.name,
            url=db_source.url,
            enabled=db_source.enabled,
            crawl_rules=db_source.crawl_rules,
            timeout=db_source.timeout,
            created_at=db_source.created_at,
            updated_at=db_source.updated_at
        )


def generate_source_id() -> str:
    """Generate a unique ID for a news source.
    
    Returns:
        UUID string
    """
    return str(uuid4())


class NewsItemOperations:
    """CRUD operations for news items."""
    
    def __init__(self, session: AsyncSession):
        """Initialize with database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self.session = session
    
    async def create(self, news_item: NewsItem) -> NewsItem:
        """Create a new news item.
        
        Args:
            news_item: NewsItem object to create
            
        Returns:
            Created NewsItem object
        """
        try:
            db_item = NewsItemModel(
                id=news_item.id,
                title=news_item.title,
                summary=news_item.summary,
                url=news_item.url,
                published_at=news_item.published_at,
                source_id=news_item.source_id,
                source_name=news_item.source_name,
                categories=news_item.categories,
                duplicate_group_id=news_item.duplicate_group_id,
                source_tags=news_item.source_tags,
                created_at=news_item.created_at,
                updated_at=news_item.updated_at
            )
            
            self.session.add(db_item)
            await self.session.flush()
            
            return news_item
        except IntegrityError as e:
            await self.session.rollback()
            raise
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(f"Database error: {str(e)}")
    
    async def get_by_id(self, item_id: str) -> Optional[NewsItem]:
        """Get a news item by ID.
        
        Args:
            item_id: News item ID
            
        Returns:
            NewsItem object if found, None otherwise
        """
        try:
            from src.database.models import NewsItemModel
            stmt = select(NewsItemModel).where(NewsItemModel.id == item_id)
            result = await self.session.execute(stmt)
            db_item = result.scalar_one_or_none()
            
            if db_item is None:
                return None
            
            return self._to_domain_model(db_item)
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")
    
    async def get_all(
        self,
        category: Optional[str] = None,
        source_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[NewsItem]:
        """Get all news items with optional filtering.
        
        Args:
            category: Filter by category
            source_name: Filter by source name
            limit: Maximum items to return
            offset: Number of items to skip
            
        Returns:
            List of NewsItem objects
        """
        try:
            from src.database.models import NewsItemModel
            stmt = select(NewsItemModel).order_by(NewsItemModel.published_at.desc())
            
            if category:
                stmt = stmt.where(NewsItemModel.categories.contains(category))
            
            if source_name:
                stmt = stmt.where(NewsItemModel.source_name == source_name)
            
            stmt = stmt.limit(limit).offset(offset)
            
            result = await self.session.execute(stmt)
            db_items = result.scalars().all()
            
            return [self._to_domain_model(db_item) for db_item in db_items]
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")
    
    async def get_by_duplicate_group(
        self,
        group_id: str
    ) -> List[NewsItem]:
        """Get all news items in a duplicate group.
        
        Args:
            group_id: Duplicate group ID
            
        Returns:
            List of NewsItem objects in the group
        """
        try:
            from src.database.models import NewsItemModel
            stmt = select(NewsItemModel).where(
                NewsItemModel.duplicate_group_id == group_id
            )
            
            result = await self.session.execute(stmt)
            db_items = result.scalars().all()
            
            return [self._to_domain_model(db_item) for db_item in db_items]
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error: {str(e)}")
    
    async def update(
        self,
        item_id: str,
        **kwargs
    ) -> Optional[NewsItem]:
        """Update a news item.
        
        Args:
            item_id: News item ID
            **kwargs: Fields to update
            
        Returns:
            Updated NewsItem object if found, None otherwise
        """
        try:
            from src.database.models import NewsItemModel
            kwargs['updated_at'] = datetime.now()
            
            stmt = (
                update(NewsItemModel)
                .where(NewsItemModel.id == item_id)
                .values(**kwargs)
            )
            await self.session.execute(stmt)
            await self.session.flush()
            
            return await self.get_by_id(item_id)
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(f"Database error: {str(e)}")
    
    async def delete(self, item_id: str) -> bool:
        """Delete a news item.
        
        Args:
            item_id: News item ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            from src.database.models import NewsItemModel
            stmt = delete(NewsItemModel).where(NewsItemModel.id == item_id)
            result = await self.session.execute(stmt)
            await self.session.flush()
            
            return result.rowcount > 0
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(f"Database error: {str(e)}")
    
    async def delete_older_than(self, days: int) -> int:
        """Delete news items older than specified days.
        
        Implements data retention policy.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of deleted items
        """
        try:
            from src.database.models import NewsItemModel
            cutoff_date = datetime.now() - timedelta(days=days)
            
            stmt = delete(NewsItemModel).where(
                NewsItemModel.published_at < cutoff_date
            )
            result = await self.session.execute(stmt)
            await self.session.flush()
            
            return result.rowcount
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise RuntimeError(f"Database error: {str(e)}")
    
    def _to_domain_model(self, db_item: NewsItemModel) -> NewsItem:
        """Convert ORM model to domain model.
        
        Args:
            db_item: NewsItemModel ORM object
            
        Returns:
            NewsItem domain object
        """
        return NewsItem(
            id=db_item.id,
            title=db_item.title,
            summary=db_item.summary or "",
            url=db_item.url,
            published_at=db_item.published_at,
            source_id=db_item.source_id or "",
            source_name=db_item.source_name,
            categories=db_item.categories or [],
            duplicate_group_id=db_item.duplicate_group_id,
            source_tags=db_item.source_tags or [],
            created_at=db_item.created_at,
            updated_at=db_item.updated_at
        )
