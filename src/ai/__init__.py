"""AI module for LLM-powered news processing."""

from src.ai.llm_client import QwenLLMClient, get_llm_client
from src.ai.deduplication import DeduplicationEngine
from src.ai.classification import CategoryClassifier

__all__ = [
    "QwenLLMClient",
    "get_llm_client", 
    "DeduplicationEngine",
    "CategoryClassifier"
]