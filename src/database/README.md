# Database Schema Documentation

This directory contains the database schema and initialization scripts for the news aggregator system.

## Files

- **schema.sql**: Complete SQL schema definition with tables, indexes, and triggers
- **init_db.py**: Python script to initialize or reset the database
- **connection.py**: Database connection management utilities

## Database Tables

### 1. news_sources
Stores configuration for news sources to be crawled.

**Columns:**
- `id` (VARCHAR(36), PK): Unique identifier
- `name` (VARCHAR(255)): Display name of the news source
- `url` (TEXT): Base URL of the news source
- `enabled` (BOOLEAN): Whether this source is active for crawling
- `crawl_rules` (JSONB): CSS selectors or XPath rules for parsing
- `timeout` (INTEGER): Timeout in seconds (default: 30)
- `created_at` (TIMESTAMP): Creation timestamp
- `updated_at` (TIMESTAMP): Last update timestamp

**Indexes:**
- `idx_news_sources_enabled`: For filtering enabled sources
- `idx_news_sources_name`: For name lookups

### 2. news_items
Stores news articles with metadata, categories, and deduplication information.

**Columns:**
- `id` (VARCHAR(36), PK): Unique identifier
- `title` (TEXT): News article title
- `summary` (TEXT): News article summary/excerpt
- `url` (TEXT): Link to original article
- `published_at` (TIMESTAMP): Publication date/time
- `source_id` (VARCHAR(36), FK): Reference to news_sources
- `source_name` (VARCHAR(255)): Name of the source
- `categories` (TEXT[]): Array of topic categories (1-3 items)
- `duplicate_group_id` (VARCHAR(36)): Groups duplicate news together
- `source_tags` (TEXT[]): All source names for merged duplicates
- `created_at` (TIMESTAMP): Creation timestamp
- `updated_at` (TIMESTAMP): Last update timestamp

**Indexes:**
- `idx_news_items_published_at`: For sorting by publication date
- `idx_news_items_categories`: GIN index for category filtering
- `idx_news_items_duplicate_group`: For finding duplicate groups
- `idx_news_items_created_at`: For sorting by creation time
- `idx_news_items_url`: For URL lookups
- `idx_news_items_categories_published`: Composite index for filtered queries

### 3. processing_logs
Tracks processing stages and errors for debugging and monitoring.

**Columns:**
- `id` (SERIAL, PK): Auto-incrementing identifier
- `news_id` (VARCHAR(36)): Reference to news item
- `stage` (VARCHAR(50)): Processing stage (crawl, dedup, classify, store)
- `status` (VARCHAR(20)): Status (success, failure)
- `error_message` (TEXT): Error details if failed
- `processing_time_ms` (INTEGER): Processing time in milliseconds
- `created_at` (TIMESTAMP): Log timestamp

**Indexes:**
- `idx_processing_logs_news_id`: For querying logs by news item
- `idx_processing_logs_created_at`: For time-based queries
- `idx_processing_logs_stage_status`: For filtering by stage and status

### 4. system_metrics
Stores system performance metrics and statistics.

**Columns:**
- `id` (SERIAL, PK): Auto-incrementing identifier
- `metric_type` (VARCHAR(50)): Type of metric (crawl_count, dedup_count, api_calls, etc.)
- `metric_value` (INTEGER): Numeric value of the metric
- `metadata` (JSONB): Additional metadata in JSON format
- `recorded_at` (TIMESTAMP): Metric timestamp

**Indexes:**
- `idx_system_metrics_type_time`: Composite index for metric queries
- `idx_system_metrics_recorded_at`: For time-based aggregations

## Usage

### Initialize Database

To create all tables and indexes:

```bash
python src/database/init_db.py
```

### Reset Database

To drop all tables and recreate them (WARNING: destroys all data):

```bash
python src/database/init_db.py --reset
```

### Environment Configuration

Make sure your `.env` file contains the correct database connection settings:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/news_aggregator
DB_HOST=localhost
DB_PORT=5432
DB_NAME=news_aggregator
DB_USER=postgres
DB_PASSWORD=password
```

## Performance Considerations

### Indexes

The schema includes several indexes optimized for common query patterns:

1. **Time-based queries**: Indexes on `published_at` and `created_at` support efficient sorting and filtering by date
2. **Category filtering**: GIN index on `categories` array enables fast category-based queries
3. **Deduplication**: Index on `duplicate_group_id` speeds up finding related news items
4. **Monitoring**: Composite indexes on logs and metrics support efficient monitoring queries

### Automatic Timestamp Updates

The schema includes triggers that automatically update the `updated_at` column whenever a record is modified in `news_sources` or `news_items` tables.

## Data Retention

According to the requirements (8.3, 8.4), the system should:
- Keep news data for the most recent 30 days
- Automatically archive or delete older data

This will be implemented in the application layer with scheduled cleanup tasks.

## Foreign Key Relationships

- `news_items.source_id` → `news_sources.id` (ON DELETE SET NULL)
  - When a news source is deleted, related news items remain but the source_id is set to NULL
  - The `source_name` field preserves the original source name

## Query Examples

### Get recent news by category

```sql
SELECT * FROM news_items
WHERE 'Technology' = ANY(categories)
AND published_at >= NOW() - INTERVAL '7 days'
ORDER BY published_at DESC
LIMIT 20;
```

### Find duplicate news groups

```sql
SELECT duplicate_group_id, COUNT(*) as count, 
       ARRAY_AGG(DISTINCT source_name) as sources
FROM news_items
WHERE duplicate_group_id IS NOT NULL
GROUP BY duplicate_group_id
HAVING COUNT(*) > 1
ORDER BY count DESC;
```

### Get processing error statistics

```sql
SELECT stage, COUNT(*) as error_count
FROM processing_logs
WHERE status = 'failure'
AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY stage
ORDER BY error_count DESC;
```

### Get system metrics over time

```sql
SELECT metric_type, 
       DATE_TRUNC('hour', recorded_at) as hour,
       SUM(metric_value) as total
FROM system_metrics
WHERE recorded_at >= NOW() - INTERVAL '24 hours'
GROUP BY metric_type, hour
ORDER BY hour DESC, metric_type;
```
