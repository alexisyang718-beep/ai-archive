# Tech Daily Brief V2

简化版工作流 - 专注于核心功能：
1. 数据采集与监控
2. 话题聚类
3. 选题报告

## 目录结构

```
v2/
├── archive/daily/YYYY-MM-DD/    # 采集数据
│   ├── x.jsonl                  # X/Twitter
│   ├── weibo.jsonl              # 微博
│   └── rss.jsonl                # RSS
├── reports/                     # 生成的报告
│   ├── monitor_YYYY-MM-DD.html  # 监控报告
│   ├── topics_YYYY-MM-DD.html   # 话题聚类报告
│   └── selection_YYYY-MM-DD.html # 选题报告
├── config/
│   └── atom_schema.json         # 数据格式定义
└── scripts/
    ├── collector.py             # 主采集脚本
    ├── monitor_report.py        # 监控报告生成
    ├── topic_report.py          # 话题聚类报告
    ├── selection_report.py      # 选题报告
    └── atom_store.py            # 数据存储
```

## 六大板块

| 板块 | 标识 | 说明 |
|------|------|------|
| AI模型与产品 | 🤖 ai_models | OpenAI、DeepSeek、Kimi等 |
| 手机与消费电子 | 📱 mobile | iPhone、华为、小米等 |
| 芯片与算力 | 🔧 chips | NVIDIA、台积电、AI芯片等 |
| 游戏行业 | 🎮 gaming | PlayStation、Steam、原神等 |
| 科技行业动态 | 🏢 tech_industry | 融资、IPO、财报等 |
| 政策与监管 | 📜 policy | 监管政策、贸易、制裁等 |

## 工作流程

### 1. 数据采集

```bash
# 采集全部渠道
python v2/scripts/collector.py

# 只采集X
python v2/scripts/collector.py --source x

# 只采集微博
python v2/scripts/collector.py --source weibo

# 只采集RSS
python v2/scripts/collector.py --source rss
```

### 2. 生成监控报告

查看每次爬取的状态和统计：

```bash
# 终端输出
python v2/scripts/monitor_report.py --date 2026-03-23

# 生成HTML
python v2/scripts/monitor_report.py --date 2026-03-23 --html

# 指定输出路径
python v2/scripts/monitor_report.py --date 2026-03-23 --html --output report.html
```

**监控报告包含：**
- 各渠道采集状态（成功/失败）
- 采集数量统计
- 板块分布
- 信源质量分布（L1/L2/L3）
- 热门实体TOP10
- 活跃作者TOP10

### 3. 生成话题聚类报告

自动识别当日热门话题：

```bash
python v2/scripts/topic_report.py --date 2026-03-23

# 指定输出路径
python v2/scripts/topic_report.py --date 2026-03-23 --output topics.html
```

**话题聚类报告包含：**
- 按实体共现自动聚类
- 每个话题的关联内容
- 话题重要性排序
- 信源质量标识

### 4. 生成选题报告

人工筛选日报内容：

```bash
python v2/scripts/selection_report.py --date 2026-03-23

# 指定输出路径
python v2/scripts/selection_report.py --date 2026-03-23 --output selection.html
```

**选题报告包含：**
- 按板块预筛选候选内容
- 基于信源质量和内容类型打分
- 可交互式勾选
- 一键导出选中项

## 每日工作流

```
早上来到公司
    ↓
1. 运行采集（如未自动运行）
   python v2/scripts/collector.py
    ↓
2. 查看监控报告
   python v2/scripts/monitor_report.py --date $(date +%Y-%m-%d) --html
    ↓
3. 查看话题聚类
   python v2/scripts/topic_report.py --date $(date +%Y-%m-%d)
    ↓
4. 生成选题报告并人工筛选
   python v2/scripts/selection_report.py --date $(date +%Y-%m-%d)
    ↓
5. 基于选题报告编写日报（使用原系统）
```

## 数据格式

### Atom 格式 (JSONL)

```json
{
  "id": "atom_20260323_001",
  "date": "2026-03-23",
  "title": "推文内容",
  "summary_zh": "中文摘要",
  "source": {
    "platform": "x",
    "author": "@OpenAI",
    "author_type": "official",
    "url": "https://x.com/...",
    "timestamp": "2026-03-23T10:00:00Z"
  },
  "category": "ai_models",
  "tags": ["openai", "gpt"],
  "entities": ["OpenAI", "GPT-4"],
  "trust_default": "L1",
  "content_type": "official"
}
```

## 与原系统的关系

```
┌─────────────────┐         ┌─────────────────┐
│    原系统        │         │    V2 系统       │
│  (tech-daily-brief) │     │  (v2/)          │
│                 │         │                 │
│ • 日报生成       │ ←──── │ • 数据采集       │
│ • 邮件发送       │   人工 │ • 自动分类       │
│ • 公众号发布     │   筛选 │ • 话题聚类       │
│                 │         │ • 选题建议       │
└─────────────────┘         └─────────────────┘
```

V2 负责**数据层和预选**，原系统负责**最终日报生成和发布**。
