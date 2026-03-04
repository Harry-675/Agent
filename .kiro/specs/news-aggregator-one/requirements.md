# 需求文档

## 简介

"one"是一个智能新闻聚合平台，旨在从多个新闻源自动抓取、分析、去重和分类新闻内容，为用户提供简洁统一的新闻浏览体验。系统通过大模型技术识别重复新闻，并按主题分类展示，减少用户在多个新闻网站间切换的时间成本。

## 术语表

- **News_Aggregator**: 新闻聚合系统，负责整体协调和管理
- **News_Crawler**: 新闻爬虫模块，负责从指定新闻源抓取新闻内容
- **AI_Agent**: 智能体模块，负责新闻分析、去重和分类
- **Deduplication_Engine**: 去重引擎，使用大模型识别相同新闻
- **Category_Classifier**: 分类器，将新闻分配到不同主题板块
- **Web_Interface**: 网页界面，向用户展示聚合后的新闻
- **News_Source**: 新闻源，指定的新闻网站列表
- **News_Item**: 新闻条目，包含标题、内容、来源、时间等信息
- **Topic_Category**: 主题分类，如金融、科技、体育等
- **Source_Tag**: 来源标签，标注新闻的多个来源

## 需求

### 需求 1: 配置新闻源列表

**用户故事:** 作为系统管理员，我希望能够配置要抓取的新闻网站列表，以便系统知道从哪些网站获取新闻。

#### 验收标准

1. THE News_Aggregator SHALL 支持配置多个 News_Source 的 URL 列表
2. THE News_Aggregator SHALL 为每个 News_Source 存储名称、URL 和抓取规则
3. WHEN 添加新的 News_Source 时，THE News_Aggregator SHALL 验证 URL 的有效性
4. THE News_Aggregator SHALL 支持启用或禁用特定的 News_Source

### 需求 2: 抓取新闻头条

**用户故事:** 作为系统，我需要定期从配置的新闻源抓取最新头条，以便为用户提供最新的新闻内容。

#### 验收标准

1. WHEN 执行抓取任务时，THE News_Crawler SHALL 访问所有已启用的 News_Source
2. THE News_Crawler SHALL 从每个 News_Source 提取新闻标题、摘要、链接和发布时间
3. WHEN 抓取失败时，THE News_Crawler SHALL 记录错误日志并继续处理其他 News_Source
4. THE News_Crawler SHALL 在 30 秒内完成单个 News_Source 的抓取，否则超时
5. THE News_Crawler SHALL 每 15 分钟自动执行一次抓取任务

### 需求 3: 新闻去重识别

**用户故事:** 作为用户，我希望系统能够识别并合并相同的新闻，避免看到重复内容。

#### 验收标准

1. WHEN 接收到新的 News_Item 时，THE Deduplication_Engine SHALL 使用大模型分析其与已有新闻的相似度
2. IF 两条 News_Item 的相似度超过 85%，THEN THE Deduplication_Engine SHALL 将它们标记为重复新闻
3. WHEN 识别到重复新闻时，THE Deduplication_Engine SHALL 保留最早发布的 News_Item 作为主条目
4. THE Deduplication_Engine SHALL 将所有重复新闻的 Source_Tag 合并到主条目上
5. THE Deduplication_Engine SHALL 在 5 秒内完成单条新闻的去重分析

### 需求 4: 新闻主题分类

**用户故事:** 作为用户，我希望新闻能够按主题分类展示，方便我快速找到感兴趣的内容。

#### 验收标准

1. THE Category_Classifier SHALL 支持至少以下 Topic_Category：金融、科技、体育、娱乐、政治、健康
2. WHEN 处理 News_Item 时，THE Category_Classifier SHALL 使用大模型分析其内容并分配到对应的 Topic_Category
3. THE Category_Classifier SHALL 为每条 News_Item 分配至少一个 Topic_Category
4. WHERE News_Item 涉及多个主题，THE Category_Classifier SHALL 分配最多 3 个 Topic_Category
5. THE Category_Classifier SHALL 在 3 秒内完成单条新闻的分类

### 需求 5: 智能体协调处理

**用户故事:** 作为系统，我需要一个智能体来协调新闻的抓取、分析、去重和分类流程。

#### 验收标准

1. THE AI_Agent SHALL 协调 News_Crawler、Deduplication_Engine 和 Category_Classifier 的执行顺序
2. WHEN 新闻抓取完成时，THE AI_Agent SHALL 自动触发去重和分类流程
3. IF 任何处理步骤失败，THEN THE AI_Agent SHALL 记录错误并继续处理其他 News_Item
4. THE AI_Agent SHALL 维护处理队列，确保新闻按接收顺序处理
5. THE AI_Agent SHALL 每小时生成处理统计报告，包括抓取数量、去重数量和分类分布

### 需求 6: 网页界面展示

**用户故事:** 作为用户，我希望通过简洁美观的网页浏览聚合后的新闻。

#### 验收标准

1. THE Web_Interface SHALL 以卡片形式展示每条 News_Item，包含标题、摘要、时间和来源标签
2. THE Web_Interface SHALL 提供按 Topic_Category 筛选新闻的导航菜单
3. WHEN News_Item 有多个 Source_Tag 时，THE Web_Interface SHALL 在标题右上角用数字上标显示来源数量
4. WHEN 用户点击来源上标时，THE Web_Interface SHALL 显示所有来源的列表
5. THE Web_Interface SHALL 使用响应式设计，支持桌面和移动设备访问
6. THE Web_Interface SHALL 在 2 秒内加载首页内容
7. THE Web_Interface SHALL 使用简洁的配色方案和清晰的排版

### 需求 7: 新闻详情访问

**用户故事:** 作为用户，我希望能够点击新闻标题跳转到原始新闻页面，阅读完整内容。

#### 验收标准

1. WHEN 用户点击 News_Item 标题时，THE Web_Interface SHALL 在新标签页打开原始新闻链接
2. WHERE News_Item 有多个来源，THE Web_Interface SHALL 默认打开最早发布的来源链接
3. THE Web_Interface SHALL 在新闻卡片上显示"查看其他来源"选项，允许用户选择其他来源链接

### 需求 8: 数据持久化存储

**用户故事:** 作为系统，我需要持久化存储新闻数据，以便支持历史查询和数据分析。

#### 验收标准

1. THE News_Aggregator SHALL 将所有 News_Item 存储到数据库中
2. THE News_Aggregator SHALL 为每条 News_Item 存储标题、摘要、链接、发布时间、来源、分类和去重关系
3. THE News_Aggregator SHALL 保留最近 30 天的新闻数据
4. WHEN 数据超过 30 天时，THE News_Aggregator SHALL 自动归档或删除旧数据
5. THE News_Aggregator SHALL 支持按时间范围、分类和关键词查询历史新闻

### 需求 9: 错误处理和监控

**用户故事:** 作为系统管理员，我需要了解系统运行状态和错误情况，以便及时处理问题。

#### 验收标准

1. WHEN 发生系统错误时，THE News_Aggregator SHALL 记录详细的错误日志，包括时间戳、错误类型和堆栈信息
2. IF News_Source 连续 3 次抓取失败，THEN THE News_Aggregator SHALL 发送告警通知
3. THE News_Aggregator SHALL 提供健康检查接口，返回各模块的运行状态
4. THE News_Aggregator SHALL 监控大模型 API 的调用次数和响应时间
5. IF 大模型 API 调用失败，THEN THE News_Aggregator SHALL 使用降级策略（如基于关键词的简单去重和分类）

### 需求 10: 性能和可扩展性

**用户故事:** 作为系统架构师，我需要确保系统能够处理大量新闻源和用户访问。

#### 验收标准

1. THE News_Aggregator SHALL 支持同时配置至少 50 个 News_Source
2. THE News_Aggregator SHALL 每小时处理至少 1000 条 News_Item
3. THE Web_Interface SHALL 支持至少 100 个并发用户访问
4. THE News_Aggregator SHALL 使用缓存机制，减少数据库查询次数
5. WHERE 系统负载超过 80%，THE News_Aggregator SHALL 自动限流，优先保证核心功能

## 附加说明

### 技术选型

本项目采用以下技术栈：

#### 智能体框架
- **LangChain**: 用于构建和协调 AI_Agent，管理新闻处理流程

#### 大模型
- **阿里百炼平台 Qwen3**: 用于以下功能：
  - 新闻相似度分析和去重
  - 新闻主题分类
  - 可选：新闻摘要生成

#### 其他技术建议
- 后端：Python + 异步任务队列
- 前端：现代 Web 框架（React/Vue）
- 数据库：关系型数据库（PostgreSQL）+ 缓存（Redis）
- 爬虫：遵守 robots.txt 和网站使用条款

### 合规性考虑

- 遵守各新闻网站的使用条款和 robots.txt 规则
- 尊重版权，仅展示标题和摘要，引导用户访问原始链接
- 实现合理的访问频率限制，避免对新闻源造成负担
