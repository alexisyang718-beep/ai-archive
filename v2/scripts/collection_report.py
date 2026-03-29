#!/usr/bin/env python3
"""
采集报告生成器 - 每次采集后生成报告

用途：
1. 记录本次采集的数量、时间范围
2. 对比上次采集，显示新增内容
3. 列出失败/异常的账号
4. 分类统计，发现分类偏差

用法：
    python collection_report.py --date 2026-03-23 --channel x
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter

V2_ROOT = Path(__file__).parent.parent
ARCHIVE_DIR = V2_ROOT / "archive" / "daily"
REPORT_DIR = V2_ROOT / "reports"

CATEGORY_NAMES = {
    "ai_models": "🤖 AI模型与产品",
    "mobile": "📱 手机与消费电子",
    "chips": "🔧 芯片与算力",
    "gaming": "🎮 游戏行业",
    "tech_industry": "🏢 科技行业动态",
    "policy": "📜 政策与监管",
    "ev_auto": "🚗 电动车",
    "crypto_web3": "₿ 加密/Web3",
    "software_dev": "💻 软件开发",
    "internet_tech": "🌐 互联网技术",
    "other": "📋 其他",
}


def load_jsonl(filepath: Path) -> list:
    """加载 JSONL 文件"""
    atoms = []
    if not filepath.exists():
        return atoms
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    atoms.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return atoms


def generate_report(date: str, channel: str):
    """生成采集报告"""
    date_dir = ARCHIVE_DIR / date
    jsonl_path = date_dir / f"{channel}.jsonl"
    
    if not jsonl_path.exists():
        print(f"❌ 文件不存在: {jsonl_path}")
        return
    
    atoms = load_jsonl(jsonl_path)
    
    # 基础统计
    total = len(atoms)
    
    # 分类统计
    cat_counter = Counter()
    author_counter = Counter()
    content_types = Counter()
    
    # 时间分布（按小时）
    hour_counter = Counter()
    
    # 引用/转发统计
    quotes_count = 0
    repost_count = 0
    with_links = 0
    
    for atom in atoms:
        # 分类
        cat = atom.get("category", "other")
        cat_counter[cat] += 1
        
        # 作者
        author = atom.get("source", {}).get("author", "unknown")
        author_counter[author] += 1
        
        # 内容类型
        ct = atom.get("content_type", "unknown")
        content_types[ct] += 1
        
        # 时间
        ts = atom.get("source", {}).get("timestamp", "")
        if ts:
            try:
                hour = ts.split(":")[0].split()[-1]
                hour_counter[hour] += 1
            except:
                pass
        
        # 引用/转发
        if atom.get("quotes_tweet"):
            quotes_count += 1
        if atom.get("is_repost"):
            repost_count += 1
        if atom.get("embedded_urls"):
            with_links += 1
    
    # 生成报告
    report_lines = [
        f"# 📊 采集报告 - {channel.upper()} - {date}",
        f"",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"## 📈 总体统计",
        f"",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 总条数 | {total} |",
        f"| 引用推文 | {quotes_count} |",
        f"| 转发 | {repost_count} |",
        f"| 含链接 | {with_links} |",
        f"",
        f"## 📂 分类分布",
        f"",
    ]
    
    # 分类表格
    report_lines.append("| 分类 | 数量 | 占比 |")
    report_lines.append("|------|------|------|")
    for cat, count in cat_counter.most_common():
        pct = count / total * 100 if total > 0 else 0
        cat_name = CATEGORY_NAMES.get(cat, cat)
        report_lines.append(f"| {cat_name} | {count} | {pct:.1f}% |")
    
    # 告警：other分类过多
    other_count = cat_counter.get("other", 0)
    other_pct = other_count / total * 100 if total > 0 else 0
    if other_pct > 30:
        report_lines.append(f"")
        report_lines.append(f"⚠️ **警告**: {other_pct:.1f}% 的内容被分到 'other'，可能存在分类偏差")
        report_lines.append(f"")
        # 列出被分到other的内容示例
        other_atoms = [a for a in atoms if a.get("category") == "other"][:5]
        if other_atoms:
            report_lines.append(f"**被分到other的示例（前5条）:**")
            for a in other_atoms:
                title = a.get("title", "")[:60]
                author = a.get("source", {}).get("author", "")
                report_lines.append(f"- @{author}: {title}...")
    
    # 内容类型分布
    report_lines.append(f"")
    report_lines.append(f"## 📝 内容类型分布")
    report_lines.append(f"")
    report_lines.append("| 类型 | 数量 |")
    report_lines.append("|------|------|")
    for ct, count in content_types.most_common():
        report_lines.append(f"| {ct} | {count} |")
    
    # 高产作者TOP10
    report_lines.append(f"")
    report_lines.append(f"## 👤 高产作者 TOP10")
    report_lines.append(f"")
    report_lines.append("| 作者 | 条数 |")
    report_lines.append("|------|------|")
    for author, count in author_counter.most_common(10):
        report_lines.append(f"| {author} | {count} |")
    
    # 时间分布
    if hour_counter:
        report_lines.append(f"")
        report_lines.append(f"## ⏰ 时间分布（按小时）")
        report_lines.append(f"")
        report_lines.append("| 小时 | 条数 |")
        report_lines.append("|------|------|")
        for hour in sorted(hour_counter.keys()):
            report_lines.append(f"| {hour}:00 | {hour_counter[hour]} |")
    
    # 写入文件
    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / f"{date}_{channel}_report.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    
    print(f"✅ 报告已生成: {report_path}")
    
    # 控制台输出摘要
    print(f"\n📊 {channel.upper()} 采集摘要 ({date}):")
    print(f"   总计: {total} 条")
    print(f"   分类最多: {CATEGORY_NAMES.get(cat_counter.most_common(1)[0][0], 'unknown')} ({cat_counter.most_common(1)[0][1]} 条)")
    if other_pct > 30:
        print(f"   ⚠️ other分类占比 {other_pct:.1f}%，建议检查")
    
    return report_path


def main():
    parser = argparse.ArgumentParser(description="生成采集报告")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="日期 (YYYY-MM-DD)")
    parser.add_argument("--channel", choices=["x", "weibo", "rss"], required=True, help="渠道")
    
    args = parser.parse_args()
    generate_report(args.date, args.channel)


if __name__ == "__main__":
    main()
