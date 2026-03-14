# Tech Daily Brief — 科技资讯日报

> **⚠️ AI 执行入口：生成日报前必须读完本文件，并按顺序执行。**

> 🚫 **全局规则：L0 X/Twitter 采集是硬性阻断点。BrowserWing 启动失败或 Cookie 过期 → 必须立刻停止，告知用户，等待修复。绝对禁止跳过 L0 直接执行 L1 或后续步骤。违反此规则 = 整期日报作废。**

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
| **L0 X/Twitter** | BrowserWing 浏览 Following 时间线 | 持续滚动 | 🚫 **最先执行，失败必须停止整个流程，禁止跳到 L1** |
| **L1 聚合扫描** | Tavily + web_search + web_fetch | 5-7 轮 | 按板块逐个搜索 `search_keywords.yaml` 中的关键词，详见下方 |
| **L2 官方校验** | Jina Reader / tavily_extract | 0-2 轮 | 仅多源矛盾时触发，日常跳过 |
| **L3 深度抓取** | Jina Reader ×1-2 抓全文 | 2-3 轮 | **不可省略**，每期至少 3-5 篇全文 |

产出 30-50 条 → 筛选至 18-22 条。

### L0 X/Twitter 采集（🚫 硬性阻断点 — 失败必须停止，禁止继续）

> 🚫🚫🚫 **绝对禁止跳过 L0。BrowserWing 启动失败、Cookie 过期、任何错误 → 必须立即停止整个日报流程，告知用户，等用户确认修复后才能继续。绝对不允许"先跳过 L0 继续 L1"。如果你跳过了 L0，整期日报作废。**

#### Step 1：确认 BrowserWing 在运行

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/v1/mcp/message
```

- 返回 `200` 或 `405` → ✅ 正常，继续 Step 2
- **连接拒绝（Connection refused）** → BrowserWing 未启动，执行以下命令启动：

```bash
cd ~/.browserwing && nohup ./browserwing > browserwing.stdout.log 2> browserwing.stderr.log &
sleep 3
# 再次探活确认
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/v1/mcp/message
```

**🚫 如果启动仍然失败 → 立即执行以下操作，不做任何其他事情：**
1. 读取错误日志：`cat ~/.browserwing/browserwing.stderr.log | tail -20`
2. 将错误信息完整展示给用户
3. 告知用户：「BrowserWing 启动失败，无法采集 X/Twitter。请先解决此问题，我会等待。」
4. **停止。不继续 L1。不继续任何后续步骤。等待用户回复。**

#### Step 2：初始化 MCP 会话

```bash
curl -s -i -X POST http://localhost:8080/api/v1/mcp/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"daily","version":"1.0"}}}'
```

从响应头中提取 `Mcp-Session-Id`（如 `mcp-session-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`），后续所有请求都要带上。

#### Step 3：导航到 X Following 时间线

```bash
curl -s -X POST http://localhost:8080/api/v1/mcp/message \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"browser_navigate","arguments":{"url":"https://x.com/home"}}}'
```

**检查返回内容**：
- 包含 "Following"、"For you"、推文内容 → ✅ 登录正常，继续 Step 4
- 包含 "Sign in"、"Log in"、"Create account" → ❌ **Cookie 缺失或过期**

**🚫 Cookie 过期 → 立即执行以下操作，不做任何其他事情：**
1. 告知用户：「X/Twitter 的 Cookie 已过期，请访问 http://localhost:8080/cookies 导入最新的 X Cookie」
2. **停止。不继续 L1。不继续任何后续步骤。等待用户回复确认 Cookie 已导入。**
3. 用户确认后 → 重新执行 Step 3

#### Step 4：截取页面内容

```bash
curl -s -X POST http://localhost:8080/api/v1/mcp/message \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"browser_snapshot","arguments":{}}}'
```

从返回的页面文本中识别 AI/科技相关推文。

**必须遍历 24 小时内的全部内容**，Following 时间线就是你的 KOL 信息流，不需要逐个搜索特定账号。

滚动策略：**不是固定滚动 2-3 次**，而是持续滚动直到看到超过 24 小时前的推文为止。

```bash
# 滚动加载更多内容
curl -s -X POST http://localhost:8080/api/v1/mcp/message \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"browser_evaluate","arguments":{"expression":"window.scrollBy(0, 2000)"}}}'
# 等待 2-3 秒后 snapshot，提取新加载的推文
```

**循环流程**：
1. snapshot → 提取推文 → 记录每条推文的发布时间
2. 如果最旧的一条推文仍在 24 小时内 → 继续滚动 + snapshot
3. 如果看到了超过 24 小时前的推文 → 停止滚动，24h 内容已全部覆盖
4. 每次 snapshot 后去重（按推文 ID），避免重复记录

**终止条件**：看到发布时间超过 24 小时前的推文（如 "Yesterday" 或具体日期）。

#### 提取格式

每条推文提取以下字段：

| 字段 | 说明 |
|------|------|
| **发布者** | 用户名（如 @sama） |
| **内容摘要** | 推文核心内容中文总结 |
| **原文链接** | `https://x.com/用户名/status/推文ID` |
| **发布时间** | 精确到小时 |

#### 故障排查

| 问题 | 解决方案 |
|------|----------|
| BrowserWing 未启动（Connection refused） | `cd ~/.browserwing && nohup ./browserwing > browserwing.stdout.log 2> browserwing.stderr.log &` |
| 数据库初始化失败 | `rm ~/.browserwing/data/browserwing.db` 后重启 |
| Chrome 连接断开（closed network connection） | 重启 BrowserWing：先 `pkill -f browserwing`（不杀 Chrome Helper），再启动 |
| Cookie 过期 | 告知用户到 `http://localhost:8080/cookies` 重新导入 |
| X 页面加载超时 | 重试一次；仍失败则检查网络环境 |
| snapshot 返回空内容 | 等待 3 秒后重试；检查页面是否加载完成 |

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
| Tavily（`tavily_search`） | 英文关键词，分 2-3 批搜索 | 2-3 轮 |
| web_search | 补充搜索，或搜 Tavily 覆盖不到的关键词 | 1-2 轮 |
| web_fetch（聚合站） | 扫一遍 36氪/虎嗅 等中文聚合站热榜 | 1 轮 |

**注意**：关键词允许跨板块重复（如 Google 同时出现在 AI、手机、科技），搜到的同一条新闻可能匹配多个板块——选最相关的板块放入即可，不要重复。

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
python scripts/send_email.py
```

- 自动检测 `brief/` 下最新的日报 HTML，自动提取日期生成邮件标题
- 也可指定文件：`python scripts/send_email.py brief/2026-03-13.html`
- 收件人：alexisyang@tencent.com 等
- 通过 QQ 邮箱 SMTP（smtp.qq.com:465 SSL），授权码在 macOS 钥匙串（service: qq-smtp-auth）
- CSS 通过 premailer 内联（邮件客户端会剥离 `<style>` 标签）

### Step 3：同步到公众号

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
□ X/Twitter 已通过 BrowserWing 采集（🚫 硬性阻断点：未完成则整期作废，绝对禁止跳过）
□ 时效性：全部新闻在 48h 内，主体在 24h 内
□ 信源：官方一手源 ≥ 5 条（海外用英文官方源，国内用中文官方源）
□ 信源：禁止用二手转载（新浪/搜狐/腾讯科技）作为主要信源
□ 信源：同一二手源整期引用 ≤ 2 次
□ 深度：至少 3-5 篇全文抓取，洞察基于全文撰写（禁止仅凭搜索摘要）
□ 数量：每板块 ≥ 5 条新闻
□ 输出：文件保存到 brief/YYYY-MM-DD.html
```

---

## 六、项目结构

```
tech-daily-brief/
├── README.md                  ← 本文件（AI 执行入口）
├── template.html              ← 日报 HTML 模板（占位符 + CSS + 结构骨架）
├── brief/                     # 日报 HTML 输出
├── config/
│   ├── config.yaml            # 邮件/微信/板块配置
│   ├── search_keywords.yaml   # 搜索关键词（按板块分类）
├── docs/
│   ├── lessons_learned.md     # 踩坑记录
│   ├── quality_rules.md       # 红线详细说明与示例
│   ├── email_guide.md         # 邮件推送指南
│   └── wechat_guide.md        # 微信公众号推送指南
├── scripts/
│   └── send_email.py          # 邮件发送脚本（自动检测最新日报）
└── 关联项目
    └── ../raphael-publish/     # 公众号排版引擎
```
