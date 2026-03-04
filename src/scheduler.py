"""Task scheduler for automatic news crawling."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from src.agent.news_agent import get_agent
from src.config.settings import get_settings


logger = logging.getLogger(__name__)


class NewsScheduler:
    """Scheduler for automatic news fetching.
    
    Uses APScheduler to trigger news crawling at configured intervals.
    """

    def __init__(self, interval_minutes: Optional[int] = None):
        """Initialize scheduler.
        
        Args:
            interval_minutes: Crawl interval in minutes. Uses setting if not provided.
        """
        settings = get_settings()
        self.interval = interval_minutes or settings.crawler_interval_minutes
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._running = False

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self.scheduler = AsyncIOScheduler()
        
        self.scheduler.add_job(
            self._crawl_task,
            trigger=IntervalTrigger(minutes=self.interval),
            id="news_crawl",
            name="News Crawl",
            replace_existing=True
        )
        
        # Add hourly report generation job
        self.scheduler.add_job(
            self._report_task,
            trigger=CronTrigger(minute=0),  # Run at the start of every hour
            id="hourly_report",
            name="Hourly Statistics Report",
            replace_existing=True
        )
        
        self.scheduler.start()
        self._running = True
        logger.info(f"Scheduler started with {self.interval} minute interval")

    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running or self.scheduler is None:
            return
        
        self.scheduler.shutdown(wait=True)
        self._running = False
        logger.info("Scheduler stopped")

    async def _crawl_task(self) -> None:
        logger.info("Starting scheduled crawl task")
        
        try:
            agent = get_agent()
            stats = await agent.process_news_cycle()
            
            logger.info(
                f"Crawl completed: "
                f"crawled={stats.crawled_count}, "
                f"unique={stats.deduplicated_count}, "
                f"classified={stats.classified_count}"
            )
        except Exception as e:
            logger.error(f"Crawl task failed: {e}")

    async def _report_task(self) -> None:
        logger.info("Generating hourly statistics report")
        
        try:
            agent = get_agent()
            report = await agent.generate_report()
            self._save_report(report)
            
            logger.info(f"Hourly report generated: {report['stats']}")
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
    
    def _save_report(self, report: Dict[str, Any]) -> None:
        settings = get_settings()
        reports_dir = Path(settings.reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"report_{timestamp}.json"
        
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    def get_status(self) -> dict:
        """Get scheduler status.
        
        Returns:
            Dictionary with scheduler status
        """
        return {
            "running": self._running,
            "interval_minutes": self.interval,
            "next_run": (
                self.scheduler.get_next_run_time().isoformat()
                if self.scheduler and self.scheduler.get_next_run_time()
                else None
            )
        }


_scheduler: Optional[NewsScheduler] = None


def get_scheduler() -> NewsScheduler:
    """Get singleton scheduler instance.
    
    Returns:
        NewsScheduler instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = NewsScheduler()
    return _scheduler