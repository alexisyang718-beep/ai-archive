# 🚨 踩坑记录

> 本文档记录项目开发过程中遇到的问题和解决方案，帮助后续 AI 避免重复踩坑。

---

## 一、内容质量相关

### 问题 1：中文搜索命中二手转载源，信息失真

**现象**：
- 使用中文关键词搜索（如 "OpenAI 发布新模型"）容易命中新浪科技、搜狐科技等二手转载
- 同一条新闻被多个二手源转载，看起来像"多条新闻"
- 二手源内容有删减、误译、夸大

**解决方案**：
- **红线 1**：每条新闻至少搜一次英文关键词
- 优先使用 Tavily 英文 query
- 中文搜索仅作补充，用于国内独家新闻

**示例**：
```
❌ tavily_search("OpenAI 发布 GPT-5", search_depth="advanced")
✅ tavily_search("OpenAI GPT-5 release", search_depth="advanced")
   tavily_search("OpenAI GPT-5 发布 国内反应", search_depth="basic")  # 补充
```

---

### 问题 2：过度依赖二手源，日报像"中文科技门户摘要汇编"

**现象**：
- 一期日报引用新浪科技 5 次、腾讯科技 3 次、搜狐科技 2 次
- 整体看起来像把各门户的科技新闻汇总了一下
- 缺乏一手源，信息链条长

**解决方案**：
- **红线 2**：同一二手源整期 ≤ 2 次引用
- 建立信源分级制度（一手源/权威媒体/二手媒体/聚合自媒体）
- 每条新闻必须追溯到最上游一手源

---

### 问题 3：仅凭摘要编写深度洞察，空泛无事实支撑

**现象**：
- 洞察写得像"这将对行业产生深远影响""值得关注""意义重大"
- 没有具体数据、没有原话引用、没有时间线对比
- 原因：只看了 Tavily 返回的 2-3 行 snippet

**解决方案**：
- **红线 3**：深度洞察必须基于全文抓取撰写
- 每期至少用 Jina Reader 抓 3-5 篇高价值文章全文
- 好洞察标准：包含具体数据、CEO 原话、时间线对比

---

### 问题 4：英文一手源偏少，像中文翻译稿合集

**现象**：
- footer 信源列表全是中文域名（sina.com.cn, tencent.com, sohu.com）
- 整体像把英文新闻翻译成中文的合集
- 缺乏国际视野

**解决方案**：
- **红线 4**：英文一手源 ≥ 10、官方源 ≥ 3
- 发布前检查 footer 信源多样性

---

## 二、技术实现相关

### 问题 5：邮件 HTML 显示空白

**现象**：
- 生成的 HTML 在浏览器中显示正常
- 发送到邮箱后显示空白
- 原因：邮件客户端（特别是 QQ 邮箱、Outlook）会剥离 `<style>` 标签

**解决方案**：
- 使用 `premailer` 库将 CSS class 转换为内联 style
- 详见 `docs/email_guide.md`

```python
from premailer import transform
html_with_inline_css = transform(html_content)
```

---

### 问题 6：本地 postfix 发送邮件被拒收

**现象**：
- 用 macOS 自带 postfix 发送邮件
- 腾讯企业邮箱拒收，提示无 SPF/DKIM 认证

**解决方案**：
- 使用 QQ 邮箱 SMTP（smtp.qq.com:465 SSL）
- 授权码存在 macOS 钥匙串

---

### 问题 7：AppleScript 发送大 HTML 失败

**现象**：
- 用 AppleScript 的 `set html content` 发送邮件
- 80KB+ 大 HTML 有 bug，收件端显示空白

**解决方案**：
- 使用 Python smtplib 发送
- 不要依赖 AppleScript

---

### 问题 8：微信公众号排版混乱

**现象**：
- 直接粘贴 HTML 到公众号编辑器，样式丢失
- 公众号不支持 `<style>` 标签、不支持外部 CSS

**解决方案**：
- 使用 Raphael 排版引擎
- 输出 Markdown → 渲染为微信兼容 HTML
- 详见 `../raphael-publish/README-publish.md`

---

## 三、流程相关

### 问题 9：发布顺序混乱

**现象**：
- 先发邮件，用户反馈问题后再改 HTML
- 公众号发布后才发现 GitHub Pages 没推送
- 多渠道版本不一致

**解决方案**：
- **发布三步走**：
  1. 先部署到 GitHub Pages（作为在线版）
  2. 发测试邮件到 alexisyang@tencent.com
  3. 用户确认后再群发 + 同步公众号

---

### 问题 10：忘记搜索 X/Twitter

**现象**：
- X/Twitter 是 AI 圈核心信息源
- 经常忘记搜索 KOL 推文
- 导致错过第一手消息

**解决方案**：
- 在采集流程中明确要求：BrowserWing → X/Twitter ×1 为必选渠道
- 维护 `config/x_twitter_watchlist.md` 监控账号列表

---

## 四、总结：预防措施

| 阶段 | 预防措施 |
|------|----------|
| 搜索时 | 强制英文关键词，避免二手源 |
| 筛选时 | 标记信源级别，控制二手源引用 |
| 撰写洞察时 | 确认已抓取全文再写 |
| 生成完成后 | 核对 footer 信源多样性指标 |
| 发布前 | 按三步走顺序执行，先测试后群发 |
| 邮件发送 | 用 premailer 内联 CSS，用 QQ SMTP |
| 公众号同步 | 用 Raphael 排版引擎 |
