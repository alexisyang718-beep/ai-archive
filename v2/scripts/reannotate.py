#!/usr/bin/env python3
"""
重新标注已有数据的分类
用于测试分类规则修复效果
"""

import json
import sys
from pathlib import Path

# 添加scripts目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from collector import RuleBasedAnnotator, AUTHOR_LEARNER_AVAILABLE
if AUTHOR_LEARNER_AVAILABLE:
    from author_learner import get_learner

def reannotate_jsonl(date: str, channel: str):
    """重新标注JSONL文件中的分类"""
    archive_dir = Path(__file__).parent.parent / "archive" / "daily" / date
    jsonl_path = archive_dir / f"{channel}.jsonl"
    
    if not jsonl_path.exists():
        print(f"❌ 文件不存在: {jsonl_path}")
        return
    
    annotator = RuleBasedAnnotator()
    learner = get_learner() if AUTHOR_LEARNER_AVAILABLE else None
    
    # 读取所有记录
    atoms = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    atoms.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    print(f"📊 重新标注 {channel} 渠道 {len(atoms)} 条记录...")
    if learner:
        print(f"   已学习作者: {len(learner.learned_authors)} 个")
    
    # 统计原分类
    from collections import Counter
    old_categories = Counter(a.get('category', 'other') for a in atoms)
    print(f"\n原分类分布:")
    for cat, count in old_categories.most_common():
        print(f"  {cat}: {count}")
    
    # 重新标注
    new_categories = Counter()
    changes = []
    
    for atom in atoms:
        old_cat = atom.get('category', 'other')
        
        # 获取文本和作者
        text = atom.get('title', '') + ' ' + atom.get('summary_zh', '')
        author = atom.get('source', {}).get('author', '').replace('@', '')
        
        # 重新标注（使用学习器增强）
        annotation = annotator.annotate(text, author)
        new_cat = annotation['category']
        
        # 如果规则标注为other，尝试使用学习器的映射
        if new_cat == 'other' and learner:
            learned_cat = learner.get_author_category(author)
            if learned_cat:
                new_cat = learned_cat
        
        new_categories[new_cat] += 1
        
        if old_cat != new_cat:
            changes.append({
                'id': atom.get('id'),
                'author': author,
                'old': old_cat,
                'new': new_cat,
                'title': atom.get('title', '')[:60]
            })
    
    print(f"\n新分类分布:")
    for cat, count in new_categories.most_common():
        pct = count / len(atoms) * 100
        print(f"  {cat}: {count} ({pct:.1f}%)")
    
    print(f"\n分类变化: {len(changes)} 条")
    if changes:
        print("\n部分变化示例:")
        for c in changes[:15]:
            print(f"  {c['author']}: {c['old']} → {c['new']} | {c['title'][:40]}...")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-03-23")
    parser.add_argument("--channel", default="x")
    args = parser.parse_args()
    
    reannotate_jsonl(args.date, args.channel)
