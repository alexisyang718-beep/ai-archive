#!/usr/bin/env python3
"""用48h过滤后的286条重写 atom_store 读取的 channel 文件"""
import json
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(hours=48)
BASE = "/Users/yangliu/Documents/Claude Code/codebuddy/tech-daily-brief"
DATE = "2026-03-20"

fresh_atoms = []
with open(f"{BASE}/v2/archive/daily/{DATE}/weibo.jsonl") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        atom = json.loads(line)
        ts = atom.get("source", {}).get("timestamp", "")
        if ts:
            try:
                dt_utc = datetime.strptime(ts[:19] + "+0000", "%Y-%m-%dT%H:%M:%S%z")
                dt_local = dt_utc.replace(tzinfo=None) - timedelta(hours=8)
                if dt_local < cutoff:
                    continue
            except Exception:
                pass
        atom["id"] = f"atom_{DATE.replace('-','')}_{len(fresh_atoms)+1:03d}"
        fresh_atoms.append(atom)

print(f"重写: {len(fresh_atoms)} 条")

out_path = f"{BASE}/v2/archive/daily/{DATE}_weibo.jsonl"
with open(out_path, "w") as f:
    for a in fresh_atoms:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
print(f"已写入 {out_path}")