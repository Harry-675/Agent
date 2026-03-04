"""Deduplication engine for identifying and merging duplicate news."""

import asyncio
import logging
from typing import List, Dict, Set, Optional
from datetime import datetime
from uuid import uuid4

from src.models.news_item import NewsItem
from src.ai.llm_client import QwenLLMClient, get_llm_client
from src.config.settings import get_settings


logger = logging.getLogger(__name__)


class DeduplicationEngine:
    """News deduplication engine.
    
    Identifies duplicate news items based on semantic similarity
    using LLM-powered similarity calculation.
    
    Features:
    - Configurable similarity threshold (default 0.85)
    - 5-second timeout for similarity calculations
    - Automatic merging of duplicate items
    - Preserves earliest publication time
    """

    def __init__(
        self,
        llm_client: Optional[QwenLLMClient] = None,
        threshold: Optional[float] = None,
        timeout: Optional[int] = None
    ):
        """Initialize deduplication engine.
        
        Args:
            llm_client: LLM client instance. Creates one if not provided.
            threshold: Similarity threshold (0-1). Uses setting if not provided.
            timeout: Timeout in seconds. Uses setting if not provided.
        """
        self.llm_client = llm_client or get_llm_client()
        
        settings = get_settings()
        self.threshold = threshold or settings.similarity_threshold
        self.timeout = timeout or settings.dedup_timeout

    async def find_duplicates(
        self,
        news_items: List[NewsItem]
    ) -> Dict[str, List[NewsItem]]:
        """Find duplicate news items.
        
        Compares all news items and groups duplicates together.
        
        Args:
            news_items: List of news items to check
            
        Returns:
            Dictionary mapping representative item ID to list of duplicates
        """
        if len(news_items) <= 1:
            return {}
        
        duplicate_groups: Dict[str, List[NewsItem]] = {}
        processed: Set[str] = set()
        
        for i, item in enumerate(news_items):
            if item.id in processed:
                continue
            
            group = [item]
            processed.add(item.id)
            
            for j, other in enumerate(news_items[i + 1:], start=i + 1):
                if other.id in processed:
                    continue
                
                try:
                    similarity = await self._calculate_similarity_with_timeout(
                        item, other
                    )
                    
                    if similarity >= self.threshold:
                        group.append(other)
                        processed.add(other.id)
                        
                except asyncio.TimeoutError:
                    logger.warning(f"Similarity calculation timed out for {item.id} vs {other.id}")
                except Exception as e:
                    logger.error(f"Error calculating similarity: {e}")
            
            if len(group) > 1:
                duplicate_groups[item.id] = group
        
        return duplicate_groups

    async def _calculate_similarity_with_timeout(
        self,
        item1: NewsItem,
        item2: NewsItem
    ) -> float:
        """Calculate similarity with timeout protection.
        
        Args:
            item1: First news item
            item2: Second news item
            
        Returns:
            Similarity score
            
        Raises:
            asyncio.TimeoutError: If calculation exceeds timeout
        """
        text1 = f"{item1.title} {item1.summary}"
        text2 = f"{item2.title} {item2.summary}"
        
        try:
            return await asyncio.wait_for(
                self.llm_client.calculate_similarity(text1, text2),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Similarity calculation timed out after {self.timeout}s")
            raise

    async def calculate_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """Calculate similarity between two texts.
        
        Convenience method for external use.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        return await self._calculate_similarity_with_timeout(
            NewsItem(
                id="temp1",
                title=text1,
                summary="",
                url="",
                published_at=datetime.now(),
                source_id="",
                source_name=""
            ),
            NewsItem(
                id="temp2",
                title=text2,
                summary="",
                url="",
                published_at=datetime.now(),
                source_id="",
                source_name=""
            )
        )

    async def merge_duplicates(
        self,
        duplicate_groups: Dict[str, List[NewsItem]]
    ) -> List[NewsItem]:
        """Merge duplicate news items into single items.
        
        Merges each group of duplicates into one item:
        - Keeps earliest published_at
        - Combines all source_tags
        - Assigns a duplicate_group_id
        
        Args:
            duplicate_groups: Dictionary of duplicate groups
            
        Returns:
            List of merged news items
        """
        merged_items = []
        
        for representative_id, items in duplicate_groups.items():
            merged = self._merge_group(items)
            merged_items.append(merged)
        
        return merged_items

    def _merge_group(self, items: List[NewsItem]) -> NewsItem:
        """Merge a group of duplicate items.
        
        Args:
            items: List of duplicate items
            
        Returns:
            Merged news item
        """
        sorted_items = sorted(items, key=lambda x: x.published_at)
        primary = sorted_items[0]
        
        group_id = str(uuid4())
        all_tags = set()
        
        for item in items:
            all_tags.update(item.source_tags)
        
        merged = NewsItem(
            id=primary.id,
            title=primary.title,
            summary=primary.summary,
            url=primary.url,
            published_at=primary.published_at,
            source_id=primary.source_id,
            source_name=primary.source_name,
            categories=primary.categories,
            duplicate_group_id=group_id,
            source_tags=list(all_tags),
            created_at=primary.created_at,
            updated_at=datetime.now()
        )
        
        return merged

    def is_duplicate(
        self,
        item1: NewsItem,
        item2: NewsItem
    ) -> bool:
        """Check if two items are duplicates based on threshold.
        
        Note: This is a synchronous check that compares group IDs.
        For actual similarity calculation, use find_duplicates.
        
        Args:
            item1: First news item
            item2: Second news item
            
        Returns:
            True if items are in the same duplicate group
        """
        if item1.duplicate_group_id and item2.duplicate_group_id:
            return item1.duplicate_group_id == item2.duplicate_group_id
        return False