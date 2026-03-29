#!/usr/bin/env python3
"""
合并多日期数据生成选题报告

使用方式:
    python3 generate_merged_report.py 2026-03-24 2026-03-25
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List

# 添加 v2/scripts 到 path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore

# ============ 配置 ============
V2_ROOT = Path(__file__).parent.parent
DOCS_DIR = V2_ROOT / "docs"
DAILY_DIR = V2_ROOT / "archive" / "daily"

# 分类显示名称
CATEGORY_NAMES = {
    "ai_models": "🤖 AI 模型与产品",
    "mobile": "📱 手机与消费电子",
    "chips": "🔧 芯片与算力",
    "gaming": "🎮 游戏行业",
    "tech_industry": "🏢 科技行业动态",
    "policy": "📜 政策与监管",
    "software_dev": "💻 开发者与软件工程",
    "internet_tech": "🌐 互联网科技",
    "ev_auto": "🚗 电动汽车",
    "crypto_web3": "₿ 加密与 Web3",
    "other": "📋 其他",
}

# 可信度图标
TRUST_ICONS = {
    "L1": "🟢",
    "L2": "🟡", 
    "L3": "🟠",
}

# 平台图标
PLATFORM_ICONS = {
    "x": "𝕏",
    "weibo": "📡",
    "rss": "📰",
}

# 内容类型标签
CONTENT_TYPE_LABELS = {
    "official": "官方",
    "exclusive": "独家",
    "firsthand_test": "实测",
    "original_analysis": "原创分析",
    "report": "报道",
    "commentary": "评论",
    "repost": "转发",
}

CHANNELS = {"x", "weibo", "rss"}


def load_atoms_by_date(date: str) -> List[Dict]:
    """加载指定日期的所有 Atoms"""
    atoms = []
    date_path = DAILY_DIR / date
    
    if not date_path.exists():
        return atoms
    
    for channel in CHANNELS:
        jsonl_path = date_path / f"{channel}.jsonl"
        if jsonl_path.exists():
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            atoms.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
    return atoms


def group_by_category(atoms: List[Dict]) -> Dict[str, List[Dict]]:
    """按分类分组"""
    groups = defaultdict(list)
    for atom in atoms:
        cat = atom.get("category", "other")
        groups[cat].append(atom)
    return groups


def format_atom(atom: Dict, index: int) -> str:
    """格式化单条新闻为 Markdown"""
    lines = []
    
    # 基础信息
    trust = atom.get("trust_default", "L3")
    trust_icon = TRUST_ICONS.get(trust, "⚪")
    
    source = atom.get("source", {})
    platform = source.get("platform", "unknown")
    platform_icon = PLATFORM_ICONS.get(platform, "📄")
    
    author = source.get("author", "未知")
    author_type = source.get("author_type", "")
    url = source.get("url", "")
    
    # 标题（优先中文标题）
    title = atom.get("title_zh") or atom.get("title", "无标题")
    
    # 内容摘要
    summary = atom.get("summary_zh", "")
    
    # 内容类型
    content_type = atom.get("content_type", "")
    ct_label = CONTENT_TYPE_LABELS.get(content_type, content_type)
    
    # 实体标签
    entities = atom.get("entities", [])
    entity_str = ", ".join(entities[:5]) if entities else ""
    
    # 互动数据（仅 X/微博）
    metrics = atom.get("metrics", {})
    metrics_str = ""
    if metrics:
        likes = metrics.get("likes", 0)
        retweets = metrics.get("retweets", 0)
        replies = metrics.get("replies", 0) or metrics.get("comments", 0)
        if likes or retweets or replies:
            metrics_str = f"❤️{likes} 🔁{retweets} 💬{replies}"
    
    # 来源日期
    atom_date = atom.get("date", "")
    date_tag = f"[{atom_date}]" if atom_date else ""
    
    # 生成 Markdown
    lines.append(f"### {index}. {trust_icon} {title} {date_tag}")
    lines.append("")
    
    # 元信息行
    meta_parts = [
        f"{platform_icon} **{author}**",
        f"类型: {ct_label}" if ct_label else "",
        f"可信度: {trust}",
        metrics_str,
    ]
    lines.append(" | ".join(p for p in meta_parts if p))
    lines.append("")
    
    # 内容摘要
    if summary:
        summary_clean = summary.strip().replace("\n", " ")
        if len(summary_clean) > 300:
            summary_clean = summary_clean[:300] + "..."
        lines.append(f"**内容**: {summary_clean}")
        lines.append("")
    
    # 原始链接
    if url:
        lines.append(f"🔗 [原始信源]({url})")
    
    # 实体标签
    if entity_str:
        lines.append(f"🏷️ {entity_str}")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    return "\n".join(lines)


def generate_report(dates: List[str]) -> str:
    """生成合并报告"""
    all_atoms = []
    date_stats = {}
    
    for date in dates:
        atoms = load_atoms_by_date(date)
        date_stats[date] = len(atoms)
        all_atoms.extend(atoms)
    
    if not all_atoms:
        return f"# 选题报告\n\n暂无数据。\n"
    
    # 去重（基于URL）
    seen_urls = set()
    unique_atoms = []
    for atom in all_atoms:
        url = atom.get("source", {}).get("url", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        unique_atoms.append(atom)
    
    # 按分类分组
    by_category = group_by_category(unique_atoms)
    
    # 按可信度排序（L1优先）
    for cat in by_category:
        by_category[cat].sort(
            key=lambda a: {"L1": 0, "L2": 1, "L3": 2}.get(a.get("trust_default", "L3"), 2)
        )
    
    # 生成 Markdown
    lines = []
    lines.append(f"# 📋 选题报告 - 合并报告")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**数据日期**: {', '.join(dates)}")
    lines.append(f"**总计**: {len(unique_atoms)} 条 (去重后)")
    lines.append("")
    
    # 各日期统计
    lines.append("**各日期数据**:")
    for date, count in date_stats.items():
        lines.append(f"- {date}: {count} 条")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 统计概览
    lines.append("## 📊 统计概览")
    lines.append("")
    
    for cat_key in ["ai_models", "mobile", "chips", "gaming", "tech_industry", "policy", "other"]:
        if cat_key in by_category:
            cat_name = CATEGORY_NAMES.get(cat_key, cat_key)
            count = len(by_category[cat_key])
            lines.append(f"- {cat_name}: {count} 条")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 详细内容（按分类）
    category_order = [
        "ai_models", "mobile", "chips", "gaming", 
        "tech_industry", "policy", "software_dev",
        "internet_tech", "ev_auto", "crypto_web3", "other"
    ]
    
    for cat_key in category_order:
        if cat_key not in by_category:
            continue
        
        cat_name = CATEGORY_NAMES.get(cat_key, cat_key)
        cat_atoms = by_category[cat_key]
        
        lines.append(f"## {cat_name}")
        lines.append(f"*{len(cat_atoms)} 条*")
        lines.append("")
        
        for i, atom in enumerate(cat_atoms, 1):
            lines.append(format_atom(atom, i))
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="合并多日期数据生成选题报告")
    parser.add_argument("dates", nargs="+", help="要合并的日期列表 (如 2026-03-24 2026-03-25)")
    parser.add_argument("--output", "-o", help="输出文件路径")
    args = parser.parse_args()
    
    report = generate_report(args.dates)
    
    # 保存报告
    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = DOCS_DIR / "daily" / today
    report_dir.mkdir(parents=True, exist_ok=True)
    
    if args.output:
        report_path = Path(args.output)
    else:
        report_path = report_dir / "merged_selection_report.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"✅ 合并选题报告已生成: {report_path}")
    print(f"📊 共 {report.count('###')} 条内容")
    
    # 打印统计
    for date in args.dates:
        count = len(load_atoms_by_date(date))
        print(f"  - {date}: {count} 条")


if __name__ == "__main__":
    main()
