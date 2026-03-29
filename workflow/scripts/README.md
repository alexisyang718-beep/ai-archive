# 工作流脚本

> 自动化脚本集合，减少AI工作量

## 脚本清单

| 脚本 | 功能 | 对应工作流 |
|------|------|-----------|
| `01_preprocess_candidates.py` | 选题预处理：去重/过滤/打标 | 2.选题报告 |
| `02_fetch_fulltext.py` | 全文抓取：批量Jina Reader | 3.撰写日报 |
| `03_publish_pipeline.py` | 发布流水线：GitHub/邮件/公众号 | 4.发布流程 |

## 使用方法

### 1. 选题预处理

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief
python3 workflow/scripts/01_preprocess_candidates.py 2026-03-26
```

**输出**: `workflow/output/candidates_2026-03-26.csv`

**CSV字段**:
- `platform`: X/微博/RSS
- `title`: 标题/摘要
- `content`: 完整内容
- `source_name`: 来源名称
- `source_url`: 原始链接
- `source_label`: 一手官方/一手媒体/二手编译
- `module`: AI模型/芯片/手机/游戏/政策/科技动态
- `created_at`: 发布时间

### 2. 全文抓取

```bash
python3 workflow/scripts/02_fetch_fulltext.py 2026-03-26
```

**前置条件**: 已生成选题报告 `v2/docs/daily_selection_2026-03-26.md`

**输出**: `workflow/output/fulltext_2026-03-26.json`

### 3. 发布流水线

```bash
python3 workflow/scripts/03_publish_pipeline.py 2026-03-26
```

**流程**:
1. GitHub Push
2. 发送测试邮件
3. 等待人工确认
4. 群发邮件
5. 同步公众号

## 输出目录

```
workflow/output/
├── candidates_YYYY-MM-DD.csv    # 候选新闻（预处理输出）
└── fulltext_YYYY-MM-DD.json     # 原文缓存（全文抓取输出）
```

## AI使用流程

### 工作流2: 选题报告（更新后）

```
脚本: 01_preprocess_candidates.py → 输出candidates.csv
                                ↓
AI: 读取candidates.csv + news-preferences.md → 生成选题报告
                                ↓
人工: 确认选题
```

### 工作流3: 撰写日报（更新后）

```
脚本: 02_fetch_fulltext.py → 输出fulltext.json
                        ↓
AI: 读取fulltext.json + 人工确认的选题 + template.html → 撰写日报
```

### 工作流4: 发布流程（更新后）

```
脚本: 03_publish_pipeline.py → 自动执行GitHub/邮件/公众号
                        ↓
人工: 确认测试邮件后自动继续
```
