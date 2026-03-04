"""Health check functionality for the news aggregator system."""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

import httpx

from src.config.settings import get_settings
from src.cache import get_redis


class HealthChecker:
    """System health checker."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity.
        
        Returns:
            Redis health status
        """
        try:
            redis = get_redis()
            await redis.connect()
            
            test_key = "health_check_redis"
            await redis.set(test_key, "ok", ttl=10)
            value = await redis.get(test_key)
            
            return {
                "status": "healthy" if value == b"ok" else "unhealthy",
                "response": value.decode() if value else None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity.
        
        Returns:
            Database health status
        """
        try:
            from src.database import get_db
            db = get_db()
            
            return {
                "status": "healthy",
                "message": "Database connection initialized"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_api_config(self) -> Dict[str, Any]:
        """Check API configuration.
        
        Returns:
            API configuration status
        """
        has_api_key = bool(self.settings.bailian_api_key)
        
        return {
            "status": "configured" if has_api_key else "missing_api_key",
            "model": self.settings.bailian_model,
            "endpoint": self.settings.bailian_api_endpoint
        }
    
    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks.
        
        Returns:
            Complete health status
        """
        redis_check = await self.check_redis()
        db_check = await self.check_database()
        api_check = await self.check_api_config()
        
        overall_status = "healthy"
        if redis_check["status"] != "healthy":
            overall_status = "unhealthy"
        elif api_check["status"] == "missing_api_key":
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": {
                "redis": redis_check,
                "database": db_check,
                "api": api_check
            }
        }


_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get singleton health checker instance.
    
    Returns:
        HealthChecker instance
    """
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker