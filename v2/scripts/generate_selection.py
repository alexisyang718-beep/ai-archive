#!/usr/bin/env python3
"""
生成3月20日科技资讯日报选题
从 v2/archive/daily/2026-03-20/*.jsonl 读取 atoms，按6大模块分类选择
"""

import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# 模块映射：category → 模块名
CATEGORY_MAP = {
    'ai_models': '🤖AI模型与产品',
    'mobile': '📱手机与消费电子',
    'chips': '🔧芯片与算力',
    'gaming': '🎮游戏行业',
    'tech_industry': '🏢科技行业动态',
    'policy': '📜政策与监管',
}

# 板块优先级（用于排序）
CATEGORY_ORDER = ['ai_models', 'mobile', 'chips', 'gaming', 'tech_industry', 'policy']

def load_atoms(date):
    """加载指定日期的所有 atoms"""
    atoms = []
    base = Path('v2/archive/daily')
    for channel in ['x', 'weibo', 'rss']:
        file = base / f'{date}_{channel}.jsonl'
        if file.exists():
            with open(file) as f:
                for line in f:
                    try:
                        atom = json.loads(line)
                        atom['channel'] = channel
                        atoms.append(atom)
                    except:
                        pass
    return atoms

def get_source_info(atom):
    """获取来源信息"""
    source = atom.get('source', {})
    if isinstance(source, dict):
        author = source.get('author', '')
        platform = source.get('platform', '')
        if author:
            return f"{author} ({platform})" if platform else author
        return platform.capitalize() if platform else '未知'
    return str(source) if source else '未知'

def get_url(atom):
    """获取 URL，兼容不同存储格式"""
    url = atom.get('url', '')
    if url and url.startswith('http'):
        return url
    source = atom.get('source', {})
    if isinstance(source, dict):
        url = source.get('url', '')
        if url and url.startswith('http'):
            return url
    return ''

def format_atom_for_selection(atom, idx):
    """格式化单个 atom 为选题条目"""
    title = atom.get('title', '')[:100]
    if not title or 'Test ' in title:
        return None

    url = get_url(atom)
    category = atom.get('category', 'other')
    trust = atom.get('trust_default', 'L3')
    channel = atom.get('channel', '')
    summary = atom.get('summary_zh', atom.get('summary', ''))[:200]
    author = get_source_info(atom)

    # 构建来源字符串
    source_str = f"{author}" if author else "X/Twitter"

    lines = [
        f"### {'✅' if idx <= 5 else '备选'}. {idx}. {title}",
        f"- **来源**: {source_str}",
    ]

    if url:
        lines.append(f"- **URL**: {url}")

    if summary and len(summary) > 10:
        lines.append(f"- **核心内容**: {summary}")

    # 入选理由（基于 trust 和 category）
    reason = get_selection_reason(atom)
    lines.append(f"- **入选理由**: {reason}")

    return '\n'.join(lines)

def get_selection_reason(atom):
    """生成入选理由"""
    category = atom.get('category', '')
    trust = atom.get('trust_default', 'L3')
    channel = atom.get('channel', '')

    reasons = {
        'ai_models': {
            'L1': 'L1权威一手，AI模型重大发布',
            'L2': '重要AI产品/模型更新',
            'L3': 'AI技术进展，值得关注',
        },
        'mobile': {
            'L1': 'L1权威一手，手机行业重大发布',
            'L2': '重要手机/消费电子新品',
            'L3': '手机行业动态',
        },
        'chips': {
            'L1': 'L1权威一手，芯片行业重大发布',
            'L2': '重要芯片/算力进展',
            'L3': '芯片行业动态',
        },
        'gaming': {
            'L1': 'L1权威一手，游戏行业重大发布',
            'L2': '重要游戏/主机新闻',
            'L3': '游戏行业动态',
        },
        'tech_industry': {
            'L1': 'L1权威一手，科技行业重大新闻',
            'L2': '重要科技行业动态',
            'L3': '科技行业动态',
        },
        'policy': {
            'L1': 'L1权威一手，政策监管重要发布',
            'L2': '重要政策/监管动态',
            'L3': '政策与监管动态',
        },
    }

    cat_reasons = reasons.get(category, reasons['tech_industry'])
    return cat_reasons.get(trust, '值得关注的信息')

def generate_selection(date, output_path):
    """生成选题报告"""
    atoms = load_atoms(date)

    print(f"加载 {len(atoms)} 条 atoms")

    # 按 category 分组
    by_category = defaultdict(list)
    for atom in atoms:
        cat = atom.get('category', 'other')
        if cat == 'software_dev':
            cat = 'tech_industry'  # 归入科技行业
        by_category[cat].append(atom)

    # 统计
    stats = {cat: len(atoms) for cat, atoms in by_category.items()}
    total = sum(stats.values())

    # 构建报告内容
    lines = [
        f"# {date} 科技资讯日报选题",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> 数据来源: v2/archive/daily/{date} 全渠道数据",
        f"> 预选题总数: {total}条",
        "> 规则: 每模块前5条 ✅ 标记为日报入选，其余为备选",
        "",
        "---",
        "",
    ]

    # 按模块顺序输出
    selected_count = 0
    for cat in CATEGORY_ORDER:
        cat_atoms = by_category.get(cat, [])
        if not cat_atoms:
            continue

        # 按 trust 排序（L1 > L2 > L3），然后按 channel
        def sort_key(a):
            trust = a.get('trust_default', 'L3')
            trust_order = {'L1': 0, 'L2': 1, 'L3': 2}.get(trust, 3)
            channel_order = {'x': 0, 'rss': 1, 'weibo': 2}.get(a.get('channel', ''), 3)
            return (trust_order, channel_order)

        cat_atoms.sort(key=sort_key)

        module_name = CATEGORY_MAP.get(cat, cat)
        lines.append(f"## {module_name} ({len(cat_atoms)}条)")
        lines.append("")

        for i, atom in enumerate(cat_atoms[:10], 1):  # 每模块最多10条备选
            formatted = format_atom_for_selection(atom, i)
            if formatted:
                lines.append(formatted)
                lines.append("")
                if i <= 5:
                    selected_count += 1

        lines.append("")

    # 底部统计
    lines.extend([
        "---",
        "",
        "## 选题统计",
        "",
        "| 模块 | 条数 |",
        "|------|------|",
    ])

    for cat in CATEGORY_ORDER:
        cnt = stats.get(cat, 0)
        if cnt > 0:
            name = CATEGORY_MAP.get(cat, cat)
            lines.append(f"| {name} | {cnt} |")

    lines.extend([
        "",
        f"**合计**: {total} 条预选，{selected_count} 条入选日报",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ])

    content = '\n'.join(lines)

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"生成选题报告: {output_path}")
    print(f"总计 {total} 条预选，{selected_count} 条入选")
    return content


if __name__ == '__main__':
    date = '2026-03-20'
    output = Path('v2/docs/daily_selection_20260320_v2.md')
    generate_selection(date, output)