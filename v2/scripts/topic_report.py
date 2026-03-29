#!/usr/bin/env python3
"""
话题聚类报告生成器

功能：
1. 读取当日所有 atoms
2. 进行话题聚类
3. 生成 HTML 报告展示话题

用法：
    python topic_report.py --date 2026-03-23
    python topic_report.py --date 2026-03-23 --output topics.html
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore

V2_ROOT = Path(__file__).parent.parent
REPORTS_DIR = V2_ROOT / "reports"

# 板块显示名称和颜色
CATEGORY_STYLES = {
    "ai_models": ("🤖 AI模型", "#e74c3c"),
    "mobile": ("📱 手机", "#3498db"),
    "chips": ("🔧 芯片", "#f39c12"),
    "gaming": ("🎮 游戏", "#9b59b6"),
    "tech_industry": ("🏢 行业", "#1abc9c"),
    "policy": ("📜 政策", "#34495e"),
}


@dataclass
class Topic:
    """话题"""
    id: str
    name: str
    atoms: List[Dict]
    main_entities: List[str]
    category: str = ""
    importance: int = 0


class SimpleTopicClusterer:
    """简化版话题聚类器"""
    
    def __init__(self, similarity_threshold: float = 0.5):
        self.similarity_threshold = similarity_threshold
    
    def cluster(self, atoms: List[Dict]) -> List[Topic]:
        """基于实体共现进行聚类"""
        if not atoms:
            return []
        
        # 按实体分组
        entity_to_atoms = defaultdict(list)
        for atom in atoms:
            entities = atom.get("entities", [])
            for entity in entities:
                entity_to_atoms[entity].append(atom)
        
        # 找出高频实体（出现在多个 atoms 中）
        entity_freq = {e: len(a) for e, a in entity_to_atoms.items()}
        significant_entities = {e for e, f in entity_freq.items() if f >= 2}
        
        # 基于实体共现聚类
        assigned = set()
        topics = []
        topic_id = 0
        
        # 按频率排序实体，优先处理高频实体
        sorted_entities = sorted(significant_entities, key=lambda e: entity_freq[e], reverse=True)
        
        for entity in sorted_entities:
            # 获取包含该实体的所有 atoms
            related_atoms = entity_to_atoms[entity]
            
            # 过滤已分配的 atoms
            unassigned = [a for a in related_atoms if id(a) not in assigned]
            
            if len(unassigned) >= 2:  # 至少2条未分配的内容才形成话题
                # 收集这个话题的所有实体
                topic_entities = set()
                for atom in unassigned:
                    topic_entities.update(atom.get("entities", []))
                
                # 找出共同实体（出现在至少一半 atoms 中）
                common_entities = []
                for e in topic_entities:
                    count = sum(1 for a in unassigned if e in a.get("entities", []))
                    if count >= len(unassigned) / 2:
                        common_entities.append(e)
                
                # 生成话题名称
                if common_entities:
                    name = f"{common_entities[0]} 相关"
                else:
                    name = f"{entity} 相关"
                
                # 确定话题板块（取多数 atoms 的板块）
                cat_counter = defaultdict(int)
                for atom in unassigned:
                    cat = atom.get("category", "")
                    if cat:
                        cat_counter[cat] += 1
                main_category = max(cat_counter, key=cat_counter.get) if cat_counter else ""
                
                # 计算重要性（基于 atoms 数量和信源质量）
                importance = len(unassigned)
                for atom in unassigned:
                    if atom.get("trust_default") == "L1":
                        importance += 2
                    elif atom.get("trust_default") == "L2":
                        importance += 1
                
                topic = Topic(
                    id=f"topic_{topic_id:03d}",
                    name=name,
                    atoms=unassigned,
                    main_entities=common_entities[:5],
                    category=main_category,
                    importance=importance
                )
                topics.append(topic)
                topic_id += 1
                
                # 标记为已分配
                for atom in unassigned:
                    assigned.add(id(atom))
        
        # 处理剩余未分配的 atoms（每个作为一个独立话题）
        for atom in atoms:
            if id(atom) not in assigned:
                entities = atom.get("entities", [])
                name = entities[0] if entities else "其他"
                
                topic = Topic(
                    id=f"topic_{topic_id:03d}",
                    name=f"{name} 相关",
                    atoms=[atom],
                    main_entities=entities[:3],
                    category=atom.get("category", ""),
                    importance=1
                )
                topics.append(topic)
                topic_id += 1
                assigned.add(id(atom))
        
        # 按重要性排序
        topics.sort(key=lambda t: t.importance, reverse=True)
        
        return topics


def generate_html_report(date_str: str, topics: List[Topic]) -> str:
    """生成 HTML 格式的话题报告"""
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>话题聚类报告 - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
            font-size: 32px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        .summary {{
            text-align: center;
            color: rgba(255,255,255,0.9);
            margin-bottom: 30px;
            font-size: 16px;
        }}
        .topic-card {{
            background: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .topic-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 15px 50px rgba(0,0,0,0.15);
        }}
        .topic-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
        }}
        .topic-title {{
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
            flex: 1;
        }}
        .topic-meta {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        .category-badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            color: white;
        }}
        .count-badge {{
            background: #ecf0f1;
            color: #7f8c8d;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        .entities {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 16px;
        }}
        .entity-tag {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 13px;
        }}
        .atoms-list {{
            border-top: 1px solid #ecf0f1;
            padding-top: 16px;
        }}
        .atom-item {{
            padding: 12px;
            background: #f8f9fa;
            border-radius: 8px;
            margin-bottom: 10px;
        }}
        .atom-text {{
            color: #2c3e50;
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 8px;
        }}
        .atom-source {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            color: #7f8c8d;
        }}
        .trust-badge {{
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        .trust-l1 {{ background: #ffebee; color: #c62828; }}
        .trust-l2 {{ background: #fff3e0; color: #ef6c00; }}
        .trust-l3 {{ background: #e8f5e9; color: #2e7d32; }}
        .platform-icon {{
            margin-right: 4px;
        }}
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: white;
        }}
        .empty-state h2 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        .timestamp {{
            text-align: center;
            color: rgba(255,255,255,0.7);
            font-size: 12px;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 话题聚类报告</h1>
        <div class="summary">
            {date_str} | 共识别 {len(topics)} 个话题
        </div>
"""
    
    if not topics:
        html += """
        <div class="empty-state">
            <h2>暂无话题数据</h2>
            <p>请检查当日是否有采集数据</p>
        </div>
"""
    else:
        for topic in topics:
            # 获取板块样式
            cat_name, cat_color = CATEGORY_STYLES.get(topic.category, ("其他", "#95a5a6"))
            
            html += f"""
        <div class="topic-card">
            <div class="topic-header">
                <div class="topic-title">{topic.name}</div>
                <div class="topic-meta">
                    <span class="category-badge" style="background: {cat_color};">{cat_name}</span>
                    <span class="count-badge">{len(topic.atoms)} 条</span>
                </div>
            </div>
            <div class="entities">
"""
            for entity in topic.main_entities[:5]:
                html += f'                <span class="entity-tag">{entity}</span>\n'
            
            html += """            </div>
            <div class="atoms-list">
"""
            for atom in topic.atoms[:5]:  # 最多显示5条
                text = atom.get("title", "") or atom.get("summary_zh", "")[:200]
                source = atom.get("source", {})
                author = source.get("author", "未知")
                platform = source.get("platform", "")
                trust = atom.get("trust_default", "L3")
                trust_class = f"trust-{trust.lower()}"
                
                platform_emoji = {"x": "𝕏", "weibo": "📝", "rss": "📰"}.get(platform, "📄")
                
                html += f"""
                <div class="atom-item">
                    <div class="atom-text">{text}</div>
                    <div class="atom-source">
                        <span><span class="platform-icon">{platform_emoji}</span>{author}</span>
                        <span class="trust-badge {trust_class}">{trust}</span>
                    </div>
                </div>
"""
            
            if len(topic.atoms) > 5:
                html += f'                <div style="text-align: center; color: #95a5a6; font-size: 12px; padding: 8px;">还有 {len(topic.atoms) - 5} 条相关内容...</div>\n'
            
            html += """            </div>
        </div>
"""
    
    html += f"""
        <div class="timestamp">
            报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>
</body>
</html>"""
    
    return html


def main():
    parser = argparse.ArgumentParser(description="生成话题聚类报告")
    parser.add_argument("--date", required=True, help="日期 (YYYY-MM-DD)")
    parser.add_argument("--output", help="输出文件路径")
    args = parser.parse_args()
    
    # 加载数据
    store = AtomStore()
    atoms = store.query_by_date(args.date)
    
    if not atoms:
        print(f"⚠️ 未找到 {args.date} 的数据")
        # 仍然生成空报告
        topics = []
    else:
        print(f"📊 加载了 {len(atoms)} 条 atoms")
        
        # 进行话题聚类
        clusterer = SimpleTopicClusterer()
        topics = clusterer.cluster(atoms)
        print(f"🔥 识别出 {len(topics)} 个话题")
    
    # 生成 HTML 报告
    html = generate_html_report(args.date, topics)
    
    if args.output:
        output_path = Path(args.output)
    else:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = REPORTS_DIR / f"topics_{args.date}.html"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 话题报告已生成: {output_path}")


if __name__ == "__main__":
    main()
