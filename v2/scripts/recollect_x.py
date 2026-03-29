#!/usr/bin/env python3
"""
重新采集X数据 - 分批次采集并过滤时间范围

使用方式：
    python3 recollect_x.py --date 2026-03-23 --start-time "2026-03-23 10:00"
"""

import json
import sys
import os
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore, create_atom

# 环境变量
PATH_ENV = os.environ.get(
    "COLLECTOR_PATH",
    os.path.expanduser("~/.local/bin") + ":/Library/Frameworks/Python.framework/Versions/3.13/bin:/usr/local/bin:/usr/bin:/bin"
)

PROJECT_ROOT = Path(__file__).parent.parent.parent
V2_ROOT = Path(__file__).parent.parent


def parse_twitter_timestamp(ts_str: str) -> datetime:
    """解析twitter时间戳"""
    if not ts_str:
        return datetime.min
    try:
        # 尝试多种格式
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%a %b %d %H:%M:%S %z %Y",  # Twitter标准格式
        ]
        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt)
            except:
                continue
        # 尝试从字符串提取
        if "T" in ts_str:
            ts_str = ts_str.replace("T", " ")[:16]
            return datetime.strptime(ts_str, "%Y-%m-%d %H:%M")
    except:
        pass
    return datetime.min


def fetch_following_batch(max_tweets: int = 50) -> List[Dict]:
    """获取一批Following时间线数据"""
    env = os.environ.copy()
    env["PATH"] = PATH_ENV + ":" + env.get("PATH", "")
    
    try:
        print(f"    🐦 调用 twitter-cli (max={max_tweets})...", flush=True)
        result = subprocess.run(
            ["twitter", "feed", "-t", "following", "--max", str(max_tweets), "--json"],
            capture_output=True, text=True, timeout=60, env=env
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            print(f"    ⚠️ twitter-cli 错误: {error_msg[:100]}")
            return []
        
        tweets = json.loads(result.stdout)
        if isinstance(tweets, dict) and "data" in tweets:
            tweets = tweets["data"]
        
        tweets = tweets if isinstance(tweets, list) else []
        print(f"    ✅ 获取 {len(tweets)} 条原始推文")
        return tweets
        
    except subprocess.TimeoutExpired:
        print("    ⚠️ twitter-cli 超时(60s)")
        return []
    except json.JSONDecodeError as e:
        print(f"    ⚠️ JSON解析错误: {e}")
        return []
    except Exception as e:
        print(f"    ⚠️ 未知错误: {e}")
        return []


def tweet_to_atom(tweet: Dict, date: str) -> Optional[Dict]:
    """将推文转换为Atom格式（简化版）"""
    text = tweet.get("text", "")
    screen_name = tweet.get("author", {}).get("screenName", "unknown")
    tweet_id = tweet.get("id", "")
    created_at = tweet.get("createdAtLocal", "")
    
    if not text or len(text.strip()) < 10:
        return None
    
    # 跳过纯转发
    if tweet.get("isRetweet", False):
        return None
    
    # 构建URL
    url = f"https://x.com/{screen_name}/status/{tweet_id}"
    
    # 提取引用推文
    quoted = tweet.get("quotedTweet")
    quotes_tweet = None
    if quoted and isinstance(quoted, dict):
        quoted_id = quoted.get("id")
        quoted_author = quoted.get("author", {}).get("screenName", "")
        if quoted_id and quoted_author:
            quotes_tweet = f"https://x.com/{quoted_author}/status/{quoted_id}"
    
    # 提取metrics
    metrics = tweet.get("metrics", {})
    
    atom = {
        "id": f"atom_{date.replace('-', '')}_{tweet_id}",
        "date": date,
        "title": text[:200] if len(text) > 200 else text,
        "title_zh": text[:200] if len(text) > 200 else text,
        "summary_zh": text,
        "source": {
            "platform": "x",
            "author": f"@{screen_name}",
            "author_type": "kol",  # 简化处理
            "url": url,
            "timestamp": created_at
        },
        "content_type": "commentary",
        "trust_default": "L2",
        "category": "other",  # 后续会重新分类
        "tags": [],
        "entities": [],
        "in_daily_brief": False,
        "trust_final": None,
        "trust_reason": None,
        "related_atoms": [],
        "full_text_fetched": False,
        "full_text_path": None,
        "metrics": {
            "likes": metrics.get("likes", 0),
            "retweets": metrics.get("retweets", 0),
            "replies": metrics.get("replies", 0),
            "views": metrics.get("views", 0)
        },
        "quotes_tweet": quotes_tweet,
        "brief_date": None,
        "channel": "x"
    }
    
    return atom


def backup_and_clear_x_data(date: str):
    """备份并清空X数据"""
    date_path = V2_ROOT / "archive" / "daily" / date
    x_file = date_path / "x.jsonl"
    
    if x_file.exists():
        # 备份
        backup_dir = V2_ROOT / "archive" / "backup" / date
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / f"x_{datetime.now().strftime('%H%M%S')}.jsonl"
        shutil.copy2(x_file, backup_file)
        print(f"  📦 已备份到: {backup_file}")
        print(f"  🗑️  清空原数据: {x_file}")
        
        # 清空（保留文件）
        with open(x_file, 'w') as f:
            pass
        return True
    return False


def recollect_x(date: str, start_time_str: str, batch_size: int = 50):
    """
    重新采集X数据
    
    Args:
        date: 日期 YYYY-MM-DD
        start_time_str: 开始时间 "YYYY-MM-DD HH:MM"
        batch_size: 每批采集数量
    """
    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
    print(f"\n{'='*60}")
    print(f"🔄 重新采集X数据")
    print(f"{'='*60}")
    print(f"日期: {date}")
    print(f"时间范围: {start_time_str} 至今 (北京时间)")
    print(f"批次大小: {batch_size}")
    
    # 备份并清空
    backup_and_clear_x_data(date)
    
    # 分批次采集
    all_atoms = []
    batch_num = 0
    max_batches = 20  # 最多20批
    consecutive_empty = 0  # 连续空批次计数
    
    print(f"\n{'─'*60}")
    print("开始分批次采集...")
    
    while batch_num < max_batches and consecutive_empty < 3:
        batch_num += 1
        print(f"\n  📡 第 {batch_num} 批采集...")
        
        tweets = fetch_following_batch(batch_size)
        
        if not tweets:
            consecutive_empty += 1
            print(f"    ⚠️ 第 {consecutive_empty} 次空数据")
            continue
        
        consecutive_empty = 0  # 重置
        
        # 转换并过滤时间
        batch_atoms = []
        batch_too_old = 0
        for tweet in tweets:
            atom = tweet_to_atom(tweet, date)
            if atom:
                # 检查时间
                ts_str = atom.get("source", {}).get("timestamp", "")
                tweet_time = parse_twitter_timestamp(ts_str)
                
                if tweet_time >= start_time:
                    batch_atoms.append(atom)
                else:
                    batch_too_old += 1
        
        print(f"    ✅ 本批有效: {len(batch_atoms)} 条, 过滤旧数据: {batch_too_old} 条")
        all_atoms.extend(batch_atoms)
        
        # 如果这批大部分都太旧了，可能是时间线到头了
        if batch_too_old > len(tweets) * 0.8:
            print(f"    ⏹️  大部分数据早于 {start_time_str}，停止采集")
            break
    
    print(f"\n{'─'*60}")
    print(f"采集完成，共 {len(all_atoms)} 条")
    
    # 去重（按URL）
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
        ids = store.save_atoms_batch(unique_atoms, channel="x")
        print(f"\n  💾 已保存 {len(ids)} 条到 x.jsonl")
    
    # 打印统计
    print(f"\n{'='*60}")
    print("采集统计:")
    print(f"  总采集: {len(all_atoms)} 条")
    print(f"  去重后: {len(unique_atoms)} 条")
    print(f"  批次: {batch_num}")
    print(f"{'='*60}")
    
    return unique_atoms


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="重新采集X数据")
    parser.add_argument("--date", default="2026-03-23", help="日期 YYYY-MM-DD")
    parser.add_argument("--start-time", default="2026-03-23 10:00", help="开始时间")
    parser.add_argument("--batch-size", type=int, default=100, help="每批数量")
    args = parser.parse_args()
    
    recollect_x(args.date, args.start_time, args.batch_size)
