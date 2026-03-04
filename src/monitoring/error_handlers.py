"""Error handlers and monitoring for the news aggregator system."""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass, field

from src.models.error_log import ErrorLog


logger = logging.getLogger(__name__)


ALERT_THRESHOLD = 3


@dataclass
class ErrorRecord:
    """Record of a single error occurrence."""
    timestamp: datetime
    error_type: str
    component: str
    message: str
    count: int = 1


class BaseErrorHandler(ABC):
    """Base class for error handlers."""
    
    def __init__(self):
        self.errors: List[ErrorLog] = []
        self.error_counts: Dict[str, int] = defaultdict(int)
    
    @abstractmethod
    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Handle an error."""
        pass
    
    def get_recent_errors(self, minutes: int = 60) -> List[ErrorLog]:
        """Get errors from the last N minutes."""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [e for e in self.errors if e.created_at >= cutoff]
    
    def get_error_count(self, error_type: str) -> int:
        """Get count of errors by type."""
        return self.error_counts.get(error_type, 0)


class CrawlErrorHandler(BaseErrorHandler):
    """Handler for news crawling errors."""
    
    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Handle crawling error and check for alerts.
        
        Args:
            error: The exception that occurred
            context: Additional context including source_id, source_name, etc.
        """
        error_log = ErrorLog.from_exception(
            error_type="crawl",
            component="crawler",
            operation=context.get("operation", "crawl") if context else "crawl",
            exception=error,
            context=context or {}
        )
        
        self.errors.append(error_log)
        self.error_counts["crawl"] += 1
        
        if context and "source_name" in context:
            source_key = f"source_{context['source_name']}"
            self.error_counts[source_key] += 1
            
            if self.error_counts[source_key] >= ALERT_THRESHOLD:
                logger.warning(
                    f"ALERT: Source {context['source_name']} has failed "
                    f"{self.error_counts[source_key]} times consecutively"
                )


class LLMErrorHandler(BaseErrorHandler):
    """Handler for LLM/API errors."""
    
    def __init__(self):
        super().__init__()
        self.fallback_mode = False
    
    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Handle LLM error and enable fallback mode if needed.
        
        Args:
            error: The exception that occurred
            context: Additional context including operation, model, etc.
        """
        error_log = ErrorLog.from_exception(
            error_type="llm",
            component="llm_client",
            operation=context.get("operation", "api_call") if context else "api_call",
            exception=error,
            context=context or {}
        )
        
        self.errors.append(error_log)
        self.error_counts["llm"] += 1
        
        if self.error_counts["llm"] >= ALERT_THRESHOLD and not self.fallback_mode:
            logger.warning(
                f"ALERT: LLM API has failed {self.error_counts['llm']} times. "
                "Enabling fallback mode."
            )
            self.fallback_mode = True
    
    def is_fallback_mode(self) -> bool:
        """Check if running in fallback mode."""
        return self.fallback_mode


class DatabaseErrorHandler(BaseErrorHandler):
    """Handler for database errors."""
    
    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """Handle database error.
        
        Args:
            error: The exception that occurred
            context: Additional context including operation, table, etc.
        """
        error_log = ErrorLog.from_exception(
            error_type="database",
            component="database",
            operation=context.get("operation", "query") if context else "query",
            exception=error,
            context=context or {}
        )
        
        self.errors.append(error_log)
        self.error_counts["database"] += 1
        
        if self.error_counts["database"] >= ALERT_THRESHOLD:
            logger.error(
                f"ALERT: Database errors have reached {self.error_counts['database']} occurrences"
            )


class ErrorTracker:
    """Central error tracking and monitoring."""
    
    def __init__(self):
        self.crawl_handler = CrawlErrorHandler()
        self.llm_handler = LLMErrorHandler()
        self.db_handler = DatabaseErrorHandler()
        self._error_history: deque = deque(maxlen=1000)
    
    def track_error(
        self,
        error_type: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track an error of any type.
        
        Args:
            error_type: Type of error (crawl, llm, database)
            error: The exception
            context: Additional context
        """
        record = ErrorRecord(
            timestamp=datetime.now(),
            error_type=error_type,
            component=context.get("component", "unknown") if context else "unknown",
            message=str(error)
        )
        
        self._error_history.append(record)
        
        if error_type == "crawl":
            self.crawl_handler.handle(error, context)
        elif error_type == "llm":
            self.llm_handler.handle(error, context)
        elif error_type == "database":
            self.db_handler.handle(error, context)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system error status.
        
        Returns:
            Dictionary with error statistics
        """
        return {
            "crawl_errors": self.crawl_handler.error_counts.get("crawl", 0),
            "llm_errors": self.llm_handler.error_counts.get("llm", 0),
            "database_errors": self.db_handler.error_counts.get("database", 0),
            "llm_fallback_mode": self.llm_handler.is_fallback_mode(),
            "recent_errors_count": len(self.get_recent_errors())
        }
    
    def get_recent_errors(self, minutes: int = 60) -> List[ErrorRecord]:
        """Get recent error records.
        
        Args:
            minutes: Time window in minutes
            
        Returns:
            List of recent error records
        """
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [e for e in self._error_history if e.timestamp >= cutoff]
    
    def clear_old_errors(self, days: int = 7) -> int:
        """Clear error history older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of records cleared
        """
        cutoff = datetime.now() - timedelta(days=days)
        original_count = len(self._error_history)
        
        self._error_history = deque(
            (e for e in self._error_history if e.timestamp >= cutoff),
            maxlen=1000
        )
        
        return original_count - len(self._error_history)


_error_tracker: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    """Get singleton error tracker instance.
    
    Returns:
        ErrorTracker instance
    """
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker