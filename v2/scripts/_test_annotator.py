"""测试改进后的分类器在已有数据上的表现"""
import json, sys
sys.path.insert(0, 'v2/scripts')
from collector import RuleBasedAnnotator

a = RuleBasedAnnotator()
with open('v2/archive/daily/2026-03-18.jsonl') as f:
    atoms = [json.loads(l) for l in f if l.strip()]

old_others = [x for x in atoms if x.get('category') == 'other']
print(f'原始 other: {len(old_others)}/{len(atoms)} 条')

new_cats = {}
still_other = 0
reclassified = 0
for item in old_others:
    text = item['title'] + ' ' + item.get('summary_zh', '')
    result = a.annotate(text, item.get('source',{}).get('author',''))
    cat = result['category']
    new_cats[cat] = new_cats.get(cat, 0) + 1
    if cat == 'other':
        still_other += 1
    else:
        reclassified += 1
        if reclassified <= 12:
            print(f'  ✅ {cat}: [{item["source"]["author"]}] {item["title"][:55]}')

print(f'\n重分类: {reclassified} 条')
print(f'仍为 other: {still_other} 条')
print(f'新分类分布: {json.dumps(new_cats, ensure_ascii=False)}')
pct_new = still_other / len(atoms) * 100
pct_old = len(old_others) / len(atoms) * 100
print(f'\nother 占比: {pct_new:.0f}%（之前 {pct_old:.0f}%）')
