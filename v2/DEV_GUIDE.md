# Tech Daily Brief v2 — 极其详细的开发指南

> **⚠️ 本文档是给 AI 模型看的开发手册。如果你是一个 AI（Claude/GPT/Gemini/任何模型），你正在接手这个项目的开发工作，请逐字阅读本文档。**
>
> **本文档的每一条规则都有存在的原因。请勿跳过、简化、或"优化"任何步骤。**

---

## 0. 绝对不可违反的硬性规则

在开始任何开发之前，先背诵这 5 条：

### 🚫 规则 1：L0 X/Twitter 是硬性阻断点
- `collector.py` 中，X/Twitter Following 时间线的采集 **必须** 是第一步
- 如果 `twitter feed -t following` 失败（Cookie 过期、超时、任何错误）→ **整个采集流程立即终止**
- **绝对禁止**跳过 L0 继续执行 L1 或后续步骤
- 如果 L0 失败，打印错误信息并 `sys.exit(1)`，告知用户修复 Cookie
- 这条规则**不可讨论、不可变通、不可绕过**

### 🚫 规则 2：不动原系统
- `v2/` 目录之外的文件 **绝对不能修改**
- 原来的 `scripts/`、`config/`、`template.html`、`brief/`、`README.md` → 不动
- `v2/` 可以 **读取** 原系统的配置文件（如 `config/search_keywords.yaml`），但 **不能写入**
- 如果需要新的配置，放在 `v2/config/` 里

### 🚫 规则 3：信源置信度跟着内容走，不跟着人走
- `trust_default`（采集时自动标）跟作者身份走 → 这是粗判
- `trust_final`（写日报时精判）跟内容性质走 → 这才是最终值
- 同一个 @数码闲聊站，发独家爆料 = L1，转发新闻 = L3
- **日报中的信源链接必须指向最上游的一手 URL**，不是转载链接

### 🚫 规则 4：所有采集数据都入库
- 不只是日报精选的 18-22 条，**全量数据都要存为 Atom**
- 一天采集了 200 条 → 200 条全部写入 `archive/daily/YYYY-MM-DD.jsonl`
- 其中 18-22 条标记 `in_daily_brief: true`，其余 `false`
- 周/月复盘依赖全量数据，不是精选数据

### 🚫 规则 5：先测试，再提交
- 每个脚本写完后，**必须**运行一次 `python3 v2/scripts/XXX.py --help` 确认不报错
- 修改 `atom_store.py` 后，**必须**运行 `python3 v2/tests/test_atom_store.py` 
- 不允许提交明知有语法错误的代码

---

## 1. 项目全景图

```
tech-daily-brief/              ← 项目根目录
├── README.md                  ← 原系统 AI 入口（不动）
├── template.html              ← 日报 HTML 模板（不动）
├── brief/                     ← 日报输出（不动）
├── config/                    ← 原配置文件（只读）
│   ├── config.yaml            ← 邮件/微信/板块配置
│   ├── search_keywords.yaml   ← 搜索关键词
│   ├── weibo_users.yaml       ← 微博博主
│   └── x_twitter_watchlist.md ← X KOL 列表
├── scripts/                   ← 原脚本（不动）
│
└── v2/                        ← 🆕 v2 系统（你的工作区）
    ├── README.md              ← v2 入口文档
    ├── DEV_GUIDE.md           ← 本文档
    ├── config/
    │   └── atom_schema.json   ← Atom 数据结构定义（已完成 ✅）
    ├── scripts/
    │   ├── atom_store.py      ← 存储引擎（已完成 ✅ 框架）
    │   ├── collector.py       ← 采集入口（已完成 ✅ 框架）
    │   ├── obsidian_sync.py   ← Obsidian 同步（已完成 ✅ 框架）
    │   ├── weekly_report.py   ← 周报生成（已完成 ✅ 框架）
    │   ├── monthly_report.py  ← 月报生成（已完成 ✅ 框架）
    │   └── trust_judge.py     ← 置信度精判（❌ 待实现）
    ├── archive/               ← 数据目录
    │   ├── daily/             ← JSONL（自动创建）
    │   ├── index/             ← 反向索引（自动创建）
    │   └── reports/
    │       ├── weekly/
    │       └── monthly/
    └── tests/
        └── test_atom_store.py ← 测试（❌ 待实现）
```

---

## 2. 当前状态：已完成 vs 待实现

### ✅ 已完成

| 文件 | 状态 | 说明 |
|------|------|------|
| `v2/config/atom_schema.json` | ✅ 完成 | Atom 数据结构的 JSON Schema 定义 |
| `v2/scripts/atom_store.py` | ✅ 完成 | 存储引擎：JSONL 读写 + 索引 + 查询 + 统计 + 关联发现 |
| `v2/scripts/collector.py` | ✅ 完成 | 采集入口：X/微博/RSS/Web 适配器全部实现 |
| `v2/scripts/obsidian_sync.py` | ✅ 完成 | Obsidian 同步：Daily/Entities/Topics 笔记生成 |
| `v2/scripts/weekly_report.py` | ✅ 完成 | 周报：entity/tag 频率统计 + 每日数据量 |
| `v2/scripts/monthly_report.py` | ✅ 完成 | 月报：趋势信号 + 跨天关联 + 环比 |
| `v2/scripts/trust_judge.py` | ✅ 完成 | 置信度精判：信号词检测 + content_type 判断 |
| `v2/tests/test_atom_store.py` | ✅ 完成 | 13 项测试全部通过 |
| **RuleBasedAnnotator** | ✅ 完成 | 规则标注器：category/tags/entities 自动判断 |
| **RSSAdapter** | ✅ 完成 | RSS 采集适配器：feedparser + 自动标注 |
| **WebAdapter** | ✅ 完成 | Web 采集适配器：Jina Reader + 网页抓取 |

### ❌ 待实现

按优先级排序：

| 优先级 | 任务 | 文件 | 难度 | 说明 |
|--------|------|------|------|------|
| **P0** | ~~AI 辅助标注~~ | ✅ 已完成 | | RuleBasedAnnotator 已实现 |
| **P1** | ~~测试脚本~~ | ✅ 已完成 | | 13 项测试全部通过 |
| **P2** | ~~RSS 适配器~~ | ✅ 已完成 | | feedparser + 自动标注已实现 |
| **P3** | ~~Web 适配器~~ | ✅ 已完成 | | Jina Reader + 网页抓取已实现 |
| **P4** | ~~trust_judge.py~~ | ✅ 已完成 | | 置信度精判器已实现 |
| **P5** | 与原日报系统集成 | 需规划 | ⭐⭐⭐ | 让原系统读取 v2 的 Atoms 生成日报 |

---

## 3. 逐任务开发步骤

### 任务 P0：collector.py 中 AI 辅助标注

**目标**：采集到的原始数据（推文/微博）自动打上 `category`、`tags`、`entities`、`content_type`。

**当前问题**：
- `XTwitterAdapter.tweet_to_atom()` 中，`category`、`tags`、`entities` 都是空的
- `content_type` 只有简单规则匹配，不够准确
- 这导致存入的 Atom 缺少关键元数据，后续检索和统计都不准

**实现方案（二选一）**：

#### 方案 A：规则引擎（推荐先做这个）

在 `collector.py` 中添加一个 `RuleBasedAnnotator` 类：

```python
class RuleBasedAnnotator:
    """基于规则的标注器——不需要 AI，纯关键词匹配"""
    
    # 板块关键词（从 search_keywords.yaml 提取）
    CATEGORY_KEYWORDS = {
        "ai_models": ["openai", "chatgpt", "gpt", "claude", "anthropic", "gemini", 
                       "deepmind", "llm", "大模型", "deepseek", "kimi", "ai model",
                       "mistral", "llama", "meta ai", "copilot", "grok", "midjourney"],
        "mobile": ["iphone", "samsung", "pixel", "android", "ios", "华为", "小米",
                   "oppo", "vivo", "荣耀", "折叠屏", "ar眼镜", "vision pro"],
        "chips": ["nvidia", "amd", "tsmc", "台积电", "gpu", "芯片", "chip",
                  "h200", "b200", "blackwell", "昇腾", "寒武纪", "算力"],
        "gaming": ["playstation", "xbox", "nintendo", "switch", "steam", "epic",
                   "游戏", "gta", "game", "gaming", "原神", "王者荣耀"],
        "tech_industry": ["融资", "acquisition", "ipo", "裁员", "layoff",
                          "revenue", "earnings", "market cap"],
        "policy": ["regulation", "监管", "policy", "ban", "制裁", "sanctions",
                   "antitrust", "反垄断", "隐私", "privacy"],
    }
    
    # 实体提取规则（公司/产品名 → 标准名）
    ENTITY_MAP = {
        "openai": "OpenAI", "chatgpt": "ChatGPT", "gpt-5": "GPT-5",
        "gpt-4": "GPT-4", "gpt-4o": "GPT-4o", "gpt5": "GPT-5",
        "anthropic": "Anthropic", "claude": "Claude",
        "google": "Google", "deepmind": "DeepMind", "gemini": "Gemini",
        "nvidia": "NVIDIA", "jensen huang": "Jensen Huang",
        "apple": "Apple", "iphone": "iPhone", "meta": "Meta",
        "samsung": "Samsung", "tsmc": "TSMC", "amd": "AMD",
        "microsoft": "Microsoft", "copilot": "Copilot",
        "tesla": "Tesla", "elon musk": "Elon Musk",
        "deepseek": "DeepSeek", "huawei": "Huawei", "华为": "Huawei",
        # ... 继续扩充
    }
    
    def annotate(self, text: str, author: str) -> dict:
        """
        返回 {"category": str, "tags": list, "entities": list}
        """
        text_lower = text.lower()
        
        # 1. 板块分类：匹配关键词最多的板块
        cat_scores = {}
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                cat_scores[cat] = score
        category = max(cat_scores, key=cat_scores.get) if cat_scores else "other"
        
        # 2. 实体提取：从文本中匹配已知实体
        entities = []
        for keyword, entity_name in self.ENTITY_MAP.items():
            if keyword in text_lower and entity_name not in entities:
                entities.append(entity_name)
        
        # 3. 标签：实体名的小写 + 板块名
        tags = [e.lower().replace(" ", "_") for e in entities]
        tags.append(category)
        tags = list(set(tags))
        
        return {"category": category, "tags": tags, "entities": entities}
```

**步骤**：
1. 在 `collector.py` 顶部添加 `RuleBasedAnnotator` 类
2. 在 `XTwitterAdapter.tweet_to_atom()` 中调用：
   ```python
   annotator = RuleBasedAnnotator()
   result = annotator.annotate(text, screen_name)
   # 然后用 result["category"], result["tags"], result["entities"]
   ```
3. 同样在 `WeiboAdapter.weibo_to_atom()` 中调用
4. 测试：`python3 collector.py --source x --dry-run`

#### 方案 B：AI 辅助（方案 A 跑通后再做）

创建一个 `ai_annotator.py` 脚本，读取当日 JSONL，用 LLM 批量标注。这需要：
- DeepSeek API 或 OpenAI API
- 每 20-30 条打包一次，减少 API 调用
- 输出覆盖原 JSONL 中的 category/tags/entities

这个后续再做，先用方案 A。

---

### 任务 P1：测试脚本

**文件**：`v2/tests/test_atom_store.py`

**步骤**：
1. 创建文件 `v2/tests/test_atom_store.py`
2. 编写以下测试用例：

```python
#!/usr/bin/env python3
"""atom_store 基本功能测试"""

import sys, json, tempfile, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from atom_store import AtomStore, create_atom

def test_all():
    # 用临时目录作为存储
    tmp = Path(tempfile.mkdtemp())
    try:
        store = AtomStore(base_dir=tmp)
        
        # 测试 1：创建 Atom
        atom = create_atom(
            title="OpenAI releases GPT-5.4",
            summary_zh="OpenAI 发布 GPT-5.4 轻量级模型",
            platform="x", author="@OpenAI", author_type="official",
            url="https://x.com/OpenAI/status/123", content_type="official",
            category="ai_models", tags=["openai", "gpt", "llm"],
            entities=["OpenAI", "GPT-5.4"], date="2026-03-18"
        )
        assert atom["trust_default"] == "L1", "official → L1"
        assert atom["id"] is None, "ID should be None before save"
        print("✅ 测试 1: create_atom 通过")
        
        # 测试 2：保存
        atom_id = store.save_atom(atom)
        assert atom_id == "atom_20260318_001"
        print("✅ 测试 2: save_atom 通过")
        
        # 测试 3：查询
        atoms = store.query_by_date("2026-03-18")
        assert len(atoms) == 1
        assert atoms[0]["title"] == "OpenAI releases GPT-5.4"
        print("✅ 测试 3: query_by_date 通过")
        
        # 测试 4：entity 索引查询
        results = store.query_by_entity("OpenAI")
        assert len(results) == 1
        print("✅ 测试 4: query_by_entity 通过")
        
        # 测试 5：tag 索引查询
        results = store.query_by_tag("gpt")
        assert len(results) == 1
        print("✅ 测试 5: query_by_tag 通过")
        
        # 测试 6：ID 精确查询
        result = store.query_by_id("atom_20260318_001")
        assert result is not None
        assert result["source"]["author"] == "@OpenAI"
        print("✅ 测试 6: query_by_id 通过")
        
        # 测试 7：更新
        ok = store.update_atom("atom_20260318_001", {
            "trust_final": "L1",
            "trust_reason": "官方公告",
            "in_daily_brief": True
        })
        assert ok
        updated = store.query_by_id("atom_20260318_001")
        assert updated["trust_final"] == "L1"
        assert updated["in_daily_brief"] == True
        print("✅ 测试 7: update_atom 通过")
        
        # 测试 8：批量保存
        atoms_batch = [
            create_atom(
                title=f"Test news {i}", summary_zh=f"测试新闻 {i}",
                platform="rss", author="TechCrunch", author_type="media",
                url=f"https://tc.com/{i}", content_type="report",
                category="ai_models", tags=["test"], entities=["TestCo"],
                date="2026-03-18"
            ) for i in range(5)
        ]
        ids = store.save_atoms_batch(atoms_batch)
        assert len(ids) == 5
        all_atoms = store.query_by_date("2026-03-18")
        assert len(all_atoms) == 6  # 1 + 5
        print("✅ 测试 8: save_atoms_batch 通过")
        
        # 测试 9：统计
        stats = store.get_daily_stats("2026-03-18")
        assert stats["total"] == 6
        assert stats["selected_for_brief"] == 1
        print("✅ 测试 9: get_daily_stats 通过")
        
        # 测试 10：日期范围查询
        atom2 = create_atom(
            title="Day 2 news", summary_zh="第二天新闻",
            platform="x", author="@test", author_type="kol",
            url="https://x.com/test/1", content_type="commentary",
            category="mobile", tags=["test"], entities=["TestCo"],
            date="2026-03-19"
        )
        store.save_atom(atom2)
        range_atoms = store.query_by_date_range("2026-03-18", "2026-03-19")
        assert len(range_atoms) == 7  # 6 + 1
        print("✅ 测试 10: query_by_date_range 通过")
        
        # 测试 11：entity 频率统计
        freq = store.get_entity_frequency("2026-03-18", "2026-03-19")
        tc_count = dict(freq).get("TestCo", 0)
        assert tc_count == 6  # 5 batch + 1 day2
        print("✅ 测试 11: get_entity_frequency 通过")
        
        # 测试 12：关联发现
        related = store.find_related_atoms("atom_20260318_001")
        assert len(related) > 0  # 应该能找到共享 entity 的其他 atoms
        print("✅ 测试 12: find_related_atoms 通过")
        
        # 测试 13：trust_default 自动判定
        a1 = create_atom(title="t", summary_zh="s", platform="x", author="@x", 
                         author_type="official", url="u", content_type="official",
                         category="other", tags=[], entities=[])
        assert a1["trust_default"] == "L1"
        
        a2 = create_atom(title="t", summary_zh="s", platform="x", author="@x",
                         author_type="media", url="u", content_type="report",
                         category="other", tags=[], entities=[])
        assert a2["trust_default"] == "L2"
        
        a3 = create_atom(title="t", summary_zh="s", platform="x", author="@x",
                         author_type="blogger", url="u", content_type="repost",
                         category="other", tags=[], entities=[])
        assert a3["trust_default"] == "L3"
        print("✅ 测试 13: trust_default 自动判定通过")
        
        print("\n🎉 全部 13 项测试通过！")
        
    finally:
        shutil.rmtree(tmp)

if __name__ == "__main__":
    test_all()
```

3. 运行测试：
```bash
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief
python3 v2/tests/test_atom_store.py
```

4. **所有 13 项测试必须通过才能继续**

---

### 任务 P2：RSS 适配器

**文件**：`collector.py` 中的 `RSSAdapter` 类

**步骤**：

1. 安装 feedparser：`pip3 install feedparser`
2. 在 `RSSAdapter.fetch_feed()` 中实现：

```python
def fetch_feed(self, url: str) -> List[Dict]:
    import feedparser
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:20]:  # 每个 feed 最多 20 条
            items.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "summary": entry.get("summary", "")[:500],
                "published": entry.get("published", ""),
                "source": url,
            })
        return items
    except Exception as e:
        print(f"  ⚠️ RSS 抓取失败 {url}: {e}")
        return []
```

3. 在 `rss_item_to_atom()` 中实现 RSS item → Atom 转化
4. 在 `CollectorOrchestrator.run_full_collection()` 的 L1 阶段调用 RSS 抓取
5. RSS 源列表从 `config/sources.json` 读取（只读，不要修改原文件）

---

### 任务 P3：Web 适配器

**文件**：`collector.py` 中的 `WebAdapter` 类

**步骤**：

1. 在 `WebAdapter.fetch_url()` 中实现：
```python
def fetch_url(self, url: str) -> Optional[str]:
    """用 Jina Reader 抓取网页"""
    import subprocess
    try:
        result = subprocess.run(
            ["curl", "-s", f"https://r.jina.ai/{url}"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and len(result.stdout) > 100:
            return result.stdout
    except Exception as e:
        print(f"  ⚠️ Jina Reader 失败: {e}")
    return None
```

2. 实现 `web_item_to_atom()`：解析抓取的 Markdown 内容，提取标题/摘要

---

### 任务 P4：trust_judge.py（置信度精判）

**文件**：`v2/scripts/trust_judge.py`

**目的**：在写日报时，对每条候选新闻精判 `trust_final`。

**核心逻辑**：

```
输入：一条 Atom（包含 text/author/url/content_type 等）
输出：trust_final (L1/L2/L3) + trust_reason (判断依据)

判断规则：
1. content_type == "official" → L1（官方公告就是一手源）
2. content_type == "exclusive" → L1（独家爆料=一手信息）
3. content_type == "firsthand_test" → L1（一手实测=一手信息）
4. content_type == "original_analysis" → L1~L2（看是否有自有数据）
5. content_type == "report" + 作者是权威媒体 → L2
6. content_type == "translation" → L3
7. content_type == "repost" → L3

信号词检测（用于覆盖 content_type 粗判）：
- "exclusive"/"独家"/"据记者获悉"/"本报了解到" → 升为 L1
- "hands-on"/"实测"/"上手" → 升为 L1
- "编译自"/"据XXX报道"/"translated" → 降为 L3
- "RT"/"转发" → 降为 L3

⚠️ 特别注意：
- @数码闲聊站 发独家爆料 = L1（内容决定）
- @数码闲聊站 转发苹果新闻 = L3（内容决定）
- 科创板日报 记者独家采访 = L1（内容决定）
- 科创板日报 翻译路透社报道 = L3（内容决定）
```

**步骤**：
1. 创建 `v2/scripts/trust_judge.py`
2. 实现 `judge_trust(atom) -> (trust_final, trust_reason)`
3. 实现 CLI：`python3 trust_judge.py --date 2026-03-18`（批量精判当日所有 atoms）
4. 精判结果通过 `atom_store.update_atom()` 写回

---

### 任务 P5：与原日报系统集成

**这是最复杂的任务，等 P0-P4 都完成后再做。**

集成方案：
1. 在原系统的日报生成流程中，读取 `v2/archive/daily/YYYY-MM-DD.jsonl` 
2. 从中筛选 18-22 条进入日报
3. 用 `atom_store.update_atom()` 标记 `in_daily_brief: true`
4. 日报的信源链接用 `source.upstream_url`（如果有）或 `source.url`

---

## 4. Atom 数据格式速查

### 完整示例

```json
{
  "id": "atom_20260318_042",
  "date": "2026-03-18",
  "title": "We're releasing GPT-5.4 mini and nano — smaller, faster models for everyone",
  "title_zh": "我们发布 GPT-5.4 mini 和 nano —— 更小更快的模型",
  "summary_zh": "OpenAI 推出两款轻量级模型 GPT-5.4 mini 和 nano，分别面向移动端和嵌入式场景。mini 在 MMLU 上达到 92.3%（仅需 8B 参数），nano 在端侧推理速度比 GPT-4o-mini 快 3.7 倍。",
  "source": {
    "platform": "x",
    "author": "@OpenAI",
    "author_type": "official",
    "url": "https://x.com/OpenAI/status/1234567890",
    "upstream_url": null,
    "timestamp": "2026-03-18T10:30:00Z"
  },
  "content_type": "official",
  "trust_default": "L1",
  "trust_final": "L1",
  "trust_reason": "OpenAI 官方账号发布的产品公告",
  "category": "ai_models",
  "tags": ["openai", "gpt", "llm", "lightweight", "mobile_ai"],
  "entities": ["OpenAI", "GPT-5.4", "GPT-5.4 mini", "GPT-5.4 nano"],
  "metrics": {
    "likes": 15200,
    "retweets": 4800,
    "replies": 2100,
    "views": 3200000
  },
  "in_daily_brief": true,
  "brief_date": "2026-03-18",
  "related_atoms": ["atom_20260315_012", "atom_20260310_005"],
  "full_text_fetched": true,
  "full_text_path": "archive/fulltext/openai-gpt54-mini.md"
}
```

### 字段必填/选填速查

| 字段 | 必填 | 采集时填 | 日报时填 | 周/月报时填 |
|------|------|----------|----------|-------------|
| id | ✅ | 自动生成 | | |
| date | ✅ | ✅ | | |
| title | ✅ | ✅ | | |
| title_zh | | ✅（AI翻译） | | |
| summary_zh | ✅ | ✅ | | |
| source.* | ✅ | ✅ | | |
| content_type | ✅ | ✅（粗判） | 可修正 | |
| trust_default | ✅ | ✅（自动） | | |
| trust_final | | | ✅ | |
| trust_reason | | | ✅ | |
| category | ✅ | ✅（粗判/AI） | 可修正 | |
| tags | ✅ | ✅（AI提取） | 可补充 | |
| entities | ✅ | ✅（AI提取） | 可补充 | |
| in_daily_brief | | false | ✅ | |
| related_atoms | | [] | | ✅（自动填充） |

---

## 5. 环境与依赖

### Python 路径
```bash
export PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin:/Users/yangliu/.local/bin:$PATH"
```

### 已安装的工具
| 工具 | 路径 | 用途 |
|------|------|------|
| twitter-cli | `~/.local/bin/twitter` | X/Twitter 采集 |
| weibo-cli | `~/.local/bin/weibo` | 微博采集 |
| python3.13 | `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3` | Python |

### 需要安装的 Python 包
```bash
pip3 install pyyaml feedparser
# atom_store.py 只依赖标准库，无需额外安装
```

### 关键路径
| 用途 | 路径 |
|------|------|
| 项目根 | `/Users/yangliu/Documents/Claude Code/codebuddy/tech-daily-brief` |
| v2 根 | `/Users/yangliu/Documents/Claude Code/codebuddy/tech-daily-brief/v2` |
| Obsidian Vault | `~/Documents/Obsidian/资讯` |
| twitter-cli | `~/.local/bin/twitter` |
| weibo-cli | `~/.local/bin/weibo` |

---

## 6. 常见陷阱

### 陷阱 1：忘记 L0 阻断
**错误**：`twitter feed` 返回错误 → 跳过继续搜索
**正确**：立即 `raise RuntimeError` → `sys.exit(1)` → 告知用户

### 陷阱 2：JSONL 追加不加换行
**错误**：`f.write(json.dumps(atom))`
**正确**：`f.write(json.dumps(atom) + "\n")`  ← 注意末尾换行

### 陷阱 3：索引键大小写不一致
**错误**：entity 存 "OpenAI"，查询用 "openai" 找不到
**正确**：索引键统一小写（`entity.lower()`），显示时用原始大小写

### 陷阱 4：Obsidian 文件名特殊字符
**错误**：Entity 名含 `/`、`\`、`:` → 文件创建失败
**正确**：`safe_name = entity.replace("/","-").replace("\\","-").replace(":","-")`

### 陷阱 5：修改原系统文件
**错误**：修改 `scripts/weibo_fetch.py` 来适配 v2
**正确**：在 `v2/scripts/` 里写适配逻辑，调用原脚本但不修改它

### 陷阱 6：YAML 解析需要 pyyaml
**错误**：`import yaml` 但没装 pyyaml → ImportError
**正确**：先 `pip3 install pyyaml`

---

## 7. 验收标准

当以下全部通过时，v2 系统基本可用：

```
□ python3 v2/tests/test_atom_store.py → 全部通过
□ python3 v2/scripts/collector.py --source x --dry-run → 能获取推文并打印 Atoms
□ python3 v2/scripts/collector.py --source x → 数据写入 v2/archive/daily/
□ python3 v2/scripts/obsidian_sync.py --date YYYY-MM-DD → Obsidian 笔记生成
□ python3 v2/scripts/weekly_report.py → 周报生成
□ python3 v2/scripts/monthly_report.py → 月报生成
□ 原系统 python3 scripts/send_email.py → 仍然正常工作（不受影响）
```

---

## 8. 给模型的最后提醒

1. **先读完这整个文档**，不要读一半就开始写代码
2. **先跑测试**（P1），确认 atom_store 没问题
3. **P0 是最重要的**——没有标注就没有数据质量
4. **每改一个文件，立即运行测试确认**
5. **不要碰 v2/ 之外的任何文件**
6. **L0 阻断是铁律**，如果你跳过了，用户会发现，整个日报作废
7. 如果你不确定某个设计决策，**在代码中留 TODO 注释**，不要瞎猜
