# 科技资讯日报工作流

> 每日 17 条精选科技资讯的生产流水线  
> 覆盖 AI、手机、芯片、游戏、科技动态、政策 6 大板块

---

## 一、核心指标

| 指标 | 目标 |
|------|------|
| **时效性** | 主体 24h 内，补充 48h 内 |
| **信源质量** | Tier 1-2 官方源 ≥ 50% |
| **产出数量** | 18-22 条/期，最终精选 17 条 |
| **发布渠道** | 网页 + 邮件 + 公众号 三端同步 |
| **深度洞察** | 每条含 200-300 字独立观点 |

---

## 二、信源体系（256+ 实体）

```
┌─────────────────────────────────────────────────────────────┐
│  Tier 1 · 一手核心（⭐⭐⭐⭐⭐）                              │
│  ├── AI 公司官方：OpenAI、DeepMind、Anthropic、Meta AI...    │
│  ├── 关键人物：Sam Altman、Musk、Karpathy、Jim Fan...        │
│  └── 数据平台：SteamDB、Famitsu、Circana                     │
├─────────────────────────────────────────────────────────────┤
│  Tier 2 · 专业媒体（⭐⭐⭐⭐）                                │
│  ├── 国际：TechCrunch、The Verge、Wired、Ars Technica        │
│  └── 中文：机器之心、量子位、新智元、36氪、虎嗅              │
├─────────────────────────────────────────────────────────────┤
│  Tier 3 · 社区/分析（⭐⭐⭐）                                 │
│  ├── 社区：HackerNews、GitHub Trending、Reddit               │
│  ├── 投资：红杉、Konvoy、InvestGame                          │
│  └── 学术：arXiv、Papers with Code                           │
├─────────────────────────────────────────────────────────────┤
│  Tier 4 · 聚合补充（⭐⭐）                                    │
│  └── 36氪、虎嗅、Buzzing、TopHub                             │
└─────────────────────────────────────────────────────────────┘
```

**信源配置**：`config/sources.json`（7670 行结构化数据）

---

## 三、四级漏斗采集流程

```
L0  X/Twitter Following  →  twitter-cli 获取关注时间线
     🚫 硬性阻断点：失败必须停止，禁止跳过
     
L0.5 微博采集           →  weibo-cli 采集 10 位科技博主

L1  聚合扫描            →  按板块逐个搜索关键词
     ├── twitter-cli 关键词搜索
     ├── Tavily 综合搜索
     ├── web_search 补充
     └── 中文聚合站扫描（36氪/虎嗅/IT之家）
     
L2  观点聚合            →  XClaw/Grok 搜索 X 讨论
                         汇总多方观点，辅助写洞察
                         
L3  深度抓取            →  Jina Reader 抓全文
                         每期 3-5 篇，洞察必须基于全文
```

**产出漏斗**：30-50 条 → 筛选至 18-22 条 → 最终 17 条

---

## 四、内容生产标准

### 4.1 板块结构

| 板块 | 数量 | 关键词示例 |
|------|------|-----------|
| 🧠 AI 模型与产品 | 3-4 条 | GPT、Claude、Gemini、DeepSeek |
| 📱 手机与消费电子 | 3-4 条 | iPhone、Samsung、小米、华为 |
| 🔧 芯片与算力 | 2-3 条 | NVIDIA、AMD、台积电、昇腾 |
| 🎮 游戏行业 | 2-3 条 | Steam、PS5、Xbox、GDC |
| 🏛️ 科技行业动态 | 2-3 条 | 融资、并购、财报、裁员 |
| 📜 政策与监管 | 1-2 条 | AI 法规、反垄断、出口管制 |

### 4.2 单条新闻结构

```html
<div class="item">
  <!-- 标题 + 标签 -->
  <div class="item-title">
    <span class="tag tag-new">新品</span>
    苹果发布 AirPods Max 2：H2 芯片驱动，降噪提升 1.5 倍
  </div>
  
  <!-- 正文（100-150 字） -->
  <div class="item-body">
    3 月 16 日，苹果正式发布 AirPods Max 2...（核心事实）
  </div>
  
  <!-- 数据标签 -->
  <div class="stat-row">
    <span class="stat">芯片 <em>H2</em></span>
    <span class="stat">降噪 <em>提升 1.5 倍</em></span>
    <span class="stat">售价 <em>3999 元</em></span>
  </div>
  
  <!-- 来源（标注一手/二手） -->
  <div class="item-source">
    来源：<a href="...">IT之家</a> ｜ <a href="...">9to5Mac</a>
  </div>
  
  <!-- 深度洞察（200-300 字，必须基于全文） -->
  <div class="insight-box">
    <div class="insight-label">💡 深度洞察</div>
    <div class="insight-content">
      AirPods Max 2 最大的信号不是产品本身，而是苹果的定价策略...
    </div>
  </div>
</div>
```

### 4.3 洞察写作原则

- **禁止**：仅凭搜索摘要写洞察
- **必须**：基于全文 + XClaw 观点搜索 + 权威观点支撑
- **角度**：定价策略、技术路线、行业影响、竞争格局

---

## 五、三端发布流程

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: GitHub Pages                                       │
│  ├── 文件：brief/YYYY-MM-DD.html                            │
│  ├── 命令：git push origin main                             │
│  └── 地址：https://alexisyang718-beep.github.io/ai-archive/ │
├─────────────────────────────────────────────────────────────┤
│  Step 2: 邮件推送                                           │
│  ├── 脚本：scripts/send_email.py                            │
│  ├── 渠道：QQ 邮箱 SMTP（smtp.qq.com:465）                  │
│  ├── 收件人：8 位                                           │
│  └── 适配：premailer CSS 内联 + 移动端优化                  │
├─────────────────────────────────────────────────────────────┤
│  Step 3: 公众号                                             │
│  ├── 脚本：raphael-publish/publish-daily.mjs                │
│  ├── 排版：Raphael 引擎（NYT 主题）                         │
│  └── 输出：微信公众号草稿箱                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、质量检查清单

```
□ 已读取 config/search_keywords.yaml，使用配置关键词搜索
□ 已读取 template.html，HTML 基于模板生成
□ X/Twitter 已通过 twitter-cli 采集（🚫 未完成则整期作废）
□ 微博已通过 weibo-cli 采集
□ 重点话题已通过 XClaw 扫描/手动搜索 X 讨论
□ 时效性：全部新闻在 48h 内，主体在 24h 内
□ 信源：官方一手源 ≥ 5 条
□ 信源：禁止用二手转载（新浪/搜狐/腾讯科技）作为主要信源
□ 深度：至少 3-5 篇全文抓取 + XClaw 观点搜索
□ 数量：每板块 ≥ 5 条新闻
□ 输出：文件保存到 brief/YYYY-MM-DD.html
□ 首页：index.html 已更新
```

---

## 七、项目结构

```
tech-daily-brief/
├── README.md                  ← 工作流入口（AI 执行必读）
├── template.html              ← 日报 HTML 模板
├── index.html                 ← 存档首页
├── brief/                     ← 日报输出（17 期）
├── config/
│   ├── sources.json           ← 256+ 信源实体（7670 行）
│   ├── search_keywords.yaml   ← 搜索关键词（6 板块）
│   ├── gaming_sources.yaml    ← 游戏专属信源（130+）
│   ├── weibo_users.yaml       ← 微博博主（10 位）
│   └── x_twitter_watchlist.md ← X/Twitter KOL（20+）
├── docs/
│   ├── workflow.md            ← 本文件
│   ├── quality_rules.md       ← 质量红线详细说明
│   └── lessons_learned.md     ← 踩坑记录
└── scripts/
    ├── send_email.py          ← 邮件发送脚本
    └── weibo_fetch.py         ← 微博采集脚本
```

---

## 八、关键工具链

| 工具 | 用途 |
|------|------|
| **twitter-cli** | X/Twitter 采集（Following/搜索） |
| **weibo-cli** | 微博博主采集 |
| **Tavily MCP** | 综合搜索 + 网页提取 |
| **Jina Reader** | 全文抓取（首选） |
| **XClaw** | X 内容聚合/观点搜索 |
| **Raphael** | 公众号排版引擎 |
| **premailer** | 邮件 CSS 内联 |

---

## 九、数据沉淀

- **已发布期数**：13 期（2026-03-05 至 2026-03-17）
- **覆盖信源**：256+ 实体，20+ 平台
- **存档地址**：https://alexisyang718-beep.github.io/ai-archive/

---

> **核心优势**：系统化漏斗采集 + 结构化信源管理 + 三端同步发布 + 独立深度洞察
