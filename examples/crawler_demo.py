"""Demo script showing how to use the NewsCrawler."""

import asyncio
import uuid
from datetime import datetime

from src.crawler.news_crawler import NewsCrawler
from src.models.news_source import NewsSource


async def main():
    """演示NewsCrawler的使用"""
    
    # 创建示例新闻源配置
    # 注意：这些是示例配置，实际使用时需要根据目标网站的HTML结构调整选择器
    sources = [
        NewsSource(
            id=str(uuid.uuid4()),
            name="示例新闻网站",
            url="https://example.com/news",
            enabled=True,
            crawl_rules={
                # container: 包含单条新闻的容器选择器
                "container": "article.news-item",
                # title: 新闻标题选择器
                "title": "h2.title",
                # link: 新闻链接选择器
                "link": "a.read-more",
                # summary: 新闻摘要选择器（可选）
                "summary": "p.summary",
                # published_at: 发布时间选择器（可选）
                "published_at": "time.published"
            },
            timeout=30
        ),
        NewsSource(
            id=str(uuid.uuid4()),
            name="另一个新闻网站",
            url="https://another-example.com/news",
            enabled=True,
            crawl_rules={
                "container": "div.article",
                "title": "h3.headline",
                "link": "a",
                "summary": "div.excerpt"
            },
            timeout=30
        ),
        NewsSource(
            id=str(uuid.uuid4()),
            name="禁用的新闻源",
            url="https://disabled.com",
            enabled=False,  # 这个源不会被抓取
            crawl_rules={"title": "h1"},
            timeout=30
        )
    ]
    
    # 创建爬虫实例
    crawler = NewsCrawler(sources, timeout=30, max_concurrent=5)
    
    print("开始抓取新闻...")
    print(f"配置了 {len(sources)} 个新闻源")
    print(f"启用的新闻源: {len([s for s in sources if s.enabled])} 个")
    print()
    
    # 抓取所有启用的新闻源
    news_items = await crawler.crawl_all()
    
    print(f"抓取完成！共获取 {len(news_items)} 条新闻")
    print()
    
    # 显示抓取到的新闻
    for i, item in enumerate(news_items, 1):
        print(f"新闻 {i}:")
        print(f"  标题: {item.title}")
        print(f"  来源: {item.source_name}")
        print(f"  链接: {item.url}")
        print(f"  摘要: {item.summary[:100]}..." if len(item.summary) > 100 else f"  摘要: {item.summary}")
        print(f"  发布时间: {item.published_at}")
        print()
    
    # 检查错误日志
    error_logs = crawler.get_error_logs()
    if error_logs:
        print(f"发生了 {len(error_logs)} 个错误:")
        for log in error_logs:
            print(f"  - {log.error_type}: {log.error_message}")
            print(f"    来源: {log.context.get('source_name', 'Unknown')}")
            print()
    
    # 单独抓取某个新闻源
    print("\n单独抓取第一个新闻源...")
    single_source_news = await crawler.crawl_source(sources[0])
    print(f"从 {sources[0].name} 获取了 {len(single_source_news)} 条新闻")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())
