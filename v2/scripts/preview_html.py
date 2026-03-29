#!/usr/bin/env python3
"""
Preview HTML Generator — 生成本地 HTML 预览

用法:
    python3 preview_html.py --date 2026-03-23          # 生成某天的 HTML 预览
    python3 preview_html.py --date 2026-03-23 --open   # 生成并自动打开浏览器
    python3 preview_html.py --channel x                # 只预览 X 渠道
"""

import json
import argparse
import webbrowser
from pathlib import Path
from datetime import datetime

V2_ROOT = Path(__file__).parent.parent
ARCHIVE_DIR = V2_ROOT / "archive" / "daily"
DOCS_DIR = V2_ROOT / "docs"

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
    "L1": "#22c55e",  # 绿色
    "L2": "#eab308",  # 黄色
    "L3": "#f97316",  # 橙色
}

CONTENT_TYPE_LABELS = {
    "official": "官方",
    "exclusive": "独家",
    "firsthand_test": "实测",
    "original_analysis": "原创分析",
    "report": "报道",
    "commentary": "评论",
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


def build_quote_mapping(atoms: list) -> dict:
    """建立推文引用关系映射
    
    返回: {
        "quoted_map": {原推文url: [引用它的推文列表]},
        "quote_to_original": {引用推文id: 原推文url}
    }
    """
    quoted_map = {}  # 原推文 -> 引用它的推文列表
    quote_to_original = {}  # 引用推文 -> 原推文url
    
    # 先建立url到atom的映射
    url_to_atom = {}
    for atom in atoms:
        url = atom.get("source", {}).get("url", "")
        if url:
            url_to_atom[url] = atom
    
    # 建立引用关系
    for atom in atoms:
        quotes_tweet = atom.get("quotes_tweet", "")
        if quotes_tweet:
            quote_to_original[atom.get("id")] = quotes_tweet
            if quotes_tweet not in quoted_map:
                quoted_map[quotes_tweet] = []
            quoted_map[quotes_tweet].append(atom)
    
    return {"quoted_map": quoted_map, "quote_to_original": quote_to_original, "url_to_atom": url_to_atom}


def generate_html(date: str, channel: str = None) -> Path:
    """生成 HTML 预览文件"""
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
        atoms = load_jsonl(jsonl_path)
        channel_counts[ch] = len(atoms)
        all_atoms.extend(atoms)

    if not all_atoms:
        print(f"⚠️ 没有找到数据")
        return None

    # 建立引用关系映射
    quote_mapping = build_quote_mapping(all_atoms)
    quoted_map = quote_mapping["quoted_map"]
    quote_to_original = quote_mapping["quote_to_original"]
    url_to_atom = quote_mapping["url_to_atom"]
    
    # 标记已处理的推文（避免重复显示）
    processed_ids = set()
    
    # 按分类分组
    by_category = {}
    for atom in all_atoms:
        cat = atom.get("category", "other")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(atom)

    # 生成 HTML
    html_parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"    <title>科技资讯采集 - {date}</title>",
        "    <style>",
        "        * { margin: 0; padding: 0; box-sizing: border-box; }",
        "        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }",
        "        .container { max-width: 1200px; margin: 0 auto; }",
        "        .header { background: white; padding: 24px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }",
        "        .header h1 { font-size: 24px; margin-bottom: 12px; }",
        "        .stats { display: flex; gap: 16px; flex-wrap: wrap; }",
        "        .stat-item { background: #f8f9fa; padding: 8px 16px; border-radius: 8px; font-size: 14px; }",
        "        .category { background: white; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }",
        "        .category-header { background: #1a1a2e; color: white; padding: 16px 24px; font-size: 18px; font-weight: 600; }",
        "        .category-content { padding: 16px 24px; }",
        "        .item { border-bottom: 1px solid #eee; padding: 16px 0; }",
        "        .item:last-child { border-bottom: none; }",
        "        .item-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }",
        "        .trust-badge { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }",
        "        .item-title { font-size: 16px; font-weight: 600; color: #1a1a2e; line-height: 1.4; }",
        "        .item-meta { display: flex; gap: 12px; margin-top: 8px; font-size: 13px; color: #666; flex-wrap: wrap; }",
        "        .item-meta span { background: #f0f0f0; padding: 2px 8px; border-radius: 4px; }",
        "        .item-summary { margin-top: 8px; font-size: 14px; color: #555; line-height: 1.6; }",
        "        .item-link { margin-top: 8px; }",
        "        .item-link a { color: #0066cc; font-size: 13px; text-decoration: none; }",
        "        .item-link a:hover { text-decoration: underline; }",
        "        .empty { color: #999; font-style: italic; padding: 20px; text-align: center; }",
        "    </style>",
        "</head>",
        "<body>",
        '    <div class="container">',
        '        <div class="header">',
        f"            <h1>📰 科技资讯采集 - {date}</h1>",
        '            <div class="stats">',
    ]

    # 统计信息
    total = len(all_atoms)
    html_parts.append(f'                <div class="stat-item">📊 总计: {total} 条</div>')
    for ch, count in channel_counts.items():
        html_parts.append(f'                <div class="stat-item">{ch.upper()}: {count} 条</div>')
    html_parts.append("            </div>")
    html_parts.append("        </div>")

    # 按分类输出
    for cat_key in ["ai_models", "mobile", "chips", "gaming", "tech_industry", "policy", "other"]:
        if cat_key not in by_category:
            continue

        cat_name = CATEGORY_NAMES.get(cat_key, cat_key)
        cat_atoms = by_category[cat_key]

        html_parts.append('        <div class="category">')
        html_parts.append(f'            <div class="category-header">{cat_name} ({len(cat_atoms)} 条)</div>')
        html_parts.append('            <div class="category-content">')

        # 按 trust 排序
        cat_atoms = sorted(
            cat_atoms,
            key=lambda a: {"L1": 0, "L2": 1, "L3": 2}.get(a.get("trust_default", "L3"), 2),
        )

        for atom in cat_atoms:
            atom_id = atom.get("id")
            
            # 跳过已处理的推文（作为引用/转发已展示的）
            if atom_id in processed_ids:
                continue
            
            trust = atom.get("trust_default", "L3")
            trust_color = TRUST_COLORS.get(trust, "#999")
            author = atom.get("source", {}).get("author", "未知")
            author_type = atom.get("source", {}).get("author_type", "")
            content_type = atom.get("content_type", "")
            ct_label = CONTENT_TYPE_LABELS.get(content_type, content_type)
            title = atom.get("title_zh") or atom.get("title", "")
            url = atom.get("source", {}).get("url", "")
            summary = atom.get("summary_zh", "")
            platform = atom.get("source", {}).get("platform", "")

            # 获取内嵌链接和转发信息
            embedded_urls = atom.get("embedded_urls", [])
            quotes_tweet = atom.get("quotes_tweet", "")
            is_quoted = atom.get("is_quoted_tweet", False)
            is_repost = atom.get("is_repost", False)
            reposted_from = atom.get("reposted_from", "")
            
            # 收集所有相关链接（原推文 + 引用推文）
            all_embedded_urls = list(embedded_urls) if embedded_urls else []
            
            # 查找引用此推文的其他推文
            quoting_atoms = quoted_map.get(url, [])
            
            # 查找此推文引用的原推文
            original_atom = None
            if quotes_tweet and quotes_tweet in url_to_atom:
                original_atom = url_to_atom[quotes_tweet]
            
            html_parts.append('            <div class="item">')
            
            # ===== 原推文（如果是引用推文，则显示原推文）=====
            if original_atom:
                # 这是一个引用推文，先显示原推文
                orig_author = original_atom.get("source", {}).get("author", "未知")
                orig_title = original_atom.get("title_zh") or original_atom.get("title", "")
                orig_summary = original_atom.get("summary_zh", "")
                orig_url = original_atom.get("source", {}).get("url", "")
                orig_embedded = original_atom.get("embedded_urls", [])
                
                html_parts.append('                <div class="original-tweet" style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px; border-left: 3px solid #1a1a2e;">')
                html_parts.append('                    <div style="font-size: 12px; color: #666; margin-bottom: 4px;">📌 原推文</div>')
                html_parts.append(f'                    <div class="item-title" style="font-size: 15px;">{escape_html(orig_title)}</div>')
                html_parts.append(f'                    <div class="item-meta" style="margin-top: 6px;">')
                html_parts.append(f'                        <span>@{escape_html(orig_author)}</span>')
                html_parts.append('                    </div>')
                if orig_summary:
                    html_parts.append(f'                    <div class="item-summary" style="margin-top: 6px; font-size: 13px;">{escape_html(orig_summary[:150])}{"..." if len(orig_summary) > 150 else ""}</div>')
                # 收集原推文的链接
                if orig_embedded:
                    all_embedded_urls.extend(orig_embedded)
                html_parts.append('                </div>')
                
                # 标记原推文为已处理
                processed_ids.add(original_atom.get("id"))
            
            # ===== 当前推文（引用/评论）=====
            html_parts.append('                <div class="item-header">')
            html_parts.append(f'                    <div class="trust-badge" style="background: {trust_color}"></div>')
            html_parts.append(f'                    <div class="item-title">{escape_html(title)}</div>')
            html_parts.append("                </div>")
            html_parts.append('                <div class="item-meta">')
            html_parts.append(f'                    <span>@{escape_html(author)}</span>')
            if author_type:
                html_parts.append(f'                    <span>{author_type}</span>')
            if ct_label:
                html_parts.append(f'                    <span>{ct_label}</span>')
            html_parts.append(f'                    <span style="color: {trust_color}">{trust}</span>')
            if platform:
                html_parts.append(f'                    <span>{platform}</span>')
            html_parts.append("                </div>")
            if summary:
                html_parts.append(f'                <div class="item-summary">{escape_html(summary[:200])}{"..." if len(summary) > 200 else ""}</div>')
            
            # 显示微博转发信息
            if is_repost:
                if reposted_from:
                    html_parts.append(f'                <div class="item-link" style="color: #666; font-size: 12px;">🔄 转发自 @{escape_html(reposted_from)}</div>')
                else:
                    html_parts.append(f'                <div class="item-link" style="color: #666; font-size: 12px;">🔄 转发微博</div>')
            
            # 收集引用此推文的其他推文的链接
            if quoting_atoms:
                for qa in quoting_atoms:
                    qa_embedded = qa.get("embedded_urls", [])
                    if qa_embedded:
                        all_embedded_urls.extend(qa_embedded)
                    processed_ids.add(qa.get("id"))
            
            # 去重并显示所有内嵌链接
            unique_urls = list(dict.fromkeys(all_embedded_urls))  # 保持顺序去重
            if unique_urls:
                html_parts.append('                <div class="item-link" style="margin-top: 10px; padding: 8px; background: #f0f7ff; border-radius: 6px;">')
                html_parts.append('                    <span style="color: #0066cc; font-size: 12px; font-weight: 500;">🔗 相关链接:</span>')
                for eurl in unique_urls[:5]:  # 最多显示5个链接
                    display_url = eurl.replace("https://", "").replace("http://", "")
                    html_parts.append(f'                    <a href="{escape_html(eurl)}" target="_blank" style="display: block; margin-left: 8px; font-size: 12px; margin-top: 4px; color: #0066cc;">{escape_html(display_url[:60])}{"..." if len(display_url) > 60 else ""}</a>')
                html_parts.append('                </div>')
            
            if url:
                html_parts.append(f'                <div class="item-link" style="margin-top: 8px;"><a href="{escape_html(url)}" target="_blank" style="color: #666; font-size: 12px;">📝 查看原文 →</a></div>')
            
            html_parts.append("            </div>")
            
            # 标记当前推文为已处理
            processed_ids.add(atom_id)

        html_parts.append("            </div>")
        html_parts.append("        </div>")

    html_parts.append("    </div>")
    html_parts.append("</body>")
    html_parts.append("</html>")

    # 写入文件
    output_dir = V2_ROOT / "preview"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{date}.html"
    output_path.write_text("\n".join(html_parts), encoding="utf-8")

    print(f"✅ HTML 预览已生成: {output_path}")
    return output_path


def escape_html(text: str) -> str:
    """转义 HTML 特殊字符"""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def main():
    parser = argparse.ArgumentParser(description="生成 HTML 预览")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="日期 (YYYY-MM-DD)")
    parser.add_argument("--channel", choices=["x", "weibo", "rss"], help="只预览指定渠道")
    parser.add_argument("--open", action="store_true", help="生成后自动打开浏览器")

    args = parser.parse_args()

    output_path = generate_html(args.date, args.channel)

    if output_path and args.open:
        webbrowser.open(f"file://{output_path}")


if __name__ == "__main__":
    main()
