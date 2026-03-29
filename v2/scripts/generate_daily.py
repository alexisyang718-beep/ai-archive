#!/usr/bin/env python3
"""从 Atom 存储生成日报 HTML"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore

# 读取模板
TEMPLATE_PATH = Path(__file__).parent.parent.parent / "template.html"
OUTPUT_PATH = Path(__file__).parent.parent.parent / "brief" / "2026-03-19.html"

def get_atoms_by_category(date_str: str) -> dict:
    """获取指定日期的所有 atoms，按板块分类"""
    store = AtomStore()
    atoms = store.query_by_date(date_str)
    
    by_cat = {}
    for a in atoms:
        cat = a.get('category', 'other')
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(a)
    
    return by_cat

def format_item(atom: dict) -> str:
    """格式化单条新闻为 HTML"""
    title = atom.get('title_zh') or atom.get('title', '')
    url = atom.get('url', '')
    source = atom.get('source', {})
    author = source.get('author', '') if isinstance(source, dict) else str(source)
    summary = atom.get('summary_zh') or atom.get('summary', '') or ''
    trust = atom.get('trust_default', 'L3')
    
    # 生成标签
    tag_map = {
        'L1': ('tag-hot', '热点'),
        'L2': ('tag-new', '重要'),
        'L3': ('tag-blue', '关注'),
    }
    tag_class, tag_text = tag_map.get(trust, ('tag-blue', '关注'))
    
    # 构建 HTML
    html = f'''<div class="item">
  <div class="item-title">
    <span class="tag {tag_class}">{tag_text}</span>
    {title}
  </div>
  <div class="item-body">
    {summary[:500] if summary else '暂无摘要'}
  </div>
  <div class="item-source">来源：<a href="{url}">{author}</a></div>
</div>'''
    return html

def main():
    date_str = '2026-03-19'
    
    # 获取数据
    by_cat = get_atoms_by_category(date_str)
    
    # 读取模板
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 生成各板块内容
    sections = {
        'model': 'ai_models',
        'phone': 'mobile', 
        'chip': 'chips',
        'game': 'gaming',
        'industry': 'tech_industry',
        'policy': 'policy'
    }
    
    result = template
    
    # 替换日期
    result = result.replace('{{DATE_TITLE}}', '2026年3月19日')
    result = result.replace('{{DATE_CN}}', '2026年3月19日')
    result = result.replace('{{WEEKDAY}}', '周四')
    result = result.replace('{{COVERAGE_RANGE}}', '3月17日-19日')
    
    # 生成核心洞察
    summary = '''❶ <strong>Anthropic 发布迄今最大规模 AI 用户调研</strong>，覆盖 80,508 名用户、159 国、70 种语言<br>
❷ <strong>华为公开自研 CIS 传感器</strong>，实现芯片+OS+AI+Sensor 全栈自研里程碑<br>
❸ <strong>阿里云、百度云同日宣布涨价</strong>，最高涨 34%，云服务价格转折点<br>
❹ <strong>美光 HBM4 量产</strong>，带宽达 2.8 TB/s，专为 NVIDIA Vera Rubin 设计<br>
❺ <strong>《光与影：33号远征队》获 GDCA 年度游戏</strong>，独立游戏逆势崛起<br>
❻ <strong>2026 超级 IPO 年</strong>：SpaceX+OpenAI+Anthropic 合计估值 2.4 万亿美元<br>
❼ <strong>GDC 2026 参展人数骤降 30%</strong>，游戏行业寒冬缩影'''
    result = result.replace('{{SUMMARY}}', summary)
    
    # 生成各板块
    for section_key, cat_key in sections.items():
        items = by_cat.get(cat_key, [])
        html_items = [format_item(a) for a in items[:10]]  # 每板块最多10条
        result = result.replace(f'{{{{SECTION_{section_key.upper()}_ITEMS}}}}', '\n'.join(html_items))
    
    # 信源列表
    sources = '<strong>X/Twitter</strong> · <strong>Weibo</strong> · <strong>RSS</strong> · Tavily · 手动补充'
    result = result.replace('{{SOURCES_LIST}}', sources)
    
    # 写入文件
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(result)
    
    print(f'✅ 日报已生成: {OUTPUT_PATH}')
    print(f'   总计: {sum(len(v) for v in by_cat.values())} 条')
    for cat, items in by_cat.items():
        if items:
            print(f'   {cat}: {len(items)} 条')

if __name__ == '__main__':
    main()
