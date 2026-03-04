"""Health check API route."""

from fastapi import APIRouter
from src.monitoring.health import get_health_checker


router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health_check() -> dict:
    """Basic health check endpoint.
    
    Returns simple health status.
    """
    return {"status": "ok"}


@router.get("/detailed")
async def detailed_health_check() -> dict:
    """Detailed health check with all system components.
    
    Returns comprehensive health status for all system components.
    """
    checker = get_health_checker()
    return await checker.check_all()


@router.get("/statistics")
async def get_statistics() -> dict:
    """Get system statistics.
    
    Returns processing statistics and error counts.
    """
    from src.monitoring.error_handlers import get_error_tracker
    
    tracker = get_error_tracker()
    
    return {
        "system_status": tracker.get_system_status(),
        "recent_errors": len(tracker.get_recent_errors())
    }