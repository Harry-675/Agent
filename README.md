# One - 智能新闻聚合平台

一个基于大模型的智能新闻聚合系统，自动抓取、去重、分类和展示新闻内容。

## 功能特性

- 🔍 **多引擎搜索**: 支持 Google、Bing、百度等搜索引擎，快速切换
- 📰 **RSS 新闻聚合**: 支持 RSS 订阅源，自动抓取并聚合新闻
- 🤖 **智能去重**: 使用阿里百炼 Qwen3 模型识别重复新闻
- 🏷️ **自动分类**: 自动将新闻分配到科技、金融、体育等主题类别
- 🎨 **简洁界面**: Tab 键快速切换搜索和新闻视图
- ⚡ **高性能**: Redis 缓存 + 异步处理

## 技术栈

- **后端**: Python 3.11+, FastAPI, LangChain
- **大模型**: 阿里百炼平台 Qwen3
- **数据库**: PostgreSQL
- **缓存**: Redis
- **任务调度**: APScheduler
- **前端**: 原生 HTML/CSS/JS，单页面应用
- **测试**: pytest, hypothesis

## 快速开始

### 1. 环境准备

确保已安装以下软件：
- Python 3.11+
- PostgreSQL 14+
- Redis 7+

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入实际配置
# 特别注意配置阿里百炼 API 密钥
```

### 4. 初始化数据库

```bash
# 创建数据库
createdb news_aggregator
```

### 5. 配置新闻源

配置文件位于 `config/news_sources.json`，支持以下字段：

```json
{
  "id": "unique-id",
  "name": "新闻源名称",
  "url": "RSS 订阅地址",
  "enabled": true,
  "crawl_rules": {
    "type": "rss",
    "category": "科技"
  },
  "timeout": 30
}
```

### 6. 运行应用

```bash
# 启动 API 服务器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. 访问 Web 界面

打开浏览器访问 http://localhost:8000

- 按 **Tab** 键切换搜索/新闻视图
- 点击右上角 **设置** 图标配置搜索引擎和新闻源

## 使用指南

### 搜索引擎

在设置中可以：
- 添加新的搜索引擎（填入名称和 URL 模板，URL 模板使用 `{q}` 或 `?wd=` 结尾）
- 删除不需要的搜索引擎
- 开关单个搜索引擎
- 设置默认搜索引擎

URL 模板示例：
- Google: `https://www.google.com/search?q=`
- 百度: `https://www.baidu.com/s?wd=`
- Bing: `https://www.bing.com/search?q=`

### 新闻源

在设置中可以：
- 添加新的 RSS 订阅源
- 删除不需要的新闻源
- 开关单个新闻源
- 选择新闻分类（综合、科技、金融、体育、娱乐、政治、健康）

### 预置新闻源

项目默认配置了以下中文 RSS 源：
- 腾讯新闻
- 知乎日报
- 网易新闻
- 新浪财经
- 36氪
- 爱范儿
- 虎嗅

## 项目结构

```
.
├── src/                    # 源代码
│   ├── api/               # Web API 路由
│   ├── agent/             # 智能体协调器
│   ├── ai/                # AI 处理模块（分类、去重）
│   ├── config/            # 配置模块
│   ├── crawler/           # 新闻爬虫
│   ├── database/          # 数据库连接和操作
│   └── models/            # 数据模型
├── static/                # 静态文件（前端）
│   └── index.html         # 单页面应用
├── config/                # 配置文件
│   └── news_sources.json  # 新闻源配置
├── tests/                 # 测试
│   ├── unit/             # 单元测试
│   ├── property/         # 属性测试
│   └── integration/      # 集成测试
├── requirements.txt      # Python 依赖
├── .env.example         # 环境变量模板
└── README.md            # 项目文档
```

## API 文档

启动服务后，访问以下地址查看 API 文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

主要 API 端点：
- `GET /api/news` - 获取新闻列表（支持分类筛选）
- `GET /api/news/sources` - 获取新闻源列表
- `POST /api/news/sources` - 添加新闻源
- `POST /api/news/sources/{id}/toggle` - 切换新闻源开关
- `DELETE /api/news/sources/{id}` - 删除新闻源
- `POST /api/news/trigger-crawl` - 手动触发抓取

## 开发指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 代码风格

项目遵循 PEP 8 代码规范。

## 许可证

MIT License