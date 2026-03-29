#!/usr/bin/env python3
"""提取近24-48h的所有科技相关新闻原文"""
import json, sys
from datetime import datetime
from pathlib import Path

date = "2026-03-24"
base = Path(__file__).resolve().parent.parent / "archive" / "daily" / date

cutoff_24h = datetime(2026, 3, 23, 10, 0)
cutoff_48h = datetime(2026, 3, 22, 10, 0)

def parse_ts(ts_str):
    if not ts_str:
        return None
    fmts = [
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M", "%a, %d %b %Y %H:%M:%S"
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(ts_str[:26], fmt)
        except:
            continue
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '').split('+')[0])
    except:
        return None

all_items = []
for ch in ['x', 'weibo', 'rss']:
    fpath = base / f"{ch}.jsonl"
    if not fpath.exists():
        continue
    with open(fpath) as f:
        for line in f:
            if not line.strip():
                continue
            a = json.loads(line)
            ts = a.get('source', {}).get('timestamp', '')
            dt = parse_ts(ts)
            if dt and dt >= cutoff_48h:
                all_items.append({
                    'channel': ch,
                    'title': a.get('title', ''),
                    'body': a.get('body', ''),
                    'url': a.get('source', {}).get('url', ''),
                    'author': a.get('source', {}).get('author', ''),
                    'timestamp': ts,
                    'dt': dt,
                    'section': a.get('section', ''),
                })

# 按时间排序（新的在前）
all_items.sort(key=lambda x: x['dt'], reverse=True)

print(f"近48h内共 {len(all_items)} 条\n")

for i, item in enumerate(all_items):
    age = "24h内" if item['dt'] >= cutoff_24h else "24-48h"
    print(f"{'='*80}")
    print(f"[{i+1}] [{item['channel'].upper()}] [{age}] {item['timestamp'][:19]}")
    print(f"作者: {item['author']}")
    print(f"标题: {item['title'][:120]}")
    print(f"正文: {item['body'][:300]}")
    print(f"URL: {item['url']}")
    print()
