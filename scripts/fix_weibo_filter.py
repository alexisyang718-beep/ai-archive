#!/usr/bin/env python3
"""从已有 raw JSON 过滤 48 小时内帖子，重新生成 weibo.jsonl"""
import json
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(hours=48)
BASE = "/Users/yangliu/Documents/Claude Code/codebuddy/tech-daily-brief"
DATE = "2026-03-20"

with open(f"{BASE}/v2/archive/daily/{DATE}/weibo_raw.json") as f:
    data = json.load(f)

users = data["users"]
atoms = []

for username, weibos in users.items():
    for w in weibos:
        ts_str = w.get("created_at", "")
        if not ts_str:
            continue
        try:
            dt = datetime.strptime(ts_str, "%a %b %d %H:%M:%S %z %Y")
            dt_naive = dt.replace(tzinfo=None)
            if dt_naive < cutoff:
                continue
        except Exception:
            pass

        text = w.get("text", "")
        title = text[:80].strip()

        atom = {
            "id": f"weibo_{DATE.replace('-','')}_{len(atoms)+1:03d}",
            "date": DATE,
            "title": title,
            "title_zh": title,
            "summary_zh": text[:200],
            "source": {
                "platform": "weibo",
                "author": username,
                "author_type": "kol",
                "url": f"https://weibo.com/u/{w.get('user',{}).get('id','')}",
                "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%SZ") if 'dt' in dir() else "",
            },
            "content_type": "report",
            "trust_default": "L3",
            "trust_final": None,
            "trust_reason": None,
            "category": "tech_industry",
            "tags": [],
            "entities": [],
            "metrics": {},
            "in_daily_brief": False,
            "brief_date": None,
            "related_atoms": [],
            "full_text_fetched": False,
            "full_text_path": None,
        }
        atoms.append(atom)

print(f"过滤后: {len(atoms)} 条 (原636条)")

with open(f"{BASE}/v2/archive/daily/{DATE}/weibo.jsonl", "w") as f:
    for a in atoms:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
print("已保存到 weibo.jsonl")