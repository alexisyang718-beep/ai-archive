#!/usr/bin/env python3
"""
监控报告生成器

功能：
1. 显示每次爬取的状态（成功/失败）
2. 统计各渠道爬取数量
3. 按板块分布统计
4. 输出为终端报告或 HTML

用法：
    python monitor_report.py --date 2026-03-23
    python monitor_report.py --date 2026-03-23 --html
    python monitor_report.py --date 2026-03-23 --html --output monitor.html
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore

V2_ROOT = Path(__file__).parent.parent
ARCHIVE_DIR = V2_ROOT / "archive" / "daily"
REPORTS_DIR = V2_ROOT / "reports"

# 板块显示名称
CATEGORY_NAMES = {
    "ai_models": "🤖 AI模型与产品",
    "mobile": "📱 手机与消费电子",
    "chips": "🔧 芯片与算力",
    "gaming": "🎮 游戏行业",
    "tech_industry": "🏢 科技行业动态",
    "policy": "📜 政策与监管",
}

# 渠道显示名称
SOURCE_NAMES = {
    "x": "X/Twitter",
    "weibo": "微博",
    "rss": "RSS",
}


def load_atoms_by_source(date_str: str) -> Dict[str, List[Dict]]:
    """按渠道加载当日数据"""
    result = {}
    date_dir = ARCHIVE_DIR / date_str
    
    if not date_dir.exists():
        return result
    
    for source in ["x", "weibo", "rss"]:
        file_path = date_dir / f"{source}.jsonl"
        if file_path.exists():
            atoms = []
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            atoms.append(json.loads(line))
                result[source] = atoms
            except Exception as e:
                print(f"⚠️ 读取 {source}.jsonl 失败: {e}", file=sys.stderr)
                result[source] = []
    
    return result


def analyze_data(atoms_by_source: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """分析数据，生成统计信息"""
    stats = {
        "total": 0,
        "by_source": {},
        "by_category": defaultdict(int),
        "by_author_type": defaultdict(int),
        "by_trust": defaultdict(int),
        "top_entities": Counter(),
        "top_authors": Counter(),
        "errors": [],
    }
    
    for source, atoms in atoms_by_source.items():
        stats["by_source"][source] = len(atoms)
        stats["total"] += len(atoms)
        
        for atom in atoms:
            # 板块统计
            cat = atom.get("category", "unknown")
            stats["by_category"][cat] += 1
            
            # 作者类型统计
            author_type = atom.get("source", {}).get("author_type", "unknown")
            stats["by_author_type"][author_type] += 1
            
            # 置信度统计
            trust = atom.get("trust_default", "unknown")
            stats["by_trust"][trust] += 1
            
            # 实体统计
            entities = atom.get("entities", [])
            for entity in entities:
                stats["top_entities"][entity] += 1
            
            # 作者统计
            author = atom.get("source", {}).get("author", "unknown")
            stats["top_authors"][author] += 1
    
    return stats


def generate_terminal_report(date_str: str, atoms_by_source: Dict[str, List[Dict]], stats: Dict) -> str:
    """生成终端格式的报告"""
    lines = []
    lines.append("=" * 70)
    lines.append(f"📊 采集监控报告 - {date_str}")
    lines.append("=" * 70)
    lines.append("")
    
    # 1. 采集状态概览
    lines.append("┌─ 采集状态 ─" + "─" * 56)
    for source in ["x", "weibo", "rss"]:
        source_name = SOURCE_NAMES.get(source, source)
        if source in atoms_by_source:
            count = len(atoms_by_source[source])
            status = "✅ 成功" if count > 0 else "⚠️ 无数据"
            lines.append(f"│ {source_name:12} {status:8}  {count:4} 条")
        else:
            lines.append(f"│ {source_name:12} ❌ 失败     未找到数据文件")
    lines.append(f"├─ 总计: {stats['total']} 条")
    lines.append("└" + "─" * 68)
    lines.append("")
    
    # 2. 板块分布
    lines.append("┌─ 板块分布 ─" + "─" * 56)
    for cat, name in CATEGORY_NAMES.items():
        count = stats["by_category"].get(cat, 0)
        if stats["total"] > 0:
            pct = count / stats["total"] * 100
            bar = "█" * int(pct / 5)
            lines.append(f"│ {name:20} {count:4} 条 ({pct:5.1f}%) {bar}")
    lines.append("└" + "─" * 68)
    lines.append("")
    
    # 3. 信源质量分布
    lines.append("┌─ 信源质量分布 ─" + "─" * 52)
    trust_labels = {"L1": "🔴 L1 一手", "L2": "🟡 L2 可靠", "L3": "🟢 L3 参考"}
    for trust, label in trust_labels.items():
        count = stats["by_trust"].get(trust, 0)
        if stats["total"] > 0:
            pct = count / stats["total"] * 100
            lines.append(f"│ {label:15} {count:4} 条 ({pct:5.1f}%)")
    lines.append("└" + "─" * 68)
    lines.append("")
    
    # 4. 热门实体 TOP 10
    lines.append("┌─ 热门实体 TOP 10 ─" + "─" * 48)
    for entity, count in stats["top_entities"].most_common(10):
        lines.append(f"│ {entity:30} {count:4} 次")
    lines.append("└" + "─" * 68)
    lines.append("")
    
    # 5. 活跃作者 TOP 10
    lines.append("┌─ 活跃作者 TOP 10 ─" + "─" * 48)
    for author, count in stats["top_authors"].most_common(10):
        lines.append(f"│ {author:30} {count:4} 条")
    lines.append("└" + "─" * 68)
    
    return "\n".join(lines)


def generate_html_report(date_str: str, atoms_by_source: Dict[str, List[Dict]], stats: Dict) -> str:
    """生成 HTML 格式的报告"""
    
    # 计算百分比
    def pct(value, total):
        return (value / total * 100) if total > 0 else 0
    
    # 板块颜色
    cat_colors = {
        "ai_models": "#e74c3c",
        "mobile": "#3498db",
        "chips": "#f39c12",
        "gaming": "#9b59b6",
        "tech_industry": "#1abc9c",
        "policy": "#34495e",
    }
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>采集监控报告 - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 28px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            font-size: 18px;
            color: #555;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        .stat-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        .stat-row:last-child {{ border-bottom: none; }}
        .stat-label {{ color: #666; font-size: 14px; }}
        .stat-value {{ font-weight: bold; color: #333; }}
        .stat-bar {{
            width: 100%;
            height: 8px;
            background: #eee;
            border-radius: 4px;
            margin-top: 5px;
            overflow: hidden;
        }}
        .stat-bar-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s;
        }}
        .status-success {{ color: #27ae60; }}
        .status-warning {{ color: #f39c12; }}
        .status-error {{ color: #e74c3c; }}
        .big-number {{
            font-size: 48px;
            font-weight: bold;
            color: #2c3e50;
            text-align: center;
            padding: 20px;
        }}
        .big-label {{
            text-align: center;
            color: #7f8c8d;
            font-size: 14px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th, td {{
            text-align: left;
            padding: 10px;
            border-bottom: 1px solid #eee;
        }}
        th {{
            color: #7f8c8d;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
        }}
        tr:hover {{ background: #f9f9f9; }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-l1 {{ background: #ffebee; color: #c62828; }}
        .badge-l2 {{ background: #fff3e0; color: #ef6c00; }}
        .badge-l3 {{ background: #e8f5e9; color: #2e7d32; }}
        .timestamp {{
            text-align: center;
            color: #95a5a6;
            font-size: 12px;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 采集监控报告 - {date_str}</h1>
        
        <!-- 总览卡片 -->
        <div class="grid">
            <div class="card">
                <div class="big-number">{stats['total']}</div>
                <div class="big-label">总采集条数</div>
            </div>
            <div class="card">
                <div class="big-number">{len(atoms_by_source)}</div>
                <div class="big-label">活跃渠道数</div>
            </div>
            <div class="card">
                <div class="big-number">{len(stats['by_category'])}</div>
                <div class="big-label">覆盖板块数</div>
            </div>
        </div>
        
        <!-- 采集状态 -->
        <div class="grid">
            <div class="card">
                <h2>📡 采集状态</h2>
"""
    
    for source in ["x", "weibo", "rss"]:
        source_name = SOURCE_NAMES.get(source, source)
        if source in atoms_by_source:
            count = len(atoms_by_source[source])
            status_class = "status-success" if count > 0 else "status-warning"
            status_text = "成功" if count > 0 else "无数据"
            html += f"""
                <div class="stat-row">
                    <span class="stat-label">{source_name}</span>
                    <span class="stat-value {status_class}">{status_text} ({count} 条)</span>
                </div>"""
        else:
            html += f"""
                <div class="stat-row">
                    <span class="stat-label">{source_name}</span>
                    <span class="stat-value status-error">失败</span>
                </div>"""
    
    html += """
            </div>
            
            <!-- 板块分布 -->
            <div class="card">
                <h2>📊 板块分布</h2>
"""
    
    for cat, name in CATEGORY_NAMES.items():
        count = stats["by_category"].get(cat, 0)
        percentage = pct(count, stats["total"])
        color = cat_colors.get(cat, "#95a5a6")
        html += f"""
                <div class="stat-row">
                    <span class="stat-label">{name}</span>
                    <span class="stat-value">{count} ({percentage:.1f}%)</span>
                </div>
                <div class="stat-bar">
                    <div class="stat-bar-fill" style="width: {percentage}%; background: {color};"></div>
                </div>"""
    
    html += """
            </div>
        </div>
        
        <!-- 信源质量 -->
        <div class="grid">
            <div class="card">
                <h2>🎯 信源质量分布</h2>
"""
    
    trust_info = [
        ("L1", "一手信源", "badge-l1"),
        ("L2", "可靠信源", "badge-l2"),
        ("L3", "参考信源", "badge-l3"),
    ]
    for trust, label, badge_class in trust_info:
        count = stats["by_trust"].get(trust, 0)
        percentage = pct(count, stats["total"])
        html += f"""
                <div class="stat-row">
                    <span class="stat-label"><span class="badge {badge_class}">{label}</span></span>
                    <span class="stat-value">{count} ({percentage:.1f}%)</span>
                </div>"""
    
    html += """
            </div>
            
            <!-- 热门实体 -->
            <div class="card">
                <h2>🔥 热门实体 TOP 10</h2>
                <table>
                    <thead>
                        <tr><th>实体</th><th>出现次数</th></tr>
                    </thead>
                    <tbody>
"""
    
    for entity, count in stats["top_entities"].most_common(10):
        html += f"""
                        <tr>
                            <td>{entity}</td>
                            <td>{count}</td>
                        </tr>"""
    
    html += """
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- 活跃作者 -->
        <div class="card">
            <h2>👤 活跃作者 TOP 10</h2>
            <table>
                <thead>
                    <tr><th>作者</th><th>发布数量</th></tr>
                </thead>
                <tbody>
"""
    
    for author, count in stats["top_authors"].most_common(10):
        html += f"""
                    <tr>
                        <td>{author}</td>
                        <td>{count}</td>
                    </tr>"""
    
    html += f"""
                </tbody>
            </table>
        </div>
        
        <div class="timestamp">
            报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>
</body>
</html>"""
    
    return html


def main():
    parser = argparse.ArgumentParser(description="生成采集监控报告")
    parser.add_argument("--date", required=True, help="日期 (YYYY-MM-DD)")
    parser.add_argument("--html", action="store_true", help="输出 HTML 格式")
    parser.add_argument("--output", help="输出文件路径（仅HTML模式）")
    args = parser.parse_args()
    
    # 加载数据
    atoms_by_source = load_atoms_by_source(args.date)
    
    if not atoms_by_source:
        print(f"⚠️ 未找到 {args.date} 的数据", file=sys.stderr)
        sys.exit(1)
    
    # 分析数据
    stats = analyze_data(atoms_by_source)
    
    if args.html:
        # 生成 HTML 报告
        html = generate_html_report(args.date, atoms_by_source, stats)
        
        if args.output:
            output_path = Path(args.output)
        else:
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            output_path = REPORTS_DIR / f"monitor_{args.date}.html"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ HTML 报告已生成: {output_path}")
    else:
        # 生成终端报告
        report = generate_terminal_report(args.date, atoms_by_source, stats)
        print(report)


if __name__ == "__main__":
    main()
