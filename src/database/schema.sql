-- News Aggregator Database Schema
-- This schema defines the core tables for the news aggregation system

-- ============================================================================
-- Table: news_sources
-- Description: Stores configuration for news sources to be crawled
-- ============================================================================
CREATE TABLE IF NOT EXISTS news_sources (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    crawl_rules JSONB NOT NULL,
    timeout INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for filtering enabled sources during crawl operations
CREATE INDEX IF NOT EXISTS idx_news_sources_enabled ON news_sources(enabled);

-- Index for faster lookups by name
CREATE INDEX IF NOT EXISTS idx_news_sources_name ON news_sources(name);

-- ============================================================================
-- Table: news_items
-- Description: Stores news articles with metadata, categories, and deduplication info
-- ============================================================================
CREATE TABLE IF NOT EXISTS news_items (
    id VARCHAR(36) PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT NOT NULL,
    published_at TIMESTAMP NOT NULL,
    source_id VARCHAR(36) REFERENCES news_sources(id) ON DELETE SET NULL,
    source_name VARCHAR(255) NOT NULL,
    categories TEXT[] NOT NULL,
    duplicate_group_id VARCHAR(36),
    source_tags TEXT[] NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for sorting news by publication date (most recent first)
CREATE INDEX IF NOT EXISTS idx_news_items_published_at ON news_items(published_at DESC);

-- GIN index for efficient array operations on categories (filtering by category)
CREATE INDEX IF NOT EXISTS idx_news_items_categories ON news_items USING GIN(categories);

-- Index for finding duplicate news groups
CREATE INDEX IF NOT EXISTS idx_news_items_duplicate_group ON news_items(duplicate_group_id);

-- Index for sorting by creation time (useful for recent news queries)
CREATE INDEX IF NOT EXISTS idx_news_items_created_at ON news_items(created_at DESC);

-- Index for URL uniqueness checks and lookups
CREATE INDEX IF NOT EXISTS idx_news_items_url ON news_items(url);

-- Composite index for category filtering with time sorting
CREATE INDEX IF NOT EXISTS idx_news_items_categories_published ON news_items USING GIN(categories) WHERE published_at IS NOT NULL;

-- ============================================================================
-- Table: processing_logs
-- Description: Tracks processing stages and errors for debugging and monitoring
-- ============================================================================
CREATE TABLE IF NOT EXISTS processing_logs (
    id SERIAL PRIMARY KEY,
    news_id VARCHAR(36),
    stage VARCHAR(50) NOT NULL,  -- 'crawl', 'dedup', 'classify', 'store'
    status VARCHAR(20) NOT NULL,  -- 'success', 'failure'
    error_message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for querying logs by news item
CREATE INDEX IF NOT EXISTS idx_processing_logs_news_id ON processing_logs(news_id);

-- Index for time-based log queries (recent errors, performance analysis)
CREATE INDEX IF NOT EXISTS idx_processing_logs_created_at ON processing_logs(created_at DESC);

-- Composite index for filtering by stage and status
CREATE INDEX IF NOT EXISTS idx_processing_logs_stage_status ON processing_logs(stage, status);

-- ============================================================================
-- Table: system_metrics
-- Description: Stores system performance metrics and statistics
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    metric_type VARCHAR(50) NOT NULL,  -- 'crawl_count', 'dedup_count', 'api_calls', etc.
    metric_value INTEGER NOT NULL,
    metadata JSONB,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Composite index for efficient metric queries by type and time
CREATE INDEX IF NOT EXISTS idx_system_metrics_type_time ON system_metrics(metric_type, recorded_at DESC);

-- Index for time-based aggregations
CREATE INDEX IF NOT EXISTS idx_system_metrics_recorded_at ON system_metrics(recorded_at DESC);

-- ============================================================================
-- Triggers for automatic timestamp updates
-- ============================================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for news_sources table
DROP TRIGGER IF EXISTS update_news_sources_updated_at ON news_sources;
CREATE TRIGGER update_news_sources_updated_at
    BEFORE UPDATE ON news_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for news_items table
DROP TRIGGER IF EXISTS update_news_items_updated_at ON news_items;
CREATE TRIGGER update_news_items_updated_at
    BEFORE UPDATE ON news_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Comments for documentation
-- ============================================================================

COMMENT ON TABLE news_sources IS 'Configuration for news sources to be crawled';
COMMENT ON TABLE news_items IS 'Stores news articles with metadata and deduplication info';
COMMENT ON TABLE processing_logs IS 'Tracks processing stages and errors for monitoring';
COMMENT ON TABLE system_metrics IS 'Stores system performance metrics and statistics';

COMMENT ON COLUMN news_sources.crawl_rules IS 'JSON object containing CSS selectors or XPath rules for parsing';
COMMENT ON COLUMN news_sources.timeout IS 'Timeout in seconds for crawling this source';

COMMENT ON COLUMN news_items.duplicate_group_id IS 'Groups duplicate news items together';
COMMENT ON COLUMN news_items.source_tags IS 'Array of all source names for merged duplicate news';
COMMENT ON COLUMN news_items.categories IS 'Array of topic categories (1-3 items)';

COMMENT ON COLUMN processing_logs.stage IS 'Processing stage: crawl, dedup, classify, or store';
COMMENT ON COLUMN processing_logs.status IS 'Processing status: success or failure';
COMMENT ON COLUMN processing_logs.processing_time_ms IS 'Time taken for this processing stage in milliseconds';

COMMENT ON COLUMN system_metrics.metric_type IS 'Type of metric: crawl_count, dedup_count, api_calls, etc.';
COMMENT ON COLUMN system_metrics.metadata IS 'Additional metadata about the metric in JSON format';
