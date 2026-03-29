#!/usr/bin/env python3
"""查看今日全量 Atom 按板块分布"""
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore

store = AtomStore()
atoms = store.query_by_date('2026-03-19')
print(f'总量: {len(atoms)} 条')

cats = Counter(a.get('category','other') for a in atoms)
print(f'板块分布:')
for cat, count in cats.most_common():
    print(f'  {cat}: {count}')

by_cat = {}
for a in atoms:
    cat = a.get('category','other')
    if cat not in by_cat:
        by_cat[cat] = []
    title = (a.get('title_zh') or a.get('title',''))[:80]
    trust = a.get('trust_default','L3')
    author = a.get('source',{}).get('author','')
    by_cat[cat].append((title, trust, author))

for cat in ['gaming','tech_industry','policy','mobile','chips','ai_models']:
    items = by_cat.get(cat, [])
    print(f'\n=== {cat} ({len(items)} 条) ===')
    for i, (t, trust, auth) in enumerate(items[:25], 1):
        print(f'  {i}. [{trust}] {t} — {auth}')
