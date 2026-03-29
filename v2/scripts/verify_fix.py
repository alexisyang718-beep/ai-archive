#!/usr/bin/env python3
"""验证分类修复效果"""

import sys
sys.path.insert(0, '.')
from collector import RuleBasedAnnotator, AUTHOR_LEARNER_AVAILABLE
if AUTHOR_LEARNER_AVAILABLE:
    from author_learner import get_learner
import json
from collections import Counter
from pathlib import Path

def verify_fix(date: str, channel: str):
    annotator = RuleBasedAnnotator()
    learner = get_learner() if AUTHOR_LEARNER_AVAILABLE else None
    
    jsonl_path = Path(__file__).parent.parent / "archive" / "daily" / date / f"{channel}.jsonl"
    
    atoms = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            try:
                atoms.append(json.loads(line))
            except:
                pass
    
    new_cats = []
    for atom in atoms:
        text = atom.get('title', '') + ' ' + atom.get('summary_zh', '')
        author = atom.get('source', {}).get('author', '').replace('@', '')
        
        annotation = annotator.annotate(text, author)
        cat = annotation['category']
        
        if cat == 'other' and learner:
            learned_cat = learner.get_author_category(author)
            if learned_cat:
                cat = learned_cat
        
        new_cats.append(cat)
    
    counts = Counter(new_cats)
    print(f'修复后的分类分布 ({channel}):')
    for cat, count in counts.most_common():
        pct = count / len(atoms) * 100
        bar = '█' * int(pct / 3)
        print(f'  {cat:20s} {count:4d} ({pct:5.1f}%) {bar}')
    
    other_pct = counts.get('other', 0) / len(atoms) * 100
    print(f'\nother占比: {other_pct:.1f}% (目标<40%)')
    
    if other_pct < 40:
        print('✅ 分类健康')
    else:
        print('⚠️ 建议运行: python collector.py --learn')

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-03-23")
    parser.add_argument("--channel", default="x")
    args = parser.parse_args()
    
    verify_fix(args.date, args.channel)
