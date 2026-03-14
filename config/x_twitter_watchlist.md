# X/Twitter 监控账号与关键词

> 采集阶段第 1 级必须通过 BrowserWing 在 X 上搜索以下账号和关键词。

## 必搜 KOL 账号

### P1 核心人物（每次必查）
| 账号 | 身份 | 关注方向 |
|------|------|----------|
| @sama | Sam Altman · OpenAI CEO | OpenAI 动态、AGI 路线 |
| @elonmusk | Elon Musk · xAI/Tesla | xAI Grok、AI 政策 |
| @demaborin | Demis Hassabis · Google DeepMind CEO | Gemini、DeepMind 研究 |
| @ylecun | Yann LeCun · Meta 首席 AI 科学家 | 世界模型、AI 争论 |
| @kaborparthy | Andrej Karpathy | AI 教育、开源项目 |
| @DrJimFan | Jim Fan · NVIDIA 高级研究科学家 | 具身智能、Foundation Agent |
| @daborei | Dario Amodei · Anthropic CEO | AI 安全、Claude |
| @aaborei | Daniela Amodei · Anthropic 总裁 | Anthropic 商业 |
| @hardmaru | David Ha · Sakana AI CEO | 进化 AI、日本 AI 生态 |
| @jasonwei20 | Jason Wei · OpenAI 研究员 | 思维链、scaling law |

### P2 重要人物（按板块选查）
| 账号 | 身份 | 关注方向 |
|------|------|----------|
| @EMostaque | Emad Mostaque · Stability AI | 开源图像生成 |
| @ClementDelangue | Clément Delangue · Hugging Face CEO | 开源 AI 生态 |
| @arthurmensch | Arthur Mensch · Mistral CEO | 欧洲 AI、开源模型 |
| @swaborx | Swyx · Latent Space 主持人 | AI 工程、趋势分析 |
| @jeaborff | Jeff Dean · Google | 大规模系统、AI 基础设施 |
| @satyanadella | Satya Nadella · Microsoft CEO | Azure AI、Copilot |
| @timaborok | Tim Cook · Apple CEO | Apple AI、硬件 |
| @linyiofficial | 林亦 · MiniMax | 中国 AI、多模态 |
| @zhangpeng | 张鹏 · 智谱 AI CEO | GLM、中国大模型 |

### P3 游戏行业
| 账号 | 身份 | 关注方向 |
|------|------|----------|
| @gaaborort | Jason Schreier · Bloomberg 游戏记者 | 游戏行业内幕 |
| @geoffkeighley | Geoff Keighley · TGA 主持人 | 游戏颁奖、行业动态 |
| @nibaborllion | Nibel · 游戏新闻速报 | 游戏快讯 |
| @IGN | IGN | 游戏评测、发布会 |
| @GameSpot | GameSpot | 游戏评测 |

## 搜索关键词

所有渠道（含 X/Twitter）共用统一关键词配置，见 `config/search_keywords.yaml`。

## BrowserWing 搜索执行方式

```bash
# 1. 初始化 BrowserWing MCP 会话
curl -s -X POST http://localhost:8080/api/v1/mcp/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"x-search","version":"1.0"}}}'

# 2. 导航到 X 搜索页
curl -s -X POST http://localhost:8080/api/v1/mcp/message \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"browser_navigate","arguments":{"url":"https://x.com/search?q=AI%20news%20today&f=live"}}}'

# 3. 读取页面内容
curl -s -X POST http://localhost:8080/api/v1/mcp/message \
  -H "Content-Type: application/json" \
  -H "Mcp-Session-Id: SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"browser_snapshot","arguments":{}}}'

# 4. 搜索指定账号最新推文
# URL: https://x.com/search?q=from%3Asama&f=live
# URL: https://x.com/search?q=from%3Akarpathy&f=live
```

## 注意事项
- BrowserWing 运行在 `http://localhost:8080`
- 需要预先在 `http://localhost:8080/cookies` 导入 X/Twitter 的登录 Cookie
- 搜索结果用于补充和交叉验证其他渠道的新闻
- 关注 KOL 的原创推文（非转发），特别是产品发布、技术观点、行业评论
