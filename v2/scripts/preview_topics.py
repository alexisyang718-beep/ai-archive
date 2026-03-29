#!/usr/bin/env python3
"""
话题聚合预览 HTML 生成器

按话题聚类展示内容，而非按单条展示
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 导入话题聚类模块
import sys
sys.path.insert(0, str(Path(__file__).parent))
from topic_cluster import TopicCluster, Atom, load_atoms_from_jsonl

V2_ROOT = Path(__file__).parent.parent
ARCHIVE_DIR = V2_ROOT / "archive" / "daily"

CATEGORY_NAMES = {
    "ai_models": "🤖 AI 模型与产品",
    "mobile": "📱 手机与消费电子",
    "chips": "🔧 芯片与算力",
    "gaming": "🎮 游戏行业",
    "tech_industry": "🏢 科技行业动态",
    "policy": "📜 政策与监管",
    "other": "📋 其他",
}

TRUST_COLORS = {
    "L1": "#22c55e",
    "L2": "#eab308",
    "L3": "#f97316",
}


def escape_html(text: str) -> str:
    """转义 HTML 特殊字符"""
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def generate_topic_html(date: str, channel: str = None) -> Path:
    """生成按话题聚合的 HTML"""
    date_dir = ARCHIVE_DIR / date
    if not date_dir.exists():
        print(f"❌ 日期目录不存在: {date_dir}")
        return None

    # 加载数据
    channels_to_load = [channel] if channel else ["x", "weibo", "rss"]
    all_atoms = []
    channel_counts = {}

    for ch in channels_to_load:
        jsonl_path = date_dir / f"{ch}.jsonl"
        atoms = load_atoms_from_jsonl(jsonl_path)
        channel_counts[ch] = len(atoms)
        all_atoms.extend(atoms)

    if not all_atoms:
        print(f"⚠️ 没有找到数据")
        return None

    # 话题聚类
    cluster = TopicCluster()
    topics = cluster.cluster_atoms(all_atoms)

    # 按分类分组话题
    topics_by_category = defaultdict(list)
    for topic in topics:
        topics_by_category[topic.category].append(topic)

    # 生成 HTML
    html_parts = []
    html_parts.append("<!DOCTYPE html>")
    html_parts.append('<html lang="zh-CN">')
    html_parts.append("<head>")
    html_parts.append(f'    <meta charset="UTF-8">')
    html_parts.append(f'    <title>话题聚合预览 - {date}</title>')
    html_parts.append("    <style>")
    html_parts.append("""
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }
        .container { max-width: 900px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 24px;
        }
        .header h1 { font-size: 28px; margin-bottom: 8px; }
        .header .meta { opacity: 0.9; font-size: 14px; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .stat-card .number {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        .stat-card .label {
            color: #666;
            font-size: 14px;
            margin-top: 4px;
        }
        .category-section {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .category-header {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 2px solid #f0f0f0;
        }
        .topic {
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            margin-bottom: 16px;
            overflow: hidden;
        }
        .topic-header {
            background: #f8f9fa;
            padding: 16px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .topic-title {
            font-size: 17px;
            font-weight: 600;
            color: #1a1a2e;
        }
        .topic-heat {
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }
        .topic-meta {
            padding: 12px 20px;
            background: #fafafa;
            font-size: 13px;
            color: #666;
            border-bottom: 1px solid #eee;
        }
        .topic-content {
            padding: 16px 20px;
        }
        .atom-item {
            padding: 12px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        .atom-item:last-child {
            border-bottom: none;
        }
        .atom-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        }
        .trust-badge {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        .atom-author {
            font-weight: 500;
            color: #333;
        }
        .atom-platform {
            font-size: 12px;
            color: #999;
            background: #f0f0f0;
            padding: 2px 8px;
            border-radius: 4px;
        }
        .atom-text {
            color: #555;
            font-size: 14px;
            line-height: 1.6;
        }
        .atom-link {
            margin-top: 6px;
        }
        .atom-link a {
            color: #667eea;
            font-size: 13px;
            text-decoration: none;
        }
        .atom-link a:hover {
            text-decoration: underline;
        }
        .atom-metrics {
            font-size: 12px;
            color: #999;
            margin-top: 4px;
        }
    """)
    html_parts.append("    </style>")
    html_parts.append("</head>")
    html_parts.append("<body>")
    html_parts.append('    <div class="container">')

    # Header
    html_parts.append('        <div class="header">')
    html_parts.append(f'            <h1>🔥 话题聚合预览</h1>')
    html_parts.append(f'            <div class="meta">{date} | 共 {len(topics)} 个话题 / {len(all_atoms)} 条内容</div>')
    html_parts.append('        </div>')

    # Stats
    html_parts.append('        <div class="stats">')
    html_parts.append('            <div class="stat-card">')
    html_parts.append(f'                <div class="number">{len(topics)}</div>')
    html_parts.append('                <div class="label">热点话题</div>')
    html_parts.append('            </div>')
    html_parts.append('            <div class="stat-card">')
    html_parts.append(f'                <div class="number">{len(all_atoms)}</div>')
    html_parts.append('                <div class="label">总内容数</div>')
    html_parts.append('            </div>')
    for ch, count in channel_counts.items():
        html_parts.append('            <div class="stat-card">')
        html_parts.append(f'                <div class="number">{count}</div>')
        html_parts.append(f'                <div class="label">{ch.upper()}</div>')
        html_parts.append('            </div>')
    html_parts.append('        </div>')

    # Topics by category
    for cat, cat_topics in sorted(topics_by_category.items(), 
                                  key=lambda x: len(x[1]), reverse=True):
        cat_name = CATEGORY_NAMES.get(cat, cat)
        html_parts.append('        <div class="category-section">')
        html_parts.append(f'            <div class="category-header">{cat_name} ({len(cat_topics)}个话题)</div>')

        # 按热度排序
        sorted_topics = sorted(cat_topics, key=lambda t: t.heat_score, reverse=True)

        for topic in sorted_topics[:15]:  # 每类最多15个话题
            html_parts.append('            <div class="topic">')

            # Topic header
            html_parts.append('                <div class="topic-header">')
            html_parts.append(f'                    <div class="topic-title">{escape_html(topic.name)}</div>')
            html_parts.append(f'                    <div class="topic-heat">🔥 {topic.heat_score:.0f}</div>')
            html_parts.append('                </div>')

            # Topic meta
            sources = topic.get_top_sources(5)
            html_parts.append('                <div class="topic-meta">')
            html_parts.append(f'                    {len(topic.atoms)} 条内容 | 信源: {escape_html(", ".join(sources))}')
            html_parts.append('                </div>')

            # Topic content (atoms)
            html_parts.append('                <div class="topic-content">')

            # 按可信度排序
            sorted_atoms = sorted(topic.atoms, 
                                  key=lambda a: {"L1": 3, "L2": 2, "L3": 1}.get(a.trust, 1),
                                  reverse=True)

            for atom in sorted_atoms[:5]:  # 每个话题最多显示5条
                trust_color = TRUST_COLORS.get(atom.trust, "#999")

                html_parts.append('                    <div class="atom-item">')
                html_parts.append('                        <div class="atom-header">')
                html_parts.append(f'                            <div class="trust-badge" style="background: {trust_color}"></div>')
                html_parts.append(f'                            <span class="atom-author">{escape_html(atom.author)}</span>')
                html_parts.append(f'                            <span class="atom-platform">{atom.platform}</span>')
                html_parts.append('                        </div>')
                html_parts.append(f'                        <div class="atom-text">{escape_html(atom.summary[:150])}{"..." if len(atom.summary) > 150 else ""}</div>')

                # 互动数据
                if atom.metrics:
                    metrics_str = []
                    if atom.platform == "x":
                        if atom.metrics.get("likes"):
                            metrics_str.append(f'❤️ {atom.metrics["likes"]}')
                        if atom.metrics.get("retweets"):
                            metrics_str.append(f'🔄 {atom.metrics["retweets"]}')
                    elif atom.platform == "weibo":
                        if atom.metrics.get("likes"):
                            metrics_str.append(f'❤️ {atom.metrics["likes"]}')
                        if atom.metrics.get("retweets"):
                            metrics_str.append(f'🔄 {atom.metrics["retweets"]}')
                    if metrics_str:
                        html_parts.append(f'                        <div class="atom-metrics">{" | ".join(metrics_str)}</div>')

                html_parts.append(f'                        <div class="atom-link"><a href="{escape_html(atom.url)}" target="_blank">查看原文 →</a></div>')
                html_parts.append('                    </div>')

            if len(sorted_atoms) > 5:
                html_parts.append(f'                    <div style="text-align: center; padding: 8px; color: #999; font-size: 13px;">还有 {len(sorted_atoms) - 5} 条内容...</div>')

            html_parts.append('                </div>')  # topic-content
            html_parts.append('            </div>')  # topic

        html_parts.append('        </div>')  # category-section

    html_parts.append('    </div>')  # container
    html_parts.append('</body>')
    html_parts.append('</html>')

    # 写入文件
    preview_dir = V2_ROOT / "preview"
    preview_dir.mkdir(parents=True, exist_ok=True)

    if channel:
        output_path = preview_dir / f"{date}_{channel}_topics.html"
    else:
        output_path = preview_dir / f"{date}_topics.html"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    print(f"✅ 话题聚合预览已生成: {output_path}")
    print(f"   共 {len(topics)} 个话题 / {len(all_atoms)} 条内容")

    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成话题聚合预览 HTML")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="日期")
    parser.add_argument("--channel", choices=["x", "weibo", "rss"], help="渠道")
    parser.add_argument("--open", action="store_true", help="自动打开浏览器")

    args = parser.parse_args()

    output_path = generate_topic_html(args.date, args.channel)

    if output_path and args.open:
        import webbrowser
        webbrowser.open(f"file://{output_path.absolute()}")
