#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime

# 简单翻译映射（英文关键词 → 中文）
TRANSLATIONS = {
    # AI & Tech
    "ai": "AI", "artificial intelligence": "人工智能", "machine learning": "机器学习",
    "openai": "OpenAI", "anthropic": "Anthropic", "google": "谷歌", "meta": "Meta",
    "microsoft": "微软", "nvidia": "英伟达", "apple": "苹果", "amazon": "亚马逊",
    "deepmind": "DeepMind", "chatgpt": "ChatGPT", "claude": "Claude", "gemini": "Gemini",
    "gpt": "GPT", "llm": "大模型", "model": "模型", "launch": "发布", "release": "发布",
    "announces": "宣布", "announcement": "公告", "beta": "测试版", "update": "更新",
    "new": "新的", "news": "新闻", "blog": "博客", "research": "研究",

    # Gaming
    "game": "游戏", "gaming": "游戏", "steam": "Steam", "playstation": "PS5",
    "xbox": "Xbox", "nintendo": "Switch", "switch": "Switch",

    # Chips
    "chip": "芯片", "gpu": "GPU", "cpu": "CPU", "processor": "处理器",
    "semiconductor": "半导体", "tsmc": "台积电", "amd": "AMD", "intel": "英特尔",
    "qualcomm": "高通", "snapdragon": "骁龙", "ryzen": "锐龙",

    # Mobile
    "iphone": "iPhone", "samsung": "三星", "android": "安卓", "ios": "iOS",
    "pixel": "Pixel", "huawei": "华为", "xiaomi": "小米", "oppo": "OPPO",
    "vivo": "vivo", "oneplus": "一加",

    # Industry
    "startup": "创业公司", "funding": "融资", "investment": "投资",
    "acquisition": "收购", "merger": "合并", "ipo": "IPO", "stock": "股票",
    "revenue": "营收", "earnings": "财报", "market": "市场", "tech": "科技",

    # Policy
    "regulation": "监管", "policy": "政策", "law": "法律", "government": "政府",
    "privacy": "隐私", "security": "安全", "breach": "泄露", "hack": "黑客",

    # Common
    "report": "报告", "study": "研究", "analysis": "分析", "review": "评测",
    "hands-on": "上手体验", "first look": "首发体验", "exclusive": "独家",
}

def translate_text(text):
    """简单翻译英文关键词为中文"""
    if not text:
        return text
    result = text
    # 按长度降序排列关键词，确保长词优先匹配
    for eng, chn in sorted(TRANSLATIONS.items(), key=lambda x: -len(x[0])):
        result = result.replace(eng, chn)
        result = result.replace(eng.title(), chn)  # 首字母大写
        result = result.replace(eng.upper(), chn)  # 全大写
    return result

def is_chinese(text):
    """判断是否包含中文"""
    for c in text:
        if '\u4e00' <= c <= '\u9fff':
            return True
    return False

base = Path("/Users/yangliu/Documents/Claude Code/codebuddy/tech-daily-brief/v2/archive/daily")
date = "2026-03-25"

atoms = []
for source in ["x", "rss", "weibo"]:
    # 先找带日期前缀的（新格式），再找子目录（2026-03-25/source.jsonl）
    f = base / f"{date}_{source}.jsonl"
    if not f.exists():
        f = base / date / f"{source}.jsonl"
    if f.exists():
        with open(f) as fp:
            for line in fp:
                line = line.strip()
                if line:
                    atoms.append(json.loads(line))

# 六大模块映射
module_map = {
    "ai_models": "🤖 AI模型与产品",
    "mobile": "📱 手机与消费电子",
    "chips": "🔧 芯片与算力",
    "gaming": "🎮 游戏行业",
    "tech_industry": "🏢 科技行业动态",
    "internet_tech": "🏢 科技行业动态",
    "policy": "📜 政策与监管",
}

# 按category分组
grouped = {}
for a in atoms:
    cat = a.get("category", "other")
    if cat in module_map:
        module = module_map[cat]
    else:
        module = "🔍 其他"

    if module not in grouped:
        grouped[module] = []

    # 优先用中文标题
    title = a.get("title_zh") or a.get("title", "")
    summary = a.get("summary_zh") or a.get("summary", "") or ""

    # 英文内容翻译
    if not is_chinese(title):
        title = translate_text(title)
    if not is_chinese(summary):
        summary = translate_text(summary)

    url = a.get("source", {}).get("upstream_url") or a.get("source", {}).get("url", "")
    author = a.get("source", {}).get("author", "")
    platform = a.get("source", {}).get("platform", "")
    trust = a.get("trust_default", "L2")
    content_type = a.get("content_type", "")

    grouped[module].append({
        "title": title[:150] if title else "无标题",
        "summary": summary[:200] if summary else "",
        "url": url,
        "author": author,
        "platform": platform,
        "trust": trust,
        "content_type": content_type,
    })

# 数据概览
x_count = len([a for a in atoms if (a.get("source") or {}).get("platform") == "x"])
rss_count = len([a for a in atoms if (a.get("source") or {}).get("platform") == "rss"])

# 输出报告
out = []
out.append("# 科技资讯日报选题 | 2026年3月23日\n")
out.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
out.append(f"数据来源: X/Twitter ({x_count}) + RSS ({rss_count}) = {len(atoms)} 条\n")
out.append("---\n")

for module in ["🤖 AI模型与产品", "📱 手机与消费电子", "🔧 芯片与算力", "🎮 游戏行业", "🏢 科技行业动态", "📜 政策与监管"]:
    items = grouped.get(module, [])
    out.append(f"## {module} ({len(items)}条)\n")
    if items:
        for i, item in enumerate(items[:8], 1):
            trust_icon = "✅" if item["trust"] == "L1" else "⚠️"
            ct = f"[{item['content_type']}]" if item['content_type'] else ""
            out.append(f"{trust_icon} **{item['title']}**\n")
            out.append(f"   - 来源: {item['author']} ({item['platform']}) {ct}\n")
            if item['url']:
                out.append(f"   - URL: {item['url'][:100]}\n")
            if item['summary']:
                out.append(f"   - 摘要: {item['summary'][:120]}...\n")
            out.append("\n")
    else:
        out.append("*（暂无数据）*\n")
    out.append("---\n")

# other中高信心的
other_items = grouped.get("🔍 其他", [])
if other_items:
    high_trust = [i for i in other_items if i["trust"] == "L1"][:5]
    if high_trust:
        out.append(f"## 🔍 其他高置信度 ({len(high_trust)}条)\n")
        for i, item in enumerate(high_trust, 1):
            out.append(f"✅ **{item['title']}**\n")
            out.append(f"   - 来源: {item['author']} ({item['platform']})\n")
            if item['url']:
                out.append(f"   - URL: {item['url'][:100]}\n")
            out.append("\n")

print("".join(out))
