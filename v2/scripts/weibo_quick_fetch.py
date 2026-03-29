#!/usr/bin/env python3
"""
微博快速采集 - 只采集核心用户，避免超时
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore

# 核心用户列表（减少数量避免超时）
CORE_USERS = [
    {"name": "数码闲聊站", "uid": "1892653244"},
    {"name": "华为", "uid": "1836861990"},
    {"name": "小米", "uid": "1748077585"},
    {"name": "OPPO", "uid": "1640296590"},
    {"name": "vivo", "uid": "1804531244"},
    {"name": "荣耀", "uid": "7369078392"},
    {"name": "36氪", "uid": "1750070171"},
    {"name": "虎嗅", "uid": "1913025567"},
]

WEIBO_CMD = str(Path.home() / ".local" / "bin" / "weibo")


def fetch_user_weibos(uid: str, max_results: int = 5):
    """获取用户微博"""
    env = {**os.environ, "PATH": "/Users/yangliu/.local/bin:/usr/local/bin:/usr/bin:/bin"}
    cmd = [WEIBO_CMD, "weibos", uid, "-n", str(max_results), "--json"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, env=env)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("list", [])
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"    ⚠️ 采集失败: {e}")
    return []


def weibo_to_atom(weibo: dict, username: str, date: str) -> dict:
    """转换为Atom格式"""
    content = weibo.get("text_raw", weibo.get("text", ""))
    if not content or len(content) < 10:
        return None
    
    created_at = weibo.get("created_at", "")
    try:
        dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
        created_at = dt.strftime("%Y-%m-%d %H:%M")
    except:
        pass
    
    # 从user对象获取uid
    user_info = weibo.get("user", {})
    uid = user_info.get("id") or user_info.get("idstr", "") or weibo.get("uid", "")
    mid = weibo.get("mid", "")
    
    # 确保uid不是0
    if uid in (0, "0", ""):
        uid = ""
    
    url = f"https://weibo.com/{uid}/{mid}" if uid and mid else f"https://m.weibo.cn/detail/{mid}" if mid else ""
    
    return {
        "id": f"atom_{date.replace('-', '')}_{mid}",
        "date": date,
        "title": content[:100] + "..." if len(content) > 100 else content,
        "title_zh": content[:100] + "..." if len(content) > 100 else content,
        "summary_zh": content,
        "source": {
            "platform": "weibo",
            "author": f"@{username}",
            "author_type": "kol",
            "url": url,
            "timestamp": created_at
        },
        "content_type": "commentary",
        "trust_default": "L2",
        "category": "tech_industry",
        "tags": [],
        "entities": [],
        "in_daily_brief": False,
        "trust_final": None,
        "trust_reason": None,
        "related_atoms": [],
        "full_text_fetched": False,
        "full_text_path": None,
        "metrics": {
            "likes": weibo.get("attitudes_count", 0),
            "retweets": weibo.get("reposts_count", 0),
            "replies": weibo.get("comments_count", 0),
            "views": 0
        },
        "brief_date": None,
        "channel": "weibo"
    }


def collect_weibo(date: str):
    """采集微博"""
    print(f"\n{'='*60}")
    print(f"📡 微博快速采集 - {date}")
    print(f"{'='*60}")
    print(f"核心用户: {len(CORE_USERS)} 个")
    
    all_atoms = []
    
    for user in CORE_USERS:
        print(f"\n  🐦 @{user['name']}...", end=" ", flush=True)
        weibos = fetch_user_weibos(user["uid"], max_results=5)
        
        count = 0
        for wb in weibos:
            atom = weibo_to_atom(wb, user["name"], date)
            if atom:
                all_atoms.append(atom)
                count += 1
        
        print(f"{count} 条")
    
    print(f"\n{'─'*60}")
    print(f"采集完成: {len(all_atoms)} 条")
    
    # 去重
    seen_urls = set()
    unique_atoms = []
    for atom in all_atoms:
        url = atom.get("source", {}).get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_atoms.append(atom)
    
    print(f"去重后: {len(unique_atoms)} 条")
    
    # 保存
    if unique_atoms:
        store = AtomStore()
        ids = store.save_atoms_batch(unique_atoms, channel="weibo")
        print(f"\n💾 已保存 {len(ids)} 条到 weibo.jsonl")
    
    print(f"{'='*60}")
    return unique_atoms


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2026-03-24")
    args = parser.parse_args()
    
    collect_weibo(args.date)
