# Tech Daily Brief — 科技资讯日报

> **⚠️ AI 执行入口：生成日报前必须读完本文件，并按顺序执行。**

> 🚫 **全局规则：L0 X/Twitter 采集是硬性阻断点。twitter-cli 失败或 Cookie 过期 → 必须立刻停止，告知用户，等待修复。绝对禁止跳过 L0 直接执行 L1 或后续步骤。违反此规则 = 整期日报作废。**

---

## 一、准备（采集前必做）

读取以下配置文件，后续步骤依赖这些内容：

| 文件 | 用途 | 说明 |
|------|------|------|
| `config/search_keywords.yaml` | 搜索关键词 | `en` 用于 Tavily/web_search，`zh` 用于百度/微信/中文站。按板块分类，**直接使用，不要自行编造关键词** |
| `template.html` | 日报 HTML 模板 | 必须读取此模板，填充占位符生成日报。占位符说明见模板末尾注释 |

---

## 二、采集

### 时效性

- **主体**：24 小时内
- **补充**：48 小时内可接受
- **禁止**：超过 48 小时的旧闻

### 四级漏斗

按 L0 → L1 → L2 → L3 顺序执行：

| 级别 | 动作 | 轮次 | 说明 |
|------|------|------|------|
| **L0 X/Twitter** | twitter-cli 获取 Following 时间线 | 1 轮 | 🚫 **最先执行，失败必须停止整个流程，禁止跳到 L1** |
| **L0.5 微博采集** | weibo-cli 搜索科技博主 | 1-2 轮 | 采集配置的中文科技博主最新微博，作为中文信息来源补充 |
| **L1 聚合扫描** | twitter-cli 搜索 + XClaw + Tavily | 5-7 轮 | twitter-cli 按板块搜索关键词，XClaw 补充热点扫描，Tavily 补充，详见下方 |
| **L2 观点聚合** | 手动在 XClaw/Grok 网页搜索 | 1-2 轮 | 对重点话题搜索 X 讨论，汇总多方观点，辅助写洞察 |
| **L3 深度抓取** | Jina Reader ×1-2 抓全文 | 2-3 轮 | **不可省略**，每期至少 3-5 篇全文 |

产出 30-50 条 → 筛选至 18-22 条。

### L0 X/Twitter 采集（🚫 硬性阻断点 — 失败必须停止，禁止继续）

> 🚫🚫🚫 **绝对禁止跳过 L0。twitter-cli 失败、Cookie 过期、任何错误 → 必须立即停止整个日报流程，告知用户，等用户确认修复后才能继续。绝对不允许"先跳过 L0 继续 L1"。如果你跳过了 L0，整期日报作废。**

#### 环境准备

```bash
# 确保 twitter-cli 已安装
uv tool install twitter-cli

# 设置 PATH
export PATH="/Users/yangliu/.local/bin:$PATH"
```

#### 配置 Cookie

Cookie 需要从浏览器手动获取（X 的 Cookie 有效期约 30 天）：

1. 登录 X.com
2. 浏览器按 F12 → Application → Cookies → x.com
3. 导出 `auth_token` 和 `ct0` 两个值
4. 设置环境变量：

```bash
export TWITTER_AUTH_TOKEN="你的 auth_token"
export TWITTER_CT0="你的 ct0"
```

**Cookie 保存在 `~/.twitter-cli/sessions.yaml`**，后续运行会自动读取。

#### 采集命令

```bash
export PATH="/Users/yangliu/.local/bin:$PATH"

# 获取关注时间线（推荐，产出更精准）
twitter feed -t following --max 50 --yaml

# 获取推荐时间线
twitter feed --max 50 --yaml

# 搜索特定关键词
twitter search "AI news today" --max 20 --yaml
```

**输出格式**：YAML/JSON 结构化输出，直接解析使用。

#### 提取字段

twitter-cli 返回的每条推文包含以下字段：

| 字段 | 说明 |
|------|------|
| `id` | 推文 ID |
| `text` | 推文内容 |
| `author.screenName` | 用户名（如 @sama） |
| `author.name` | 显示名 |
| `createdAtLocal` | 本地时间 |
| `metrics` | 互动数据（likes/retweets/views） |
| `media` | 媒体附件 |

#### 故障排查

| 问题 | 解决方案 |
|------|----------|
| `twitter: command not found` | `export PATH="/Users/yangliu/.local/bin:$PATH"` |
| `authenticated: false` | Cookie 过期，重新获取并设置环境变量 |
| 请求超时/限流 | 等待 1-2 分钟后重试，控制请求频率 |

---

### L0.5 微博采集（weibo-cli）

> 微博采集作为中文科技信息来源的补充，采集配置的中文科技博主最新微博。

#### 环境准备

```bash
# 确保 weibo-cli 已安装
# 参考：https://github.com/ay147git/weibo-cli
uv tool install weibo-cli

# 设置 PATH
export PATH="/Users/yangliu/.local/bin:$PATH"
```

#### 配置 Cookie

微博需要登录 Cookie（有效期约 3 个月）：

1. 登录 weibo.com
2. 浏览器按 F12 → Application → Cookies → weibo.com
3. 导出关键 Cookie 值
4. 运行 `weibo login` 扫码登录

#### 配置文件

微博用户列表在 `config/weibo_users.yaml` 中配置：

```yaml
weibo_users:
  - name: "数码闲聊站"
    uid: "6048569942"
    category: "手机/芯片"
  - name: "机器之心"
    category: "AI/科技"
  # 添加更多博主...
```

#### 采集命令

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief

# 采集配置文件中所有博主的微博
python3 scripts/weibo_fetch.py

# 只采集指定博主（用于测试）
python3 scripts/weibo_fetch.py --user "数码闲聊站"

# 输出 JSON 格式
python3 scripts/weibo_fetch.py --json

# 每个用户采集条数（默认10）
python3 scripts/weibo_fetch.py --max 20
```

**输出字段**：

| 字段 | 说明 |
|------|------|
| `username` | 微博用户名 |
| `nickname` | 显示昵称 |
| `content_raw` | 微博正文（原始 HTML 已去除） |
| `created_at` | 发布时间 |
| `reposts_count` | 转发数 |
| `comments_count` | 评论数 |
| `attitudes_count` | 点赞数 |

#### 故障排查

| 问题 | 解决方案 |
|------|----------|
| `weibo: command not found` | `export PATH="/Users/yangliu/.local/bin:$PATH"` |
| `home` 返回 500 错误 | Cookie 过期或无效，运行 `weibo login` 重新扫码 |
| 搜索结果为空 | 检查 Cookie 是否有效，或尝试搜索其他关键词 |

---

### L1 聚合搜索（按板块逐个搜索）

**策略**：按 `search_keywords.yaml` 中的 6 个板块逐个搜索，每板块用该板块的关键词。这样保证每个板块都有足够覆盖，不会遗漏冷门板块。

**执行流程**：

1. **先搜 `global` 关键词**（"AI news today"、"tech news today" 等），作为通用热点兜底
2. **逐板块搜索**：依次用 `ai_models`、`mobile`、`chips`、`gaming`、`tech_industry`、`policy` 的关键词
3. 每板块选 2-3 组关键词（en 用 Tavily/web_search，zh 用百度/微信），不需要把所有关键词都搜一遍
4. 搜到的结果先按板块归类暂存

**工具分配**：

| 工具 | 用途 | 轮次 |
|------|------|------|
| twitter-cli | X 关键词搜索，获取原始推文数据 | 2-3 轮 |
| Tavily（`tavily_search`） | 英文关键词，综合搜索 | 1-2 轮 |
| web_search | 补充搜索，或搜 Tavily 覆盖不到的关键词 | 1-轮 |
| web_fetch（聚合站） | 扫一遍 36氪/虎嗅 等中文聚合站热榜 | 1 轮 |

**twitter-cli 搜索示例**：

```bash
export PATH="/Users/yangliu/.local/bin:$PATH"

# 按板块搜索 X
twitter search "AI OR LLM OR GPT" --lang en --since 2026-03-16 --max 20 --yaml
twitter search "NVIDIA OR AMD OR GPU" --lang en --since 2026-03-16 --max 20 --yaml
twitter search "iPhone OR Samsung" --lang en --since 2026-03-16 --max 20 --yaml

# 搜索特定用户的讨论
twitter search "Kimi" --from Kimi_Moonshot --yaml
```

**注意**：关键词允许跨板块重复（如 Google 同时出现在 AI、手机、科技），搜到的同一条新闻可能匹配多个板块——选最相关的板块放入即可，不要重复。

---

### L2 观点聚合（XClaw + 手动搜索）

> 用于对重点话题搜索 X 上的多方讨论，汇总权威观点，辅助写深度洞察。

#### XClaw（推荐）

**XClaw** (xclaw.info) 是 AI 领域 Twitter/X 内容聚合站，提供：
- 实时抓取 X 上的 AI 相关推文
- 中文摘要 + 热度排序
- 按标签筛选（AI/大模型/算力/具身智能等）

**网址**：
- 全球 AI 热点：https://xclaw.info/zh/tweets?group=global&tag=ai
- 大模型动态：https://xclaw.info/zh/tweets?tag=大模型动态
- 算力与基础设施：https://xclaw.info/zh/tweets?tag=算力与基础设施

#### 手动搜索（备选）

在以下平台手动搜索话题讨论：
- X.com 搜索
- Grok.com 搜索

#### 整合到工作流

| 场景 | 用法 |
|------|------|
| 快速扫描 | 打开 XClaw 热点页面，快速浏览遗漏的热点 |
| 获取观点 | 对候选新闻搜索"X 上谁在讨论" |
| 交叉验证 | 搜索"这个说法对不对" |

**输出**：XClaw 的中文摘要可直接参考，引用来源@XX 作为洞察支撑。

---

## 三、生成

### 步骤

1. **读取模板**：`template.html`（必须先 read_file，占位符说明见模板末尾注释）
2. **填充占位符**：用采集到的新闻替换模板中的 `{{PLACEHOLDER}}`
3. **输出文件**：`brief/YYYY-MM-DD.html`（YYYY-MM-DD 为当天日期）

### 6 大板块

1. 🧠 AI 模型与产品
2. 📱 手机与消费电子
3. 🔧 芯片与算力
4. 🎮 游戏行业
5. 🏛️ 科技行业动态
6. 📜 政策与监管

### 每条新闻结构

标题 + 标签 + 正文 + 数据标签 + 来源（标注一手/二手） + 深度洞察（≤300 字符，必须基于全文撰写）。

**HTML 结构和 CSS class 参考 `template.html` 末尾的注释示例。**

---

## 四、发布（按顺序执行）

### Step 1：GitHub Pages

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy
git add tech-daily-brief/brief/YYYY-MM-DD.html
git commit -m "Add daily brief YYYY-MM-DD"
git push origin main
```

在线地址：`https://alexisyang718-beep.github.io/ai-archive/brief/YYYY-MM-DD.html`

### Step 2：发送测试邮件

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief

# ✅ 正确：指定文件 + 指定单人测试邮箱
python scripts/send_email.py brief/YYYY-MM-DD.html --to alexisyang@tencent.com
```

- **必须指定文件路径**（不传文件路径时脚本会默认选 index.html，不是日报）
- **测试邮件必须加 `--to alexisyang@tencent.com`**，默认会发给全部 23 人
- 发送前会显示预览（收件人列表 + 邮件大小），需输入 `y` 确认
- 加 `-y` 可跳过确认直接发送（CI/脚本调用时使用）
- 测试邮件内容和群发完全一致，区别只是只发给你一个人

### Step 3：群发邮件

确认测试邮件效果OK后，执行群发：

```bash
# ✅ 正确：指定文件，脚本会显示预览确认后发给全部 23 人
python scripts/send_email.py brief/YYYY-MM-DD.html
```

> ⚠️ **不要不传文件直接运行 `python scripts/send_email.py`**，会默认发给全部 23 人且可能选错文件。

### Step 4：同步到公众号

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/raphael-publish
node publish-daily.mjs ../tech-daily-brief/brief/YYYY-MM-DD.html
```

默认配置（已固化，无需传参）：

| 配置项 | 值 |
|--------|-----|
| 标题 | `科技资讯日报｜MM月DD日` |
| 封面 | `~/Desktop/cover.png` |
| 主题 | `nyt`（纽约时报风格） |
| 页脚品牌 | `Tech Daily Brief` |

---

## 五、发布前检查清单

```
□ 已读取 config/search_keywords.yaml，搜索使用了配置中的关键词（未自行编造）
□ 已读取 template.html 模板，HTML 基于模板生成（填充占位符）
□ X/Twitter 已通过 twitter-cli 采集（🚫 硬性阻断点：未完成则整期作废，绝对禁止跳过）
□ 微博已通过 weibo-cli 采集（L0.5：配置文件中博主的最新微博）
□ 重点话题已通过 XClaw 扫描/手动搜索 X 讨论（用于洞察观点支撑）
□ 时效性：全部新闻在 48h 内，主体在 24h 内
□ 信源：官方一手源 ≥ 5 条（海外用英文官方源，国内用中文官方源）
□ 信源：禁止用二手转载（新浪/搜狐/腾讯科技）作为主要信源
□ 信源：同一二手源整期引用 ≤ 2 次
□ 深度：至少 3-5 篇全文抓取 + XClaw 观点搜索，洞察基于全文+权威观点（禁止仅凭搜索摘要）
□ 数量：每板块 ≥ 5 条新闻
□ 输出：文件保存到 brief/YYYY-MM-DD.html
```

---

## 六、快捷工具

### 一键发布（推荐）

> ⚠️ 一键发布内部会自动检测最新日报，但建议手动指定文件避免误选

```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief

# 完整发布流程（按顺序）：GitHub push → 测试邮件 → 群发邮件 → 公众号
python scripts/publish_all.py brief/YYYY-MM-DD.html

# 只发测试邮件（验证效果）✅ 推荐先跑这个
python scripts/publish_all.py brief/YYYY-MM-DD.html --test-email alexisyang@tencent.com

# 测试OK后单独群发（跳过公众号先用 --skip-wechat）
python scripts/publish_all.py brief/YYYY-MM-DD.html --skip-wechat

# 跳过某些步骤
python scripts/publish_all.py brief/YYYY-MM-DD.html --skip-github   # 跳过 GitHub
python scripts/publish_all.py brief/YYYY-MM-DD.html --skip-email    # 跳过邮件
python scripts/publish_all.py brief/YYYY-MM-DD.html --skip-wechat   # 跳过公众号
```

### 社交媒体 CLI 工具

```bash
# Twitter / Weibo 统一入口（自动设置 PATH）
python scripts/social_cli.py twitter feed -t following -n 100 --json
python scripts/social_cli.py twitter search "OpenAI" --json -o results.json
python scripts/social_cli.py weibo search "AI" -n 50

# 或直接调用（需先 export PATH）
export PATH="/Users/yangliu/.local/bin:$PATH"
twitter feed -t following -n 100 --json
weibo ...
```

### 邮件发送

> ⚠️ **默认发给全部 23 人，测试必须加 `--to alexisyang@tencent.com`**

```bash
# 发送给全部收件人（23人）- 会显示预览确认
python scripts/send_email.py brief/YYYY-MM-DD.html

# 发送给指定邮箱（测试用）✅
python scripts/send_email.py brief/YYYY-MM-DD.html --to alexisyang@tencent.com

# 跳过确认直接发送（CI/脚本调用）
python scripts/send_email.py brief/YYYY-MM-DD.html -y

# 发送给新增的收件人（15人）
python scripts/send_email.py brief/YYYY-MM-DD.html --new-only
```

---

## 七、项目结构

```
tech-daily-brief/
├── README.md                  ← 本文件（AI 执行入口）
├── template.html              ← 日报 HTML 模板（占位符 + CSS + 结构骨架）
├── index.html                 ← 日报存档首页（自动更新 BRIEFS 数组）
├── brief/                     # 日报 HTML 输出
│   ├── YYYY-MM-DD.html        # 网页版
│   ├── YYYY-MM-DD-wechat.html # 公众号版（自动生成）
│   └── YYYY-MM-DD.md          # Markdown 版（自动生成）
├── config/
│   ├── config.yaml            # 邮件/微信/板块配置
│   ├── search_keywords.yaml   # 搜索关键词（按板块分类）
│   ├── weibo_users.yaml       # 微博采集用户列表
│   └── gaming_sources.yaml    # 游戏行业信源配置
├── docs/
│   ├── lessons_learned.md     # 踩坑记录
│   ├── quality_rules.md       # 红线详细说明与示例
│   ├── email_guide.md         # 邮件推送指南
│   ├── wechat_guide.md        # 微信公众号推送指南
│   └── agent-sop.md           # AI 执行 SOP
├── scripts/
│   ├── publish_all.py         # ⭐ 一键发布脚本（GitHub+邮件+公众号）
│   ├── send_email.py          # 邮件发送脚本（支持灵活选择收件人）
│   ├── social_cli.py          # Twitter/Weibo 统一调用入口
│   ├── weibo_fetch.py         # 微博采集脚本
│   ├── bw_twitter.py          # BrowserWing Twitter 采集
│   ├── filter_tweets.py       # 推文过滤筛选
│   └── generate_brief.py      # 日报生成辅助
└── 关联项目
    └── ../raphael-publish/     # 公众号排版引擎
```
