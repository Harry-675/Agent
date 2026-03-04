# News Crawler Module

新闻爬虫模块，负责从配置的新闻源抓取新闻内容。

## 功能特性

- ✅ 异步并发抓取多个新闻源
- ✅ 网页内容解析（标题、摘要、链接、发布时间）
- ✅ 超时控制（默认30秒）
- ✅ 错误处理和日志记录
- ✅ 只抓取启用的新闻源
- ✅ 单个源失败不影响其他源

## 使用方法

### 基本用法

```python
import asyncio
from src.crawler.news_crawler import NewsCrawler
from src.models.news_source import NewsSource

# 创建新闻源配置
sources = [
    NewsSource(
        id="source-1",
        name="示例新闻网站",
        url="https://example.com/news",
        enabled=True,
        crawl_rules={
            "container": "article.news-item",
            "title": "h2.title",
            "link": "a.read-more",
            "summary": "p.summary",
            "published_at": "time.published"
        },
        timeout=30
    )
]

# 创建爬虫实例
crawler = NewsCrawler(sources)

# 抓取所有启用的新闻源
async def main():
    news_items = await crawler.crawl_all()
    print(f"获取了 {len(news_items)} 条新闻")
    
    # 检查错误日志
    errors = crawler.get_error_logs()
    if errors:
        print(f"发生了 {len(errors)} 个错误")

asyncio.run(main())
```

### 抓取单个新闻源

```python
# 抓取特定的新闻源
news_items = await crawler.crawl_source(sources[0])
```

### 自定义配置

```python
# 自定义超时时间和并发数
crawler = NewsCrawler(
    sources=sources,
    timeout=60,  # 60秒超时
    max_concurrent=5  # 最多同时抓取5个源
)
```

## 爬取规则配置

爬取规则使用CSS选择器来定位网页元素：

```python
crawl_rules = {
    # 必需：新闻容器选择器（如果没有，使用整个页面）
    "container": "article.news-item",
    
    # 必需：标题选择器
    "title": "h2.title",
    
    # 必需：链接选择器
    "link": "a.read-more",
    
    # 可选：摘要选择器（如果没有，使用标题作为摘要）
    "summary": "p.summary",
    
    # 可选：发布时间选择器（如果没有，使用当前时间）
    "published_at": "time.published"
}
```

### CSS选择器示例

- `article.news-item` - 选择class为news-item的article元素
- `h2.title` - 选择class为title的h2元素
- `a.read-more` - 选择class为read-more的a元素
- `p.summary` - 选择class为summary的p元素
- `time.published` - 选择class为published的time元素

## 错误处理

爬虫会自动处理以下错误：

1. **网络错误**: 连接失败、超时、DNS错误
2. **解析错误**: 网页结构变化、选择器不匹配
3. **系统错误**: 其他未预期的错误

所有错误都会被记录到错误日志中，可以通过 `get_error_logs()` 获取：

```python
error_logs = crawler.get_error_logs()
for log in error_logs:
    print(f"{log.error_type}: {log.error_message}")
    print(f"来源: {log.context['source_name']}")
```

## 返回的数据结构

每条新闻返回一个 `NewsItem` 对象：

```python
NewsItem(
    id="uuid",
    title="新闻标题",
    summary="新闻摘要",
    url="https://example.com/news/1",
    published_at=datetime(2024, 1, 15, 10, 0, 0),
    source_id="source-1",
    source_name="示例新闻网站",
    categories=[],  # 分类将在后续步骤中添加
    source_tags=["示例新闻网站"],
    created_at=datetime.now(),
    updated_at=datetime.now()
)
```

## 性能特性

- **并发抓取**: 使用asyncio并发抓取多个新闻源
- **超时控制**: 每个源有独立的超时设置（默认30秒）
- **并发限制**: 可配置最大并发数（默认10个）
- **错误隔离**: 单个源失败不影响其他源的抓取

## 注意事项

1. **遵守robots.txt**: 使用前请确保遵守目标网站的robots.txt规则
2. **访问频率**: 合理设置抓取间隔，避免对目标网站造成负担
3. **选择器维护**: 网站结构变化时需要更新CSS选择器
4. **相对URL**: 爬虫会自动将相对URL转换为绝对URL
5. **User-Agent**: 爬虫使用标准的浏览器User-Agent

## 测试

运行单元测试：

```bash
pytest tests/unit/test_news_crawler.py -v
```

运行集成测试：

```bash
pytest tests/integration/test_crawler_integration.py -v -m integration
```

## 相关模块

- `src.models.news_source`: 新闻源数据模型
- `src.models.news_item`: 新闻条目数据模型
- `src.models.error_log`: 错误日志数据模型
- `src.config.settings`: 配置管理

## 下一步

爬虫抓取的新闻将传递给：

1. **去重引擎** (`DeduplicationEngine`): 识别重复新闻
2. **分类器** (`CategoryClassifier`): 对新闻进行主题分类
3. **智能体** (`NewsAggregatorAgent`): 协调整个处理流程
