# Project Structure

This document describes the directory structure and organization of the One News Aggregator project.

## Directory Layout

```
news-aggregator-one/
├── .kiro/                          # Kiro spec files
│   └── specs/
│       └── news-aggregator-one/
│           ├── requirements.md     # Requirements document
│           ├── design.md          # Design document
│           └── tasks.md           # Implementation tasks
│
├── src/                           # Source code
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   │
│   ├── config/                    # Configuration module
│   │   ├── __init__.py
│   │   └── settings.py            # Application settings (Pydantic)
│   │
│   ├── database/                  # Database module
│   │   ├── __init__.py
│   │   └── connection.py          # PostgreSQL connection management
│   │
│   ├── cache/                     # Cache module
│   │   ├── __init__.py
│   │   └── connection.py          # Redis connection management
│   │
│   ├── models/                    # Data models (to be created in Task 2)
│   │   ├── __init__.py
│   │   ├── news_source.py
│   │   ├── news_item.py
│   │   └── error_log.py
│   │
│   ├── crawler/                   # News crawler module (Task 5)
│   │   ├── __init__.py
│   │   └── crawler.py
│   │
│   ├── ai/                        # AI processing modules (Tasks 6-8)
│   │   ├── __init__.py
│   │   ├── llm_client.py          # Qwen3 LLM client
│   │   ├── deduplication.py       # Deduplication engine
│   │   └── classification.py      # Category classifier
│   │
│   ├── agent/                     # AI agent coordinator (Task 10)
│   │   ├── __init__.py
│   │   └── coordinator.py
│   │
│   └── api/                       # Web API (Task 14)
│       ├── __init__.py
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── news.py
│       │   ├── categories.py
│       │   └── health.py
│       └── dependencies.py
│
├── tests/                         # Test suite
│   ├── __init__.py
│   │
│   ├── unit/                      # Unit tests
│   │   ├── __init__.py
│   │   ├── test_config.py
│   │   ├── test_crawler.py
│   │   ├── test_deduplication.py
│   │   ├── test_classification.py
│   │   └── test_agent.py
│   │
│   ├── property/                  # Property-based tests
│   │   ├── __init__.py
│   │   ├── test_properties_config.py
│   │   ├── test_properties_crawl.py
│   │   ├── test_properties_dedup.py
│   │   ├── test_properties_classify.py
│   │   ├── test_properties_agent.py
│   │   ├── test_properties_web.py
│   │   ├── test_properties_storage.py
│   │   └── test_properties_monitoring.py
│   │
│   ├── integration/               # Integration tests
│   │   ├── __init__.py
│   │   └── test_end_to_end.py
│   │
│   └── fixtures/                  # Test fixtures and mock data
│       ├── __init__.py
│       ├── mock_news_sources.py
│       ├── mock_llm_responses.py
│       └── sample_news_data.py
│
├── config/                        # Configuration files
│   ├── news_sources.example.json # Example news sources configuration
│   └── news_sources.json         # Actual news sources (not in git)
│
├── requirements.txt               # Python dependencies
├── .env.example                  # Environment variables template
├── .env                          # Actual environment variables (not in git)
├── .gitignore                    # Git ignore rules
├── pytest.ini                    # Pytest configuration
├── docker-compose.yml            # Docker services (PostgreSQL, Redis)
├── setup.sh                      # Setup script for Linux/Mac
├── setup.bat                     # Setup script for Windows
├── verify_setup.py               # Project structure verification script
├── README.md                     # Project documentation
└── PROJECT_STRUCTURE.md          # This file
```

## Module Descriptions

### Core Modules

#### `src/config/`
Configuration management using Pydantic Settings. Loads environment variables and provides type-safe configuration access.

#### `src/database/`
PostgreSQL database connection management using SQLAlchemy async. Provides session management and connection pooling.

#### `src/cache/`
Redis cache connection management. Provides async cache operations with JSON serialization support.

#### `src/models/`
Data models and ORM definitions. Includes NewsSource, NewsItem, and other domain models.

### Feature Modules

#### `src/crawler/`
News crawler implementation. Handles fetching news from configured sources with timeout and error handling.

#### `src/ai/`
AI processing modules:
- `llm_client.py`: Alibaba Bailian Qwen3 API client
- `deduplication.py`: Semantic similarity-based news deduplication
- `classification.py`: Topic classification using LLM

#### `src/agent/`
LangChain-based AI agent that coordinates the news processing pipeline (crawl → deduplicate → classify → store).

#### `src/api/`
FastAPI web API implementation. Provides REST endpoints for news access and system monitoring.

### Test Organization

#### `tests/unit/`
Unit tests for individual components. Tests specific examples, edge cases, and error conditions.

#### `tests/property/`
Property-based tests using Hypothesis. Verifies universal properties across random inputs.

#### `tests/integration/`
End-to-end integration tests. Tests complete workflows across multiple components.

#### `tests/fixtures/`
Shared test data, mock objects, and test utilities.

## Configuration Files

### `requirements.txt`
Python package dependencies. Install with: `pip install -r requirements.txt`

### `.env.example` / `.env`
Environment variables for database, Redis, API keys, and application settings.

### `config/news_sources.json`
JSON configuration for news sources to crawl. Each source includes URL, CSS selectors, and crawl rules.

### `pytest.ini`
Pytest configuration including test discovery patterns, markers, and coverage settings.

### `docker-compose.yml`
Docker services for local development (PostgreSQL and Redis).

## Setup Scripts

### `setup.sh` / `setup.bat`
Automated setup scripts that:
1. Create Python virtual environment
2. Install dependencies
3. Copy configuration templates
4. Start Docker services

### `verify_setup.py`
Verification script that checks if all required files and directories are present.

## Development Workflow

1. **Initial Setup**: Run `./setup.sh` (or `setup.bat` on Windows)
2. **Configuration**: Edit `.env` and `config/news_sources.json`
3. **Development**: Implement features according to tasks.md
4. **Testing**: Run `pytest` to execute test suite
5. **Running**: Start with `uvicorn src.main:app --reload`

## Next Steps

After Task 1 (infrastructure setup), the following modules will be implemented:

- Task 2: Data models and database schema
- Task 3: News source configuration management
- Task 5: News crawler
- Task 6: LLM client
- Task 7: Deduplication engine
- Task 8: Classification engine
- Task 10: AI agent coordinator
- Task 14: Web API
- Task 15: Web frontend

See `tasks.md` for the complete implementation plan.
