#!/usr/bin/env python3
"""分析采集数据的时效性"""
import json, sys
from datetime import datetime
from collections import Counter
from pathlib import Path

date = sys.argv[1] if len(sys.argv) > 1 else "2026-03-24"
base = Path(__file__).resolve().parent.parent / "archive" / "daily" / date

cutoff_24h = datetime(2026, 3, 23, 10, 0)  # 24小时前
cutoff_48h = datetime(2026, 3, 22, 10, 0)  # 48小时前

def parse_ts(ts_str):
    """尝试多种格式解析时间戳"""
    if not ts_str:
        return None
    fmts = [
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M", "%a, %d %b %Y %H:%M:%S"
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(ts_str[:len(fmt.replace('%','x').replace('x','0'))], fmt)
        except:
            continue
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '').split('+')[0])
    except:
        return None

for ch in ['x', 'weibo', 'rss']:
    fpath = base / f"{ch}.jsonl"
    if not fpath.exists():
        print(f"\n===== {ch.upper()} (不存在) =====")
        continue
    
    atoms = []
    with open(fpath) as f:
        for line in f:
            if line.strip():
                atoms.append(json.loads(line))
    
    recent_24h, recent_48h, old, no_time = [], [], [], []
    
    for a in atoms:
        ts = a.get('source', {}).get('timestamp', '')
        dt = parse_ts(ts)
        if dt is None:
            no_time.append(a)
        elif dt >= cutoff_24h:
            recent_24h.append(a)
        elif dt >= cutoff_48h:
            recent_48h.append(a)
        else:
            old.append(a)
    
    print(f"\n{'='*60}")
    print(f"{ch.upper()} ({len(atoms)}条)")
    print(f"{'='*60}")
    print(f"  近24h (3/23 10:00后): {len(recent_24h)}条")
    print(f"  24-48h: {len(recent_48h)}条")
    print(f"  >48h旧数据: {len(old)}条")
    print(f"  无时间戳: {len(no_time)}条")
    
    if old:
        years = Counter([a.get('source',{}).get('timestamp','')[:4] for a in old])
        print(f"  旧数据年份: {dict(years.most_common(10))}")
    
    # 打印近24h的内容
    print(f"\n  --- 近24h内容 ({len(recent_24h)}条) ---")
    for i, a in enumerate(recent_24h[:50]):
        title = a.get('title', '')[:80]
        ts = a.get('source', {}).get('timestamp', '')[:19]
        url = a.get('source', {}).get('url', '')[:80]
        author = a.get('source', {}).get('author', '')[:25]
        section = a.get('section', '')
        print(f"  {i+1}. [{ts}] [{section}] {title}")
        print(f"     作者: {author} | {url}")
    
    # 打印24-48h的内容
    if recent_48h:
        print(f"\n  --- 24-48h内容 ({len(recent_48h)}条) ---")
        for i, a in enumerate(recent_48h[:20]):
            title = a.get('title', '')[:80]
            ts = a.get('source', {}).get('timestamp', '')[:19]
            author = a.get('source', {}).get('author', '')[:25]
            section = a.get('section', '')
            print(f"  {i+1}. [{ts}] [{section}] {title}")
