"""Qwen LLM Client for Alibaba Bailian API integration."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

import httpx
from src.config.settings import get_settings


logger = logging.getLogger(__name__)


@dataclass
class APIStats:
    """API call statistics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_tokens: int = 0


class QwenLLMClient:
    """Alibaba Bailian Qwen API client.
    
    Provides interfaces for:
    - Text generation with Qwen models
    - Similarity calculation between texts
    - News classification
    """

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        """Initialize the Qwen LLM client.
        
        Args:
            api_key: Alibaba Bailian API key. Falls back to settings if not provided.
            endpoint: API endpoint URL. Falls back to settings if not provided.
        """
        settings = get_settings()
        self.api_key = api_key or settings.bailian_api_key
        self.endpoint = endpoint or settings.bailian_api_endpoint
        self.model = settings.bailian_model
        self.stats = APIStats()
        self._timeout = 30

    async def _call_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make API call to Alibaba Bailian.
        
        Args:
            payload: Request payload
            
        Returns:
            Response data
            
        Raises:
            httpx.HTTPStatusError: On HTTP errors
            asyncio.TimeoutError: On timeout
        """
        if not self.api_key:
            raise ValueError("API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        timeout = httpx.Timeout(self._timeout, connect=10.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self.endpoint,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Generate text using Qwen model.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        self.stats.total_calls += 1
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            response = await self._call_api(payload)
            self.stats.successful_calls += 1
            
            choices = response.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
            
        except Exception as e:
            self.stats.failed_calls += 1
            logger.error(f"API call failed: {e}")
            raise

    async def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts.
        
        Uses the model to evaluate similarity between news titles/summaries.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        prompt = f"""请判断以下两条新闻标题的语义相似度，只返回一个0到1之间的浮点数。
如果两条新闻讲述的是同一事件或高度相似的内容，返回0.85或以上。
如果两条新闻是同一话题但不同事件，返回0.5-0.84。
如果两条新闻完全不相关，返回0.5以下。

新闻1: {text1}
新闻2: {text2}

相似度:"""

        try:
            result = await self.generate_text(prompt, max_tokens=10, temperature=0.3)
            result = result.strip()
            
            score = float(result)
            return max(0.0, min(1.0, score))
            
        except (ValueError, asyncio.TimeoutError) as e:
            logger.warning(f"Similarity calculation failed: {e}, using fallback")
            return await self._fallback_similarity(text1, text2)

    async def _fallback_similarity(self, text1: str, text2: str) -> float:
        """Fallback similarity calculation based on keywords.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        jaccard = len(intersection) / len(union) if union else 0.0
        
        return min(0.8, jaccard * 1.5)

    async def classify_news(
        self,
        title: str,
        summary: str,
        valid_categories: Optional[set] = None
    ) -> List[str]:
        """Classify news into categories.
        
        Args:
            title: News title
            summary: News summary
            valid_categories: Set of valid categories. Defaults to predefined set.
            
        Returns:
            List of 1-3 categories
        """
        if valid_categories is None:
            valid_categories = {"金融", "科技", "体育", "娱乐", "政治", "健康"}
        
        prompt = f"""请分析以下新闻的类别，只返回类别名称，用逗号分隔，最多返回3个类别。
可选类别: 金融, 科技, 体育, 娱乐, 政治, 健康

新闻标题: {title}
新闻摘要: {summary}

类别:"""

        try:
            result = await self.generate_text(prompt, max_tokens=50, temperature=0.3)
            
            categories = [
                cat.strip() 
                for cat in result.split(",")
                if cat.strip()
            ]
            
            filtered = [
                cat for cat in categories
                if cat in valid_categories
            ]
            
            return filtered[:3] if filtered else ["科技"]
            
        except Exception as e:
            logger.warning(f"Classification failed: {e}, using fallback")
            return self._fallback_classification(title, summary)

    def _fallback_classification(
        self,
        title: str,
        summary: str
    ) -> List[str]:
        """Fallback classification based on keywords.
        
        Args:
            title: News title
            summary: News summary
            
        Returns:
            List of categories
        """
        text = (title + " " + summary).lower()
        
        category_keywords = {
            "金融": ["股票", "基金", "银行", "美元", "人民币", "金融", "投资", "通胀", "利率", "股市"],
            "科技": ["科技", "AI", "人工智能", "芯片", "互联网", "软件", "算法", "技术"],
            "体育": ["足球", "篮球", "比赛", "运动员", "奥运", "冠军", "体育"],
            "娱乐": ["电影", "明星", "音乐", "综艺", "演员", "娱乐", "票房"],
            "政治": ["政府", "总统", "外交", "政策", "国会", "政治", "国际"],
            "健康": ["健康", "医疗", "疫苗", "病毒", "疾病", "医院", "药物"]
        }
        
        scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scores[category] = score
        
        if not scores:
            return ["科技"]
        
        sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [sorted_cats[0][0]]

    def get_stats(self) -> Dict[str, Any]:
        """Get API usage statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            "total_calls": self.stats.total_calls,
            "successful_calls": self.stats.successful_calls,
            "failed_calls": self.stats.failed_calls,
            "total_tokens": self.stats.total_tokens,
            "success_rate": (
                self.stats.successful_calls / self.stats.total_calls
                if self.stats.total_calls > 0 else 0
            )
        }


_llm_client: Optional[QwenLLMClient] = None


def get_llm_client() -> QwenLLMClient:
    """Get or create singleton LLM client instance.
    
    Returns:
        QwenLLMClient instance
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = QwenLLMClient()
    return _llm_client