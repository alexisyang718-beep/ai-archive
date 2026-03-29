# V2 系统重构方案

> **作者**: Claude (综合审查方)
> **日期**: 2026-03-19
> **状态**: 待执行
> **目标**: 修复数据质量三大致命缺口 + 可靠性提升 + 架构优化
> **代码审查**: 所有修改完成后，由 Claude 逐条对照本文档审查

---

## 一、系统定位

V2 是部门级信息中枢的**底层数据引擎**。核心价值：
- 信源权威、覆盖面广（X/微博一手信源 + RSS权威源 + 反爬内容）
- 存档质量高（去重、分类、实体提取完善，噪音低）
- 为上层应用提供数据基础（日报选题、周报、专题报告、实时问答）

**本方案不涉及**：日报生成（另起项目）、SQLite 迁移（对当前规模不必要）、AI embedding 语义过滤（规则引擎优化够用）

---

## 二、核心文件清单

修改涉及以下文件（修改前请先通读）：

| 文件 | 路径 | 说明 |
|------|------|------|
| `atom_store.py` | `v2/scripts/atom_store.py` | 存储引擎（643行） |
| `collector.py` | `v2/scripts/collector.py` | 采集入口（~1913行） |
| `atom_schema.json` | `v2/config/atom_schema.json` | Atom Schema 定义 |
| `weibo_users.yaml` | `config/weibo_users.yaml` | 微博采集配置 |

---

## Phase 0：质量闸门（必须全部完成）

### 0.1 存储层 URL 去重

**问题**：`save_atoms_batch()` 没有任何去重机制，实测 42-49% 数据是重复 URL。

**文件**：`v2/scripts/atom_store.py`

**修改位置**：`save_atoms_batch()` 方法（当前第 142-195 行）

**具体要求**：

1. 在 `save_atoms_batch()` 开头，加载当日已有 JSONL 中所有 URL 到一个 `set`
2. 对传入的 `atoms` 列表：
   - 先在 atoms 内部去重（同一批次内可能有重复 URL）
   - 再与已有 URL set 比对
   - 跳过重复的，只写入新的
3. 打印去重统计：`f"去重: {total}条输入, {dupes}条重复, {saved}条新增"`
4. **同时也要修改 `save_atom()` 单条保存方法**（第 87-140 行），加同样的 URL 去重检查

**URL 提取方式**：`atom.get("source", {}).get("url", "")`

**注意**：
- URL 比较时应该**规范化**：去掉尾部的 `/`，去掉 `?utm_*` 等追踪参数
- 空 URL 或无效 URL 不参与去重（直接放行）
- 建议加一个 `_normalize_url(url)` 私有方法

**参考实现**（仅供理解意图，不是要求照搬）：

```python
@staticmethod
def _normalize_url(url: str) -> str:
    """规范化 URL 用于去重比较"""
    if not url:
        return ""
    url = url.rstrip("/")
    # 去掉常见追踪参数
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    # 移除追踪参数
    cleaned = {k: v for k, v in params.items() 
               if not k.startswith("utm_") and k not in ("ref", "source", "from")}
    new_query = urlencode(cleaned, doseq=True)
    return urlunparse(parsed._replace(query=new_query))
```

---

### 0.2 统一 Schema 与代码的分类枚举

**问题**：代码中实际使用了 `ev_auto`、`crypto_web3`、`software_dev`、`internet_tech` 四个分类，但 `atom_schema.json` 中的 `category.enum` 没有这四个值，会导致 Schema 验证失败。

**文件**：`v2/config/atom_schema.json`

**修改位置**：第 111 行的 `category.enum`

**当前值**：
```json
"enum": ["ai_models", "mobile", "chips", "gaming", "tech_industry", "policy", "github", "other"]
```

**改为**：
```json
"enum": ["ai_models", "mobile", "chips", "gaming", "tech_industry", "policy", "github", "software_dev", "internet_tech", "ev_auto", "crypto_web3", "other"]
```

**同时更新** `category` 的 `description` 字段，说明新增板块含义。

---

### 0.3 分类器增强：降 other 到 <15%

**问题**：46% 的数据落入 `other` 分类，原因是短文本（推文 140 字）命中关键词概率低。

**文件**：`v2/scripts/collector.py`

**修改位置**：`RuleBasedAnnotator` 类（第 56-429 行）

**具体要求**：

#### 0.3.1 短文本增强：利用作者信息辅助分类

修改 `annotate()` 方法（第 375 行开始），当 `author` 参数不为空时：

1. 如果 `@screen_name` 或作者名能映射到一个已知分类（比如 `@OpenAI` → `ai_models`，`@数码闲聊站` → `mobile`），给对应分类 +3 分加权
2. 新增一个 `AUTHOR_CATEGORY_HINTS` 字典，定义常见作者→分类的映射

```python
# 作者→分类提示（当纯文本关键词不够时，作者身份可以辅助判断）
AUTHOR_CATEGORY_HINTS = {
    # X 用户
    "@openai": "ai_models",
    "@anthropic": "ai_models",
    "@google": "ai_models",    # Google AI 相关账号
    "@nvidia": "chips",
    "@aaborode": "ai_models",  # AI 研究者
    # 微博用户
    "数码闲聊站": "mobile",
    "机器之心pro": "ai_models",
    "量子位": "ai_models",
    "新智元": "ai_models",
    "36氪": "tech_industry",
    "虎嗅app": "tech_industry",
    "宝玉xp": "ai_models",
    "歸藏的ai工具箱": "ai_models",
    "karminski-牙医": "ai_models",
    "林亦lyi": "ai_models",
    # 可以继续扩展...
}
```

3. 在 `annotate()` 的分类计分逻辑中，如果 author 在 `AUTHOR_CATEGORY_HINTS` 中，给对应分类 +3 额外分

#### 0.3.2 扩充分类关键词

在 `CATEGORY_KEYWORDS` 中补充以下遗漏的关键词：

- `ai_models` 补充：`"vibe coding"`, `"mcp"`, `"a]i编程"` 已有但确认 `"coding agent"`, `"code agent"`, `"devin"` 也应在此（注意：`devin` 当前在 `software_dev` 中，AI coding agent 应该双归属或放在 `ai_models`）
- `chips` 补充：`"ai服务器"`, `"ai server"`, `"液冷"`, `"liquid cooling"`, `"供应链"` (芯片语境), `"ai基础设施"`, `"ai infrastructure"`
- `mobile` 补充：`"手机壳"`, `"保护壳"`, `"屏幕"`, `"display"`, `"刷新率"`, `"续航"`, `"battery life"`
- `gaming` 补充：`"steam deck"`, `"rog ally"`, `"掌机"`, `"handheld"`, `"云游戏"`, `"cloud gaming"`
- `policy` 补充：`"关税"`, `"tariff"`, `"贸易战"`, `"trade war"`, `"国产替代"`, `"信创"`

#### 0.3.3 ai_models vs chips 的重叠消除

**问题**：`ai_models` 关键词中包含 `"ai芯片"`, `"ai chip"`, `"ai accelerator"`，和 `chips` 分类重叠。

**解决**：从 `ai_models` 的 `CATEGORY_KEYWORDS` 中**删除**以下三个词：
```python
"ai芯片", "ai chip", "ai accelerator"
```
这三个本就属于 chips 分类。如果一条新闻同时提到 AI 模型和 AI 芯片，靠其他关键词（如 `"openai"`, `"nvidia"`）自然分流。

---

### 0.4 实体提取增强：降空率到 <25%

**问题**：65% 的数据没有任何实体，索引/关联/趋势发现全部失效。

**文件**：`v2/scripts/collector.py`

**修改位置**：`RuleBasedAnnotator` 类的 `ENTITY_MAP`（第 227-357 行）和 `annotate()` 方法

**具体要求**：

#### 0.4.1 扩充 ENTITY_MAP（从 ~80 条扩到 200+ 条）

新增以下实体映射（补充当前遗漏的重要实体）：

```python
# ===== 新增 AI 公司/产品 =====
"cohere": "Cohere",
"stability ai": "Stability AI",
"stable diffusion": "Stable Diffusion",
"runway": "Runway",
"flux": "Flux",
"whisper": "Whisper",
"together ai": "Together AI",
"hugging face": "HuggingFace",  # 带空格的版本
"manus": "Manus AI",
"manus ai": "Manus AI",
"豆包": "Doubao",
"doubao": "Doubao",
"文心一言": "ERNIE Bot",
"ernie": "ERNIE Bot",
"混元": "Hunyuan",
"hunyuan": "Hunyuan",
"天工": "Skywork",
"skywork": "Skywork",
"讯飞星火": "iFlytek Spark",
"spark": "iFlytek Spark",  # 注意：可能有歧义，但在科技语境下通常指讯飞
"abab": "MiniMax ABAB",

# ===== 新增芯片/硬件 =====
"h100": "NVIDIA H100",
"h200": "NVIDIA H200",
"b100": "NVIDIA B100",
"b200": "NVIDIA B200",
"gb200": "NVIDIA GB200",
"blackwell": "NVIDIA Blackwell",
"rubin": "NVIDIA Rubin",
"a100": "NVIDIA A100",
"hopper": "NVIDIA Hopper",
"grace": "NVIDIA Grace",
"骁龙": "Snapdragon",
"snapdragon": "Snapdragon",
"天玑": "Dimensity",
"dimensity": "Dimensity",
"exynos": "Samsung Exynos",
"a17 pro": "Apple A17 Pro",
"a18 pro": "Apple A18 Pro",
"m4": "Apple M4",
"m5": "Apple M5",

# ===== 新增手机品牌/产品 =====
"一加": "OnePlus",
"oneplus": "OnePlus",
"realme": "Realme",
"红米": "Redmi",
"redmi": "Redmi",
"小米su7": "Xiaomi SU7",
"小米汽车": "Xiaomi Auto",
"ipad": "iPad",
"macbook": "MacBook",
"mac pro": "Mac Pro",

# ===== 新增互联网公司 =====
"腾讯": "Tencent",
"tencent": "Tencent",
"阿里巴巴": "Alibaba",
"alibaba": "Alibaba",
"字节跳动": "ByteDance",
"bytedance": "ByteDance",
"百度": "Baidu",
"baidu": "Baidu",
"美团": "Meituan",
"meituan": "Meituan",
"京东": "JD.com",
"拼多多": "PDD",
"pinduoduo": "PDD",
"网易": "NetEase",
"netease": "NetEase",
"bilibili": "Bilibili",
"哔哩哔哩": "Bilibili",
"抖音": "Douyin",
"tiktok": "TikTok",
"小红书": "Xiaohongshu",
"快手": "Kuaishou",
"kuaishou": "Kuaishou",
"spotify": "Spotify",
"netflix": "Netflix",
"amazon": "Amazon",
"aws": "AWS",

# ===== 新增汽车 =====
"比亚迪": "BYD",  # 已有，确认
"蔚来": "NIO",
"nio": "NIO",
"小鹏": "XPeng",
"xpeng": "XPeng",
"理想汽车": "Li Auto",
"li auto": "Li Auto",
"问界": "AITO",
"aito": "AITO",
"特斯拉": "Tesla",  # 已有，确认

# ===== 新增游戏 =====
"epic games": "Epic Games",
"epic": "Epic Games",
"game pass": "Xbox Game Pass",
"switch 2": "Nintendo Switch 2",
"unreal engine": "Unreal Engine",
"虚幻引擎": "Unreal Engine",
"unity": "Unity",

# ===== 新增人物 =====
"李彦宏": "Robin Li",
"robin li": "Robin Li",
"马化腾": "Pony Ma",
"pony ma": "Pony Ma",
"jack dorsey": "Jack Dorsey",
"sundar pichai": "Sundar Pichai",
"craig federighi": "Craig Federighi",

# ===== 新增平台/产品 =====
"cursor": "Cursor",  # 已有，确认
"windsurf": "Windsurf",
"devin": "Devin",
"vercel": "Vercel",
"supabase": "Supabase",
"cloudflare": "Cloudflare",
"product hunt": "Product Hunt",
```

#### 0.4.2 基于 @screen_name 自动映射实体

在 `annotate()` 方法中，当 `author` 参数是 `@xxx` 格式时，尝试从 ENTITY_MAP 匹配：

```python
# 在 annotate() 方法中，实体提取部分之后添加：
# 如果 author 是 @xxx 格式，尝试提取实体
if author.startswith("@"):
    author_key = author[1:].lower()  # 去掉 @，小写
    if author_key in self.ENTITY_MAP:
        entity_name = self.ENTITY_MAP[author_key]
        if entity_name not in entities:
            entities.append(entity_name)
```

#### 0.4.3 RSS source_name 反查实体

在 `RSSAdapter.rss_item_to_atom()` 调用 annotator 时，把 `source_name` 也传进去：

当前代码（第 875 行附近）：
```python
annotation = self.annotator.annotate(content, username)
```

对于 RSS，应改为（在 `rss_item_to_atom` 中，约第 1040 行）：
```python
annotation = self.annotator.annotate(f"{title} {summary}", source_name)
```

确认当前代码中 RSS 的 annotate 调用确实传了 source_name。如果没传，要补上。

---

### 0.5 移除硬编码 API Key

**问题**：Tavily API Key 硬编码在代码第 1620 行。

**文件**：`v2/scripts/collector.py`

**修改位置**：第 1620 行

**当前代码**：
```python
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "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")
```

**改为**：
```python
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
if not TAVILY_API_KEY:
    print("  ⚠️ TAVILY_API_KEY 未设置，跳过 Tavily 搜索")
    return []
```

---

### 0.6 修复微博 adapter 的 author_type 硬编码

**问题**：所有微博数据的 `author_type` 都硬编码为 `"blogger"`（第 870 行），没有读取 `weibo_users.yaml` 中的 `category` 和 `tier` 信息。导致数码闲聊站（T3 爆料人）和机器之心（T1 AI 媒体）都被标为 `blogger`，trust_default 全部是 L3。

**文件**：`v2/scripts/collector.py`

**修改位置**：`WeiBoAdapter.weibo_to_atom()` 方法（第 859 行开始）

**具体要求**：

1. 在 `WeiBoAdapter.__init__()` 中加载 `weibo_users.yaml`，构建一个 `username → {category, tier, author_type}` 的查找表
2. 在 `weibo_to_atom()` 中，根据查找表确定 `author_type`：

**映射规则**：

| yaml 中的 tier | yaml 中的 category | → author_type | → trust_default |
|---|---|---|---|
| T1 | AI | media | L2 |
| T2 | 科技/* | media | L2 |
| T3 | 手机/芯片 | insider | L2 |
| T3 | AI/科技 | kol | L2 |
| T4 | AI | kol | L2 |
| 其他 | 其他 | blogger | L3 |

**参考实现**：

```python
def __init__(self):
    self.annotator = RuleBasedAnnotator()
    self.user_map = self._load_user_config()

def _load_user_config(self) -> Dict[str, Dict]:
    """加载 weibo_users.yaml，构建 username→config 查找表"""
    import yaml
    config_file = CONFIG_DIR / "weibo_users.yaml"
    if not config_file.exists():
        return {}
    
    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    user_map = {}
    for user in config.get("weibo_users", []):
        name = user.get("name", "").strip()
        tier = user.get("tier", "")
        category = user.get("category", "")
        
        # 根据 tier + category 推断 author_type
        if tier == "T1" or tier == "T2":
            author_type = "media"
        elif tier == "T3":
            if "爆料" in user.get("description", "") or "手机" in category:
                author_type = "insider"
            else:
                author_type = "kol"
        elif tier == "T4":
            author_type = "kol"
        else:
            author_type = "blogger"
        
        user_map[name.lower()] = {
            "author_type": author_type,
            "tier": tier,
            "category": category,
        }
    
    return user_map
```

然后在 `weibo_to_atom()` 中替换第 870 行：

```python
# 旧代码：
# author_type = "blogger"  # 微博博主默认
# 新代码：
user_config = self.user_map.get(username.lower().strip(), {})
author_type = user_config.get("author_type", "blogger")
```

---

### 0.7 修复 Tavily fallback 的 author_type 非法值

**问题**：Tavily 搜索结果的 `author_type` 写了 `"aggregator"`（第 1771 行），这个值不在 Schema 的 `author_type.enum` 中。

**文件**：`v2/scripts/collector.py`

**修改位置**：第 1771 行

**当前代码**：
```python
author_type="aggregator",
```

**改为**：
```python
author_type="media",
```

**理由**：Tavily 搜索结果通常来自新闻媒体网站，`media` 是最合适的归类。

同时，第 1769 行的 `platform="tavily"` 也不在 Schema 的 `platform.enum`（`["x", "weibo", "rss", "web", "arxiv", "github"]`）中。

**改为**：
```python
platform="web",
```

---

### 0.8 修复 RSS adapter 的时间戳问题

**问题**：`fetch_all_feeds()` 中每条 RSS 条目的 `date` 都取 `datetime.now()`（第 1095 行），而非条目的实际发布时间。

**文件**：`v2/scripts/collector.py`

**修改位置**：第 1095-1097 行

**当前代码**：
```python
date = datetime.now().strftime("%Y-%m-%d")
for item in items:
    atom = self.rss_item_to_atom(item, name, domain, date)
```

**改为**：
```python
today = datetime.now().strftime("%Y-%m-%d")
for item in items:
    # 优先使用 RSS 条目的发布时间，fallback 到当前时间
    pub_date = item.get("published", "") or item.get("updated", "")
    if pub_date:
        try:
            from email.utils import parsedate_to_datetime
            item_dt = parsedate_to_datetime(pub_date)
            date = item_dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            date = today
    else:
        date = today
    atom = self.rss_item_to_atom(item, name, domain, date)
```

**注意**：`parsedate_to_datetime` 是标准库 `email.utils` 的函数，能解析 RFC 2822 格式（RSS 常用格式）。如果 RSS 条目用的是 Atom 格式（ISO 8601），需要额外处理。建议加一个 fallback：

```python
try:
    from email.utils import parsedate_to_datetime
    item_dt = parsedate_to_datetime(pub_date)
    date = item_dt.strftime("%Y-%m-%d")
except (ValueError, TypeError):
    try:
        # ISO 8601 fallback
        item_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
        date = item_dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        date = today
```

---

## Phase 1：可靠性提升

### 1.1 RSS 并行抓取

**问题**：`fetch_all_feeds()` 是串行逐个抓取，50 个 feed × 15 秒超时 ≈ 最坏 12 分钟。

**文件**：`v2/scripts/collector.py`

**修改位置**：`RSSAdapter.fetch_all_feeds()` 方法（第 1073 行开始）

**具体要求**：

使用 `concurrent.futures.ThreadPoolExecutor` 并行抓取，最多 8 个线程：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_all_feeds(self, feed_urls: List[Dict], max_per_feed: int = 10) -> List[Dict]:
    all_atoms = []
    
    def _fetch_one(feed_info):
        url = feed_info.get("url", "")
        name = feed_info.get("name", "Unknown")
        domain = feed_info.get("domain", "")
        
        items = self.fetch_feed(url, max_items=max_per_feed)
        
        atoms = []
        today = datetime.now().strftime("%Y-%m-%d")
        for item in items:
            # （同 0.8 的时间戳修复逻辑）
            pub_date = item.get("published", "") or item.get("updated", "")
            date = self._parse_pub_date(pub_date, today)
            atom = self.rss_item_to_atom(item, name, domain, date)
            if atom:
                atoms.append(atom)
        return name, atoms
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_fetch_one, fi): fi for fi in feed_urls}
        for future in as_completed(futures):
            try:
                name, atoms = future.result()
                print(f"  ✅ {name}: {len(atoms)} 条", flush=True)
                all_atoms.extend(atoms)
            except Exception as e:
                fi = futures[future]
                print(f"  ⚠️ {fi.get('name', '?')} 失败: {e}", flush=True)
    
    return all_atoms
```

**注意**：把时间解析逻辑提取成 `_parse_pub_date()` 私有方法，避免重复。

---

### 1.2 索引写入原子化

**问题**：`_save_index()` 直接覆写文件，如果写入过程中崩溃会损坏索引。

**文件**：`v2/scripts/atom_store.py`

**修改位置**：`_save_index()` 方法（第 454 行）

**当前代码**：
```python
def _save_index(self, filename: str, data: Dict[str, List[str]]):
    path = self.index_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

**改为**（write-to-temp + atomic rename）：
```python
def _save_index(self, filename: str, data: Dict[str, List[str]]):
    path = self.index_dir / filename
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(str(tmp_path), str(path))  # 原子替换
```

需要在文件顶部确认 `import os` 已存在（当前第 24 行已有）。

同理，`save_atoms_batch()` 中写 JSONL 也应该用类似的安全写入方式。但因为 JSONL 是 append 模式，崩溃最多丢失最后一条，风险较低。**索引写入是重点**。

---

### 1.3 ID 生成改为内存计数器

**问题**：`generate_id()` 每次调用 `query_by_date()` 读取整个 JSONL 文件来计算下一个 ID。在 `save_atoms_batch()` 中批量保存 N 条时，这会导致 O(N²) 的 I/O。

**文件**：`v2/scripts/atom_store.py`

**修改位置**：`generate_id()` 方法（第 64 行）

**具体要求**：

1. 在 `AtomStore.__init__()` 中初始化一个日期→计数器的字典
2. `generate_id()` 只在首次调用某日期时读一次文件，之后在内存中递增

```python
def __init__(self, base_dir=None):
    # ... 原有代码 ...
    self._id_counters: Dict[str, int] = {}  # date → next_num

def generate_id(self, date: str) -> str:
    date_compact = date.replace("-", "")
    
    if date not in self._id_counters:
        # 首次：读取当日已有数量
        existing = self.query_by_date(date)
        self._id_counters[date] = len(existing) + 1
    
    num = self._id_counters[date]
    self._id_counters[date] = num + 1
    
    return f"atom_{date_compact}_{num:03d}"
```

---

### 1.4 硬编码路径迁移到配置

**问题**：`PATH_ENV`（第 45 行）和 `OBSIDIAN_VAULT`（第 48 行）是硬编码的绝对路径。

**文件**：`v2/scripts/collector.py`

**修改位置**：第 45-48 行

**改为**：
```python
# 环境变量（可通过 .env 或 export 自定义）
PATH_ENV = os.environ.get(
    "COLLECTOR_PATH",
    os.path.expanduser("~/.local/bin") + ":/Library/Frameworks/Python.framework/Versions/3.13/bin:/usr/local/bin:/usr/bin:/bin"
)

# Obsidian vault 路径（可选，仅同步功能需要）
OBSIDIAN_VAULT = Path(os.environ.get(
    "OBSIDIAN_VAULT",
    "~/Documents/Obsidian/资讯"
)).expanduser()
```

---

### 1.5 错误处理统一 + 重试机制

**问题**：外部 API/CLI 调用没有重试机制，单次超时就放弃。

**文件**：`v2/scripts/collector.py`

**修改位置**：新增一个工具函数，在文件开头的配置区域之后

**具体要求**：

新增一个 `_retry_subprocess()` 通用重试包装：

```python
def _retry_subprocess(cmd, max_retries=2, timeout=60, **kwargs):
    """带重试的 subprocess.run 封装"""
    import time
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kwargs)
            return result
        except subprocess.TimeoutExpired as e:
            last_err = e
            if attempt < max_retries:
                wait = 2 ** attempt  # 指数退避：1s, 2s
                print(f"    ⏱️ 超时，{wait}s 后重试 ({attempt+1}/{max_retries})...", flush=True)
                time.sleep(wait)
        except Exception as e:
            last_err = e
            break
    raise last_err
```

然后在各 adapter 的 `subprocess.run()` 调用处，替换为 `_retry_subprocess()`。

---

## Phase 2：架构优化（可分次做）

### 2.1 拆分 collector.py

**目标**：将 1913 行的单文件拆为模块化结构。

**目标目录结构**：
```
v2/scripts/
├── collector.py          # CLI 入口（精简为 ~100 行）
├── atom_store.py         # 不变
├── annotator.py          # RuleBasedAnnotator 独立出来
├── adapters/
│   ├── __init__.py
│   ├── x_adapter.py      # XTwitterAdapter
│   ├── weibo_adapter.py  # WeiBoAdapter
│   └── rss_adapter.py    # RSSAdapter + TavilyFallback
└── utils.py              # 通用工具函数（_retry_subprocess 等）
```

**注意**：拆分时不要改变任何逻辑，纯结构重组。拆分后确保 `python3 collector.py --source all` 仍能正常运行。

### 2.2 logging 替代 print

所有 `print()` 替换为 `logging`，使用 `logging.getLogger("v2.collector")` 等命名空间。

级别映射：
- 信息性输出 → `logging.info()`
- 警告（⚠️） → `logging.warning()`
- 错误 → `logging.error()`
- 调试信息 → `logging.debug()`

### 2.3 Quote Tweet 双向关联

**问题**：X adapter 对 Quote Tweet 同时产出引用者 atom + 被引者 atom，但没有建立双向关联。

**文件**：`v2/scripts/collector.py` 中的 `XTwitterAdapter`

**要求**：在产出 Quote Tweet 的两个 atom 时，互相在 `related_atoms` 字段中写入对方的 ID。需要在 `save_atoms_batch()` 之前完成关联。

---

## 三、验收标准

完成所有修改后，运行以下命令验证：

```bash
# 1. 语法检查
python3 -c "from v2.scripts.collector import *; print('import OK')"
python3 -c "from v2.scripts.atom_store import *; print('import OK')"

# 2. Schema 验证
python3 -c "
import json
with open('v2/config/atom_schema.json') as f:
    schema = json.load(f)
cats = schema['properties']['category']['enum']
expected = ['ai_models','mobile','chips','gaming','tech_industry','policy','github','software_dev','internet_tech','ev_auto','crypto_web3','other']
assert set(expected) == set(cats), f'Missing: {set(expected)-set(cats)}'
print('Schema OK')
"

# 3. 单次采集测试（dry run）
cd /Users/yangliu/Documents/Claude\ Code/codebuddy/tech-daily-brief
python3 v2/scripts/collector.py --source rss 2>&1 | head -50

# 4. 去重验证
python3 -c "
from v2.scripts.atom_store import AtomStore
store = AtomStore()
from datetime import datetime
date = datetime.now().strftime('%Y-%m-%d')
atoms = store.query_by_date(date)
urls = [a.get('source',{}).get('url','') for a in atoms if a.get('source',{}).get('url','')]
unique = len(set(urls))
total = len(urls)
print(f'Total: {total}, Unique URLs: {unique}, Dupe rate: {(total-unique)/max(total,1)*100:.1f}%')
"
```

**质量指标目标**：
- URL 重复率：< 5%（当前 42-49%）
- `other` 分类占比：< 15%（当前 46%）
- 实体为空的占比：< 25%（当前 65%）
- 非法 Schema 值：0 个（当前 2 个：`aggregator` + `tavily`）

---

## 四、⚠️ 禁止事项

1. **不要修改 `atom_schema.json` 的 required 字段**——已有字段全部保留
2. **不要引入新的外部依赖**——所有修改只用 Python 标准库 + 已有依赖（yaml、json、feedparser）
3. **不要动 `generate_daily.py`**——该文件不在本次修改范围内
4. **不要改变 JSONL 存储格式**——只在写入前加过滤，不改变输出格式
5. **不要删除任何现有的 ENTITY_MAP 条目**——只增不减
6. **不要改变 CLI 接口**——`python3 collector.py --source x/weibo/rss/all` 必须保持兼容
7. **不要修改 `weibo_users.yaml` 的结构**——只读取，不写入

---

## 五、修改检查清单

完成后请逐项打勾：

- [ ] **0.1** `atom_store.py` — `save_atoms_batch()` 和 `save_atom()` 加 URL 去重
- [ ] **0.2** `atom_schema.json` — category enum 补充 4 个分类
- [ ] **0.3** `collector.py` — RuleBasedAnnotator 分类器增强（作者提示 + 关键词扩充 + 消除重叠）
- [ ] **0.4** `collector.py` — ENTITY_MAP 扩充到 200+ 条 + @screen_name 映射 + source_name 反查
- [ ] **0.5** `collector.py` — 移除硬编码 API Key
- [ ] **0.6** `collector.py` — WeiBoAdapter 读取 weibo_users.yaml 的 tier/category 设置 author_type
- [ ] **0.7** `collector.py` — Tavily author_type 改 "media"，platform 改 "web"
- [ ] **0.8** `collector.py` — RSS date 使用条目发布时间
- [ ] **1.1** `collector.py` — RSS 并行抓取（ThreadPoolExecutor, 8 线程）
- [ ] **1.2** `atom_store.py` — 索引写入原子化（write-to-temp + os.replace）
- [ ] **1.3** `atom_store.py` — ID 生成改为内存计数器
- [ ] **1.4** `collector.py` — 硬编码路径改为环境变量
- [ ] **1.5** `collector.py` — 新增 `_retry_subprocess()` 重试机制
- [ ] **2.1** 拆分 collector.py 为模块化结构（可选，可后做）
- [ ] **2.2** logging 替代 print（可选，可后做）
- [ ] **2.3** Quote Tweet 双向关联（可选，可后做）
