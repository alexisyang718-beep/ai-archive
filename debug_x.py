#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, 'scripts')

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

def run_twitter_command(args):
    cmd = ['twitter'] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print(f'错误: {result.stderr}')
        return None
    # 跳过警告行
    lines = result.stdout.strip().split('\n')
    json_start = 0
    for i, line in enumerate(lines):
        if line.startswith('{'):
            json_start = i
            break
    json_str = '\n'.join(lines[json_start:])
    return json.loads(json_str)

def parse_tweet_time(time_str):
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%a %b %d %H:%M:%S +0000 %Y',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(time_str.replace('Z', '+00:00').replace('+00:00', ''))
    except:
        pass
    return None

# 获取数据
print('🔄 获取 X Following 数据...')
result = run_twitter_command(['feed', '-t', 'following', '--max', '200', '--json'])
if not result:
    print('❌ 获取失败')
    sys.exit(1)

tweets = result.get('data', [])
print(f'获取到 {len(tweets)} 条原始推文')

# 检查时间范围
now = datetime.utcnow()
cutoff = now - timedelta(hours=6)
print(f'当前UTC时间: {now}')
print(f'6小时 cutoff: {cutoff}')

valid = 0
for t in tweets[:10]:
    ts = t.get('createdAt')
    if ts:
        dt = parse_tweet_time(ts)
        if dt:
            in_range = dt >= cutoff
            print(f'  {ts} -> {dt} | 在范围内: {in_range}')
            if in_range:
                valid += 1

print(f'\n前10条中在6小时内的: {valid} 条')
