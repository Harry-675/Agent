"""SQLAlchemy ORM models for database tables."""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Text, TIMESTAMP, ForeignKey, JSON

from src.database.base import Base


class NewsSourceModel(Base):
    """ORM model for news_sources table."""
    
    __tablename__ = 'news_sources'
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True)
    crawl_rules = Column(JSON, nullable=False)  # Use JSON for cross-database compatibility
    timeout = Column(Integer, default=30)
    created_at = Column(TIMESTAMP, default=datetime.now)
    updated_at = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)


class NewsItemModel(Base):
    """ORM model for news_items table."""
    
    __tablename__ = 'news_items'
    
    id = Column(String(36), primary_key=True)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    url = Column(Text, nullable=False)
    published_at = Column(TIMESTAMP, nullable=False)
    source_id = Column(String(36), ForeignKey('news_sources.id', ondelete='SET NULL'))
    source_name = Column(String(255), nullable=False)
    categories = Column(JSON, nullable=False)  # Use JSON for cross-database compatibility
    duplicate_group_id = Column(String(36))
    source_tags = Column(JSON, nullable=False)  # Use JSON for cross-database compatibility
    created_at = Column(TIMESTAMP, default=datetime.now)
    updated_at = Column(TIMESTAMP, default=datetime.now, onupdate=datetime.now)


class ProcessingLogModel(Base):
    """ORM model for processing_logs table."""
    
    __tablename__ = 'processing_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    news_id = Column(String(36))
    stage = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    error_message = Column(Text)
    processing_time_ms = Column(Integer)
    created_at = Column(TIMESTAMP, default=datetime.now)


class SystemMetricModel(Base):
    """ORM model for system_metrics table."""
    
    __tablename__ = 'system_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_type = Column(String(50), nullable=False)
    metric_value = Column(Integer, nullable=False)
    metric_metadata = Column('metadata', JSON)  # Use JSON for cross-database compatibility
    recorded_at = Column(TIMESTAMP, default=datetime.now)
