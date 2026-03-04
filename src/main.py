"""Main application entry point."""

import time
from contextlib import asynccontextmanager
from pathlib import Path
from collections import defaultdict

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.cache import get_redis
from src.config import get_settings
from src.database import get_db
from src.api import news, categories, health
from src.scheduler import get_scheduler

settings = get_settings()

STATIC_DIR = Path(__file__).parent.parent / "static"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware supporting 100 concurrent users."""
    
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()
        
        self._requests[client_ip] = [
            t for t in self._requests[client_ip]
            if current_time - t < self.window_seconds
        ]
        
        if len(self._requests[client_ip]) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later."
            )
        
        self._requests[client_ip].append(current_time)
        
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            self.max_requests - len(self._requests[client_ip])
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("🚀 Starting One News Aggregator...")
    
    # Initialize Redis connection
    redis = get_redis()
    await redis.connect()
    print("✅ Redis connected")
    
    # Initialize database
    db = get_db()
    print("✅ Database initialized")
    
    # Start scheduler
    scheduler = get_scheduler()
    await scheduler.start()
    print(f"✅ Scheduler started ({scheduler.interval} min interval)")
    
    yield
    
    # Shutdown
    print("👋 Shutting down One News Aggregator...")
    await scheduler.stop()
    await redis.disconnect()
    print("✅ Redis disconnected")


app = FastAPI(
    title="One News Aggregator",
    description="智能新闻聚合平台 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware (100 concurrent requests per IP)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

# Include API routers
app.include_router(news.router)
app.include_router(categories.router)
app.include_router(health.router)

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    """Root endpoint - serve the frontend."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "message": "Welcome to One News Aggregator",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Basic health check
    redis = get_redis()
    redis_connected = await redis.exists("health_check_test")
    
    return {
        "status": "healthy",
        "redis": "connected" if redis_connected is not None else "disconnected",
        "database": "initialized",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )
