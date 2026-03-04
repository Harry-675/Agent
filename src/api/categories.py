"""Categories API routes."""

from typing import List
from fastapi import APIRouter

from src.ai.classification import VALID_CATEGORIES


router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("")
async def get_categories() -> dict:
    """Get list of all available categories.
    
    Returns all valid news categories.
    """
    return {
        "categories": sorted(list(VALID_CATEGORIES)),
        "count": len(VALID_CATEGORIES)
    }