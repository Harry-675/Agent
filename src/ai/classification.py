"""News category classifier using LLM."""

import asyncio
import logging
from typing import List, Optional, Set

from src.models.news_item import NewsItem
from src.ai.llm_client import QwenLLMClient, get_llm_client
from src.config.settings import get_settings


logger = logging.getLogger(__name__)


VALID_CATEGORIES: Set[str] = {"金融", "科技", "体育", "娱乐", "政治", "健康"}


class CategoryClassifier:
    """News category classifier.
    
    Uses LLM to classify news items into predefined categories.
    
    Features:
    - 3-second timeout for classification
    - Returns 1-3 categories per news item
    - Validates categories against predefined set
    - Fallback to keyword-based classification on failure
    """

    def __init__(
        self,
        llm_client: Optional[QwenLLMClient] = None,
        timeout: Optional[int] = None,
        max_categories: Optional[int] = None
    ):
        """Initialize category classifier.
        
        Args:
            llm_client: LLM client instance. Creates one if not provided.
            timeout: Classification timeout in seconds. Uses setting if not provided.
            max_categories: Maximum categories per item. Uses setting if not provided.
        """
        self.llm_client = llm_client or get_llm_client()
        
        settings = get_settings()
        self.timeout = timeout or settings.classification_timeout
        self.max_categories = max_categories or settings.max_categories

    async def classify(self, news_item: NewsItem) -> List[str]:
        """Classify a news item into categories.
        
        Args:
            news_item: News item to classify
            
        Returns:
            List of 1-3 category strings
        """
        try:
            categories = await asyncio.wait_for(
                self.llm_client.classify_news(
                    title=news_item.title,
                    summary=news_item.summary,
                    valid_categories=VALID_CATEGORIES
                ),
                timeout=self.timeout
            )
            
            filtered = self._validate_categories(categories)
            
            return filtered if filtered else ["科技"]
            
        except asyncio.TimeoutError:
            logger.warning(f"Classification timed out for {news_item.id}")
            return self._fallback_classify(news_item)
        except Exception as e:
            logger.error(f"Classification failed for {news_item.id}: {e}")
            return self._fallback_classify(news_item)

    async def classify_batch(
        self,
        news_items: List[NewsItem]
    ) -> List[List[str]]:
        """Classify multiple news items.
        
        Args:
            news_items: List of news items to classify
            
        Returns:
            List of category lists
        """
        tasks = [self.classify(item) for item in news_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        classified = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to classify item {i}: {result}")
                classified.append(["科技"])
            else:
                classified.append(result)
        
        return classified

    def _validate_categories(self, categories: List[str]) -> List[str]:
        """Validate and filter categories.
        
        Args:
            categories: List of category strings
            
        Returns:
            Filtered list of valid categories (1-3)
        """
        valid = [cat for cat in categories if cat in VALID_CATEGORIES]
        unique = list(dict.fromkeys(valid))
        return unique[:self.max_categories]

    def _fallback_classify(self, news_item: NewsItem) -> List[str]:
        """Fallback classification using keywords.
        
        Args:
            news_item: News item to classify
            
        Returns:
            List of categories
        """
        text = (news_item.title + " " + news_item.summary).lower()
        
        category_keywords = {
            "金融": ["股票", "基金", "银行", "美元", "人民币", "金融", "投资", "通胀", "利率", "股市", "上证", "深证", "美股", "港股"],
            "科技": ["科技", "AI", "人工智能", "芯片", "互联网", "软件", "算法", "技术", "大模型", "模型", "GPT", "机器人"],
            "体育": ["足球", "篮球", "比赛", "运动员", "奥运", "冠军", "体育", "球", "队", "联赛", "世界杯"],
            "娱乐": ["电影", "明星", "音乐", "综艺", "演员", "娱乐", "票房", "导演", "歌", "剧"],
            "政治": ["政府", "总统", "外交", "政策", "国会", "政治", "国际", "国家", "领导", "峰会"],
            "健康": ["健康", "医疗", "疫苗", "病毒", "疾病", "医院", "药物", "治疗", "疫情", "新冠"]
        }
        
        scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[category] = score
        
        if not scores:
            return ["科技"]
        
        sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in sorted_cats[:self.max_categories]]

    def get_valid_categories(self) -> Set[str]:
        """Get set of valid categories.
        
        Returns:
            Set of valid category strings
        """
        return VALID_CATEGORIES.copy()