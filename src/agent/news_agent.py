"""News aggregator agent for orchestrating the complete news processing pipeline."""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import defaultdict
from dataclasses import dataclass, field

from src.crawler.news_crawler import NewsCrawler
from src.ai.deduplication import DeduplicationEngine
from src.ai.classification import CategoryClassifier
from src.models.news_source import NewsSource
from src.models.news_item import NewsItem
from src.config.settings import get_settings


logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """Statistics for a processing cycle."""
    crawled_count: int = 0
    deduplicated_count: int = 0
    classified_count: int = 0
    failed_count: int = 0
    category_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    source_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "crawled_count": self.crawled_count,
            "deduplicated_count": self.deduplicated_count,
            "classified_count": self.classified_count,
            "failed_count": self.failed_count,
            "category_distribution": dict(self.category_distribution),
            "source_distribution": dict(self.source_distribution),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.start_time and self.end_time else None
            )
        }


class NewsAggregatorAgent:
    """News aggregator agent.
    
    Orchestrates the complete news processing pipeline:
    1. Crawl news from enabled sources
    2. Deduplicate using LLM-powered similarity
    3. Classify into categories
    4. Store in database
    
    Features:
    - Sequential processing preserving order
    - Error isolation (single item failure doesn't affect others)
    - Comprehensive statistics reporting
    """

    def __init__(
        self,
        sources: Optional[List[NewsSource]] = None,
        crawler: Optional[NewsCrawler] = None,
        deduplicator: Optional[DeduplicationEngine] = None,
        classifier: Optional[CategoryClassifier] = None
    ):
        """Initialize news aggregator agent.
        
        Args:
            sources: List of news sources. Loads from DB if not provided.
            crawler: News crawler instance. Creates new if not provided.
            deduplicator: Deduplication engine. Creates new if not provided.
            classifier: Category classifier. Creates new if not provided.
        """
        self.sources = sources or []
        self.crawler = crawler or NewsCrawler(self.sources)
        self.deduplicator = deduplicator or DeduplicationEngine()
        self.classifier = classifier or CategoryClassifier()
        self.stats = ProcessingStats()
        self._processing_queue: List[NewsItem] = []

    async def process_news_cycle(self) -> ProcessingStats:
        """Execute complete news processing cycle.
        
        Process pipeline:
        1. Crawl from all enabled sources
        2. Find and merge duplicates
        3. Classify each news item
        4. Return statistics
        
        Returns:
            ProcessingStats object with cycle statistics
        """
        self.stats = ProcessingStats()
        self.stats.start_time = datetime.now()
        
        logger.info("Starting news processing cycle")
        
        raw_items = await self.crawler.crawl_all()
        self.stats.crawled_count = len(raw_items)
        
        logger.info(f"Crawled {len(raw_items)} items, starting deduplication")
        
        duplicate_groups = await self.deduplicator.find_duplicates(raw_items)
        
        non_duplicates = [
            item for item in raw_items
            if item.id not in duplicate_groups
        ]
        
        merged = await self.deduplicator.merge_duplicates(duplicate_groups)
        
        all_items = non_duplicates + merged
        self.stats.deduplicated_count = len(all_items)
        
        logger.info(f"Deduplication complete: {len(all_items)} unique items")
        
        for item in all_items:
            await self._process_single_news(item)
        
        self.stats.end_time = datetime.now()
        
        logger.info(
            f"Processing cycle complete: "
            f"crawled={self.stats.crawled_count}, "
            f"unique={self.stats.deduplicated_count}, "
            f"classified={self.stats.classified_count}"
        )
        
        return self.stats

    async def _process_single_news(self, news_item: NewsItem) -> None:
        """Process a single news item through classification.
        
        Args:
            news_item: News item to process
        """
        try:
            categories = await self.classifier.classify(news_item)
            news_item.categories = categories
            
            self.stats.classified_count += 1
            
            for cat in categories:
                self.stats.category_distribution[cat] += 1
            
            self.stats.source_distribution[news_item.source_name] += 1
            
            self._processing_queue.append(news_item)
            
        except Exception as e:
            logger.error(f"Failed to process news item {news_item.id}: {e}")
            news_item.categories = ["科技"]
            self.stats.failed_count += 1

    def get_processing_queue(self) -> List[NewsItem]:
        """Get the current processing queue.
        
        Returns:
            List of processed news items in order
        """
        return self._processing_queue.copy()

    def clear_queue(self) -> None:
        """Clear the processing queue."""
        self._processing_queue.clear()

    async def generate_report(self) -> Dict[str, Any]:
        """Generate hourly statistics report.
        
        Returns:
            Dictionary containing statistics report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats.to_dict(),
            "system_health": {
                "crawler_errors": len(self.crawler.get_error_logs()),
                "queue_size": len(self._processing_queue)
            }
        }
        
        return report


_agent: Optional[NewsAggregatorAgent] = None


def get_agent(sources: Optional[List[NewsSource]] = None) -> NewsAggregatorAgent:
    """Get or create singleton agent instance.
    
    Args:
        sources: Optional list of news sources
        
    Returns:
        NewsAggregatorAgent instance
    """
    global _agent
    if _agent is None:
        _agent = NewsAggregatorAgent(sources=sources)
    return _agent