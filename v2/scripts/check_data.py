#!/usr/bin/env python3
"""检查采集数据的时间范围和重复情况"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore

def check_channel(date: str, channel: str):
    """检查指定渠道的数据"""
    store = AtomStore()
    atoms = store.query_by_date_channel(date, channel)
    
    print(f"\n{'='*60}")
    print(f"📊 {channel.upper()} 数据分析 ({date})")
    print(f"{'='*60}")
    print(f"总条数: {len(atoms)}")
    
    if not atoms:
        return
    
    # 时间范围
    timestamps = []
    for a in atoms:
        ts = a.get('source', {}).get('timestamp', '')
        if ts:
            timestamps.append(ts)
    
    if timestamps:
        timestamps.sort()
        print(f"时间范围: {timestamps[0]} ~ {timestamps[-1]}")
    
    # 检查重复URL
    urls = [a.get('source', {}).get('url', '') for a in atoms if a.get('source', {}).get('url')]
    url_counts = Counter(urls)
    duplicates = {url: count for url, count in url_counts.items() if count > 1}
    print(f"重复URL数: {len(duplicates)}")
    
    # 检查重复ID
    ids = [a.get('id', '') for a in atoms if a.get('id')]
    id_counts = Counter(ids)
    dup_ids = {id_: count for id_, count in id_counts.items() if count > 1}
    print(f"重复ID数: {len(dup_ids)}")
    
    # 板块分布
    cats = Counter(a.get('category', 'unknown') for a in atoms)
    print(f"\n板块分布:")
    for cat, count in cats.most_common():
        print(f"  {cat}: {count}")
    
    # 信源分布
    sources = Counter(a.get('source', {}).get('author', 'unknown') for a in atoms)
    print(f"\nTOP 10 信源:")
    for src, count in sources.most_common(10):
        print(f"  {src}: {count}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-03-23")
    parser.add_argument("--channel", default="x", choices=["x", "weibo", "rss"])
    args = parser.parse_args()
    
    check_channel(args.date, args.channel)
