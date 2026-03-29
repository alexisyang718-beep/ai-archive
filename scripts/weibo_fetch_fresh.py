#!/usr/bin/env python3
"""串行爬取微博 → Atom JSONL（限流友好版）"""
import json, os, sys, argparse, re
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import yaml

BASE_DIR = Path(__file__).parent.parent / "v2" / "archive"
TODAY = "2026-03-20"

def get_weibo_cli_path():
    p = Path.home() / ".local" / "bin" / "weibo"
    return str(p) if p.exists() else "weibo"

def load_users():
    with open(Path(__file__).parent.parent / "config" / "weibo_users.yaml") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("weibo_users", [])

def fetch_one(uid, name, max_n=5):
    cmd = [get_weibo_cli_path(), "weibos", str(uid), "-n", str(max_n), "--json"]
    env = {**os.environ, "PATH": "/Users/yangliu/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"}
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
        if r.returncode == 0:
            data = json.loads(r.stdout)
            items = data.get("list", [])
            if items:
                return name, uid, items
    except Exception:
        pass
    return name, uid, []

def main():
    users = load_users()
    cutoff = datetime.now() - timedelta(hours=48)
    atoms = []
    fresh_total = 0
    raw_users = {}

    for u in users:
        uid = u.get("uid", "")
        name = u["name"]
        if not uid:
            print(f"  ⏭ {name}: 无UID")
            continue

        name, uid, items = fetch_one(uid, name, max_n=20)
        raw_users[name] = items

        fresh = 0
        for w in items:
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
            title = re.sub(r'<[^>]+>', '', text)[:80].strip()

            atom = {
                "id": f"weibo_{TODAY.replace('-','')}_{len(atoms)+1:03d}",
                "date": TODAY,
                "title": title,
                "title_zh": title,
                "summary_zh": re.sub(r'<[^>]+>', '', text)[:200],
                "source": {
                    "platform": "weibo",
                    "author": name,
                    "author_type": "kol",
                    "url": f"https://weibo.com/{uid}/{w.get('mid', '')}",
                    "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%SZ") if 'dt' in dir() else "",
                },
                "content_type": "report",
                "trust_default": "L3",
                "trust_final": None,
                "trust_reason": None,
                "category": "tech_industry",
                "tags": [],
                "entities": [],
                "metrics": {"likes": w.get("attitudes_count", 0)},
                "in_daily_brief": False,
                "brief_date": None,
                "related_atoms": [],
                "full_text_fetched": False,
                "full_text_path": None,
            }
            atoms.append(atom)
            fresh += 1

        print(f"  [{name}] 获取{items.__len__()}条, 48h内{fresh}条")
        fresh_total += fresh

    print(f"\n✅ 共 {len(raw_users)} 个账号, {fresh_total} 条在48h内 → 生成 {len(atoms)} Atoms")

    daily_dir = Path(__file__).parent.parent / "v2" / "archive" / "daily" / TODAY
    daily_dir.mkdir(parents=True, exist_ok=True)

    # 保存 atom JSONL
    with open(daily_dir / "weibo.jsonl", "w") as f:
        for a in atoms:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")

    # 保存 raw JSON（方便下次直接过滤）
    with open(daily_dir / "weibo_raw.json", "w") as f:
        json.dump({"date": TODAY, "users": raw_users}, f, ensure_ascii=False, indent=2)

    print(f"💾 已保存到 {daily_dir}")

if __name__ == "__main__":
    sys.exit(main())