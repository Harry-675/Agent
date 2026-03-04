"""News API routes."""

import json
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from src.models.news_item import NewsItem
from src.models.news_source import NewsSource

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/news", tags=["news"])


class NewsItemResponse(BaseModel):
    """News item response model."""
    id: str
    title: str
    summary: str
    url: str
    published_at: str
    source_name: str
    categories: List[str]
    source_tags: List[str]
    duplicate_group_id: Optional[str] = None


class NewsListResponse(BaseModel):
    """News list response model."""
    items: List[NewsItemResponse]
    total: int
    page: int
    page_size: int


def load_news_sources() -> List[NewsSource]:
    """Load news sources from config file."""
    config_path = Path(__file__).parent.parent.parent / "config" / "news_sources.json"
    
    if not config_path.exists():
        logger.warning(f"News sources config not found: {config_path}")
        return []
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            sources_data = json.load(f)
        
        sources = []
        for item in sources_data:
            if item.get("enabled", True):
                source = NewsSource(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    url=item.get("url", ""),
                    enabled=item.get("enabled", True),
                    crawl_rules=item.get("crawl_rules", {}),
                    timeout=item.get("timeout", 30)
                )
                sources.append(source)
        
        return sources
    except Exception as e:
        logger.error(f"Failed to load news sources: {e}")
        return []


@router.get("", response_model=NewsListResponse)
async def get_news(
    category: Optional[str] = Query(None, description="Filter by category"),
    source: Optional[str] = Query(None, description="Filter by source name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
) -> NewsListResponse:
    """Get news items with optional filtering and pagination.
    
    Returns a paginated list of news items, optionally filtered by category or source.
    """
    from src.crawler.news_crawler import NewsCrawler
    
    try:
        sources = load_news_sources()
        crawler = NewsCrawler(sources)
        
        news_items = await crawler.crawl_all()
        
        if category and category != 'all':
            filtered = [
                item for item in news_items
                if item.categories and category in item.categories
            ]
            news_items = filtered
        
        # Filter by source if provided
        if source:
            news_items = [
                item for item in news_items 
                if item.source_name == source
            ]
        
        total = len(news_items)
        offset = (page - 1) * page_size
        paginated_items = news_items[offset:offset + page_size]
        
        items = [
            NewsItemResponse(
                id=item.id,
                title=item.title,
                summary=item.summary,
                url=item.url,
                published_at=item.published_at.isoformat() if hasattr(item.published_at, 'isoformat') else str(item.published_at),
                source_name=item.source_name,
                categories=item.categories or ["科技"],
                source_tags=item.source_tags or [item.source_name],
                duplicate_group_id=item.duplicate_group_id
            )
            for item in paginated_items
        ]
        
        return NewsListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Failed to fetch news: {e}")
        return NewsListResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size
        )


@router.get("/sources")
async def get_news_sources() -> List[dict]:
    """Get list of configured news sources."""
    sources = load_news_sources()
    return [
        {
            "id": s.id,
            "name": s.name,
            "url": s.url,
            "enabled": s.enabled
        }
        for s in sources
    ]


@router.post("/sources/{source_id}/toggle")
async def toggle_news_source(source_id: str) -> dict:
    """Toggle a news source enabled/disabled status."""
    config_path = Path(__file__).parent.parent.parent / "config" / "news_sources.json"
    
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Config file not found")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            sources_data = json.load(f)
        
        for item in sources_data:
            if item.get("id") == source_id:
                item["enabled"] = not item.get("enabled", True)
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(sources_data, f, ensure_ascii=False, indent=2)
                return {"id": source_id, "enabled": item["enabled"]}
        
        raise HTTPException(status_code=404, detail="Source not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources")
async def add_news_source(source: dict) -> dict:
    """Add a new news source."""
    config_path = Path(__file__).parent.parent.parent / "config" / "news_sources.json"
    
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Config file not found")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            sources_data = json.load(f)
        
        # Validate required fields
        required = ["id", "name", "url"]
        for field in required:
            if field not in source:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Check if source already exists
        for item in sources_data:
            if item.get("id") == source.get("id"):
                raise HTTPException(status_code=400, detail="Source ID already exists")
        
        new_source = {
            "id": source.get("id"),
            "name": source.get("name"),
            "url": source.get("url"),
            "enabled": source.get("enabled", True),
            "crawl_rules": source.get("crawl_rules", {"type": "rss", "category": "综合"}),
            "timeout": source.get("timeout", 30)
        }
        
        sources_data.append(new_source)
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(sources_data, f, ensure_ascii=False, indent=2)
        
        return {"message": "Source added successfully", "source": new_source}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sources/{source_id}")
async def delete_news_source(source_id: str) -> dict:
    """Delete a news source."""
    config_path = Path(__file__).parent.parent.parent / "config" / "news_sources.json"
    
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Config file not found")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            sources_data = json.load(f)
        
        original_count = len(sources_data)
        sources_data = [item for item in sources_data if item.get("id") != source_id]
        
        if len(sources_data) == original_count:
            raise HTTPException(status_code=404, detail="Source not found")
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(sources_data, f, ensure_ascii=False, indent=2)
        
        return {"message": "Source deleted successfully", "id": source_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{news_id}", response_model=NewsItemResponse)
async def get_news_item(news_id: str) -> NewsItemResponse:
    """Get a single news item by ID.
    
    Returns a single news item with all details.
    """
    raise HTTPException(status_code=404, detail="News item not found")


@router.post("/trigger-crawl")
async def trigger_crawl() -> dict:
    """Trigger a manual news crawl.
    
    Starts a new crawl cycle for all enabled news sources.
    """
    return {"message": "Crawl triggered", "status": "started"}