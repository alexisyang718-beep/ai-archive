#!/usr/bin/env python3
"""
选题报告生成器

功能：
1. 按板块筛选高质量内容（L1/L2优先）
2. 生成选题建议报告
3. 输出为本地 HTML，便于人工筛选

用法：
    python selection_report.py --date 2026-03-23
    python selection_report.py --date 2026-03-23 --output selection.html
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore

V2_ROOT = Path(__file__).parent.parent
REPORTS_DIR = V2_ROOT / "reports"

# 板块配置
CATEGORY_CONFIG = {
    "ai_models": {
        "name": "🤖 AI模型与产品",
        "color": "#e74c3c",
        "icon": "🤖",
        "target": 5,  # 目标选取条数
    },
    "mobile": {
        "name": "📱 手机与消费电子",
        "color": "#3498db",
        "icon": "📱",
        "target": 3,
    },
    "chips": {
        "name": "🔧 芯片与算力",
        "color": "#f39c12",
        "icon": "🔧",
        "target": 3,
    },
    "gaming": {
        "name": "🎮 游戏行业",
        "color": "#9b59b6",
        "icon": "🎮",
        "target": 2,
    },
    "tech_industry": {
        "name": "🏢 科技行业动态",
        "color": "#1abc9c",
        "icon": "🏢",
        "target": 3,
    },
    "policy": {
        "name": "📜 政策与监管",
        "color": "#34495e",
        "icon": "📜",
        "target": 2,
    },
}


def score_atom(atom: Dict) -> int:
    """计算内容得分，用于排序"""
    score = 0
    
    # 信源质量得分
    trust = atom.get("trust_default", "L3")
    if trust == "L1":
        score += 100
    elif trust == "L2":
        score += 50
    
    # 内容类型得分
    content_type = atom.get("content_type", "")
    type_scores = {
        "official": 50,
        "exclusive": 40,
        "firsthand_test": 35,
        "original_analysis": 30,
        "report": 25,
        "interview": 20,
        "commentary": 10,
    }
    score += type_scores.get(content_type, 0)
    
    # 实体数量得分（信息密度）
    entities = atom.get("entities", [])
    score += min(len(entities) * 5, 20)
    
    return score


def select_candidates(atoms: List[Dict], category: str, target: int = 5) -> List[Dict]:
    """从 atoms 中筛选候选内容"""
    # 过滤出该板块的内容
    cat_atoms = [a for a in atoms if a.get("category") == category]
    
    # 按得分排序
    scored = [(a, score_atom(a)) for a in cat_atoms]
    scored.sort(key=lambda x: x[1], reverse=True)
    
    # 返回前 target*2 条作为候选（给人工选择留空间）
    return [a for a, s in scored[:target * 2]]


def generate_html_report(date_str: str, candidates_by_cat: Dict[str, List[Dict]]) -> str:
    """生成 HTML 格式的选题报告"""
    
    # 统计
    total_candidates = sum(len(v) for v in candidates_by_cat.values())
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>选题报告 - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f8f9fa;
            min-height: 100vh;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .header .subtitle {{
            opacity: 0.9;
            font-size: 16px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .stats-bar {{
            display: flex;
            justify-content: center;
            gap: 40px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 36px;
            font-weight: bold;
        }}
        .stat-label {{
            font-size: 14px;
            opacity: 0.8;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 3px solid;
        }}
        .section-icon {{
            font-size: 28px;
        }}
        .section-title {{
            font-size: 22px;
            font-weight: bold;
            color: #2c3e50;
            flex: 1;
        }}
        .section-count {{
            background: #ecf0f1;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 14px;
            color: #7f8c8d;
        }}
        .candidate-list {{
            display: grid;
            gap: 16px;
        }}
        .candidate-card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 4px solid;
            transition: all 0.2s;
            cursor: pointer;
        }}
        .candidate-card:hover {{
            transform: translateX(4px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }}
        .candidate-card.selected {{
            background: #e8f5e9;
            border-left-width: 6px;
        }}
        .candidate-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }}
        .candidate-title {{
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            line-height: 1.5;
            flex: 1;
            margin-right: 12px;
        }}
        .score-badge {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            white-space: nowrap;
        }}
        .candidate-meta {{
            display: flex;
            gap: 12px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }}
        .meta-tag {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
        }}
        .trust-l1 {{ background: #ffebee; color: #c62828; }}
        .trust-l2 {{ background: #fff3e0; color: #ef6c00; }}
        .trust-l3 {{ background: #e8f5e9; color: #2e7d32; }}
        .type-official {{ background: #e3f2fd; color: #1565c0; }}
        .type-exclusive {{ background: #f3e5f5; color: #7b1fa2; }}
        .type-report {{ background: #e0f2f1; color: #00695c; }}
        .type-default {{ background: #f5f5f5; color: #616161; }}
        .candidate-source {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            color: #7f8c8d;
        }}
        .source-link {{
            color: #667eea;
            text-decoration: none;
        }}
        .source-link:hover {{
            text-decoration: underline;
        }}
        .entities {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 10px;
        }}
        .entity-tag {{
            background: #f0f0f0;
            color: #555;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
        }}
        .checkbox-wrapper {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px dashed #ddd;
        }}
        .checkbox-wrapper input[type="checkbox"] {{
            width: 20px;
            height: 20px;
            cursor: pointer;
        }}
        .checkbox-wrapper label {{
            cursor: pointer;
            font-size: 14px;
            color: #555;
        }}
        .actions {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: white;
            padding: 16px 20px;
            box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
            display: flex;
            justify-content: center;
            gap: 16px;
            z-index: 100;
        }}
        .btn {{
            padding: 12px 32px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        .btn-secondary {{
            background: #ecf0f1;
            color: #555;
        }}
        .btn-secondary:hover {{
            background: #e0e0e0;
        }}
        .empty-section {{
            text-align: center;
            padding: 40px;
            color: #95a5a6;
            background: white;
            border-radius: 12px;
        }}
        .timestamp {{
            text-align: center;
            color: #95a5a6;
            font-size: 12px;
            margin: 40px 0 100px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📋 科技资讯日报选题</h1>
        <div class="subtitle">{date_str} | 预筛选候选内容</div>
        <div class="stats-bar">
            <div class="stat-item">
                <div class="stat-value">{total_candidates}</div>
                <div class="stat-label">候选内容</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">6</div>
                <div class="stat-label">板块分类</div>
            </div>
        </div>
    </div>
    
    <div class="container">
"""
    
    for cat_key, config in CATEGORY_CONFIG.items():
        candidates = candidates_by_cat.get(cat_key, [])
        color = config["color"]
        
        html += f"""
        <div class="section">
            <div class="section-header" style="border-color: {color};">
                <span class="section-icon">{config["icon"]}</span>
                <span class="section-title">{config["name"]}</span>
                <span class="section-count">目标 {config["target"]} 条 | 候选 {len(candidates)} 条</span>
            </div>
            <div class="candidate-list">
"""
        
        if not candidates:
            html += f"""
                <div class="empty-section">
                    该板块暂无候选内容
                </div>
"""
        else:
            for i, atom in enumerate(candidates):
                atom_id = atom.get("id", f"unknown_{cat_key}_{i}")
                title = atom.get("title", "")[:150]
                if len(atom.get("title", "")) > 150:
                    title += "..."
                
                source = atom.get("source", {})
                author = source.get("author", "未知")
                platform = source.get("platform", "")
                url = source.get("url", "#")
                
                trust = atom.get("trust_default", "L3")
                trust_class = f"trust-{trust.lower()}"
                trust_label = {"L1": "🔴 L1 一手", "L2": "🟡 L2 可靠", "L3": "🟢 L3 参考"}.get(trust, trust)
                
                content_type = atom.get("content_type", "")
                type_class = f"type-{content_type}" if content_type else "type-default"
                type_label = content_type.replace("_", " ").title() if content_type else "其他"
                
                score = score_atom(atom)
                
                platform_emoji = {"x": "𝕏", "weibo": "📝", "rss": "📰"}.get(platform, "📄")
                
                entities = atom.get("entities", [])[:5]
                entities_html = "".join([f'<span class="entity-tag">{e}</span>' for e in entities])
                
                html += f"""
                <div class="candidate-card" data-id="{atom_id}" style="border-color: {color};">
                    <div class="candidate-header">
                        <div class="candidate-title">{title}</div>
                        <span class="score-badge">得分 {score}</span>
                    </div>
                    <div class="candidate-meta">
                        <span class="meta-tag {trust_class}">{trust_label}</span>
                        <span class="meta-tag {type_class}">{type_label}</span>
                    </div>
                    <div class="candidate-source">
                        <span>{platform_emoji} {author}</span>
                        <a href="{url}" class="source-link" target="_blank">查看原文 →</a>
                    </div>
                    <div class="entities">{entities_html}</div>
                    <div class="checkbox-wrapper">
                        <input type="checkbox" id="sel_{atom_id}" data-atom-id="{atom_id}">
                        <label for="sel_{atom_id}">选中此条进入日报</label>
                    </div>
                </div>
"""
        
        html += """
            </div>
        </div>
"""
    
    html += f"""
        <div class="timestamp">
            报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>
    
    <div class="actions">
        <button class="btn btn-secondary" onclick="window.print()">🖨️ 打印/PDF</button>
        <button class="btn btn-primary" onclick="exportSelection()">📋 导出选中项</button>
    </div>
    
    <script>
        // 导出选中的内容
        function exportSelection() {{
            const selected = [];
            document.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {{
                const card = cb.closest('.candidate-card');
                const title = card.querySelector('.candidate-title').textContent;
                const source = card.querySelector('.source-link').href;
                selected.push({{title, source}});
            }});
            
            if (selected.length === 0) {{
                alert('请先选中至少一条内容');
                return;
            }}
            
            let text = `已选中 ${{selected.length}} 条内容：\\n\\n`;
            selected.forEach((item, i) => {{
                text += `${{i+1}}. ${{item.title}}\\n   ${{item.source}}\\n\\n`;
            }});
            
            navigator.clipboard.writeText(text).then(() => {{
                alert('已复制到剪贴板！');
            }});
        }}
        
        // 点击卡片切换选中状态
        document.querySelectorAll('.candidate-card').forEach(card => {{
            card.addEventListener('click', function(e) {{
                // 如果点击的是链接或复选框，不处理
                if (e.target.tagName === 'A' || e.target.tagName === 'INPUT') return;
                
                const checkbox = this.querySelector('input[type="checkbox"]');
                checkbox.checked = !checkbox.checked;
                this.classList.toggle('selected', checkbox.checked);
            }});
        }});
        
        // 复选框变化时更新样式
        document.querySelectorAll('input[type="checkbox"]').forEach(cb => {{
            cb.addEventListener('change', function() {{
                const card = this.closest('.candidate-card');
                card.classList.toggle('selected', this.checked);
            }});
        }});
    </script>
</body>
</html>"""
    
    return html


def main():
    parser = argparse.ArgumentParser(description="生成选题报告")
    parser.add_argument("--date", required=True, help="日期 (YYYY-MM-DD)")
    parser.add_argument("--output", help="输出文件路径")
    args = parser.parse_args()
    
    # 加载数据
    store = AtomStore()
    atoms = store.query_by_date(args.date)
    
    if not atoms:
        print(f"⚠️ 未找到 {args.date} 的数据")
        # 仍然生成空报告
        candidates_by_cat = {cat: [] for cat in CATEGORY_CONFIG.keys()}
    else:
        print(f"📊 加载了 {len(atoms)} 条 atoms")
        
        # 按板块筛选候选内容
        candidates_by_cat = {}
        for cat_key, config in CATEGORY_CONFIG.items():
            candidates = select_candidates(atoms, cat_key, config["target"])
            candidates_by_cat[cat_key] = candidates
            print(f"  {config['name']}: {len(candidates)} 条候选")
    
    # 生成 HTML 报告
    html = generate_html_report(args.date, candidates_by_cat)
    
    if args.output:
        output_path = Path(args.output)
    else:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = REPORTS_DIR / f"selection_{args.date}.html"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 选题报告已生成: {output_path}")


if __name__ == "__main__":
    main()
