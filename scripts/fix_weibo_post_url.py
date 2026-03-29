#!/usr/bin/env python3
"""批量获取微博 mid 并修复帖子链接"""
import json, subprocess, re, os
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import yaml

BASE = Path("/Users/yangliu/Documents/Claude Code/codebuddy/tech-daily-brief/v2/archive/daily")
TODAY = "2026-03-20"

# 读取现有 atoms
atoms = []
with open(BASE / TODAY / "weibo.jsonl") as f:
    for line in f:
        line = line.strip()
        if not line: continue
        atoms.append(json.loads(line))
print(f"读取 {len(atoms)} 条 atoms")

# 读取 uid mapping
with open(BASE.parent.parent.parent / "config" / "weibo_users.yaml") as f:
    cfg = yaml.safe_load(f)
uid_map = {u['name']: u['uid'] for u in cfg['weibo_users'] if u.get('uid')}

# 获取所有 unique 作者
authors = list({a['source']['author'] for a in atoms})
print(f"需要获取 {len(authors)} 个账号的 mid")

def fetch_mids_for_author(author):
    uid = uid_map.get(author, "")
    if not uid:
        return author, uid, []
    cmd = ["weibo", "weibos", str(uid), "-n", "20", "--json"]
    env = {**os.environ, "PATH": "/Users/yangliu/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"}
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
        if r.returncode == 0:
            data = json.loads(r.stdout)
            items = data.get("list", [])
            result = []
            for item in items:
                text_clean = re.sub(r'<[^>]+>', '', item.get('text', ''))[:80].strip()
                result.append({
                    'mid': item.get('mid', ''),
                    'text': text_clean,
                    'created_at': item.get('created_at', ''),
                    'uid': uid
                })
            return author, uid, result
    except Exception as e:
        print(f"  ERROR @{author}: {e}")
    return author, uid, []

# 并行获取 mid（8线程避免限流）
mid_cache = {}
with ThreadPoolExecutor(max_workers=8) as ex:
    futures = {ex.submit(fetch_mids_for_author, author): author for author in authors}
    done = 0
    for future in as_completed(futures):
        author, uid, items = future.result()
        mid_cache[author] = items
        done += 1
        print(f"  [{done}/{len(authors)}] @{author}: {len(items)} mids")

print(f"\n获取完成，开始匹配...")

# 按 author 分组 atoms
from collections import defaultdict
by_author = defaultdict(list)
for atom in atoms:
    by_author[atom['source']['author']].append(atom)

# 重建 atoms，带正确 URL
fixed = 0
new_atoms = []
for author, author_atoms in by_author.items():
    mids = mid_cache.get(author, [])
    if not mids:
        # 兜底：保留原 URL
        for atom in author_atoms:
            atom['id'] = f"atom_{TODAY.replace('-','')}_{len(new_atoms)+1:03d}"
            new_atoms.append(atom)
        continue

    # 建立 text→mid 映射
    text_to_info = {}
    for m in mids:
        key = m['text'][:50]
        if key:
            text_to_info[key] = m

    for atom in author_atoms:
        atom['id'] = f"atom_{TODAY.replace('-','')}_{len(new_atoms)+1:03d}"
        atom_key = atom['title'][:50].strip()
        matched_mid = None
        matched_ts = None
        for key, info in text_to_info.items():
            if atom_key and key and (atom_key.startswith(key[:20]) or key.startswith(atom_key[:20])):
                matched_mid = info['mid']
                matched_ts = info['created_at']
                break
        if matched_mid:
            atom['source']['url'] = f"https://weibo.com/{info['uid']}/{matched_mid}"
            if matched_ts:
                try:
                    dt = datetime.strptime(matched_ts, "%a %b %d %H:%M:%S %z %Y")
                    atom['source']['timestamp'] = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                except:
                    pass
            fixed += 1
        new_atoms.append(atom)

print(f"✅ 修复完成: {len(new_atoms)} 条, 其中 {fixed} 条已更新为帖子级链接")

# 写入正确路径
out_path = BASE / f"{TODAY}_weibo.jsonl"
with open(out_path, "w") as f:
    for a in new_atoms:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
print(f"💾 已写入 {out_path}")

# 同时更新 weibo.jsonl
with open(BASE / TODAY / "weibo.jsonl", "w") as f:
    for a in new_atoms:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
print(f"💾 已同步 weibo.jsonl")