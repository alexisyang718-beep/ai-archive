#!/usr/bin/env python3
import json

# 要查找的文章URL
target_urls = [
    ('https://mp.weixin.qq.com/s/1LFk8UU6ospjUgu7Oenorg', 'GB300'),
    ('https://mp.weixin.qq.com/s/5awq6K3xjfdgWtT0n8li8Q', '面壁EdgeClaw'),
    ('https://mp.weixin.qq.com/s/EWiO_RCJgiTqPzquGMVSDg', '阶跃StepClaw'),
    ('https://mp.weixin.qq.com/s/5YVVcFC26W7MlR8_2nc9_Q', 'QQ浏览器AIPPT'),
    ('https://mp.weixin.qq.com/s/yL9YHzyOkgEzL8eVR2K44w', 'GTC对话'),
]

# 检查3月19日和3月20日的数据
for date in ['2026-03-19', '2026-03-20']:
    print(f"\n📅 检查 {date}:")
    found = []
    
    for url, title in target_urls:
        url_short = url.split('/')[-1][:8]
        
        # 检查所有渠道文件
        for channel in ['x', 'rss', 'weibo', 'search']:
            filepath = f'archive/daily/{date}_{channel}.jsonl'
            try:
                with open(filepath, 'r') as f:
                    for line in f:
                        if url_short in line:
                            atom = json.loads(line)
                            if atom.get('source', {}).get('url', '') == url:
                                found.append({
                                    'title': title,
                                    'channel': channel,
                                    'atom_title': atom.get('title', 'N/A')[:40],
                                })
                                break
            except FileNotFoundError:
                pass
    
    if found:
        print('  找到的文章：')
        for f in found:
            print(f"    ✅ [{f['channel']}] {f['title']}")
    else:
        print('  未找到任何文章')
    
    # 检查未找到的文章
    found_titles = {f['title'] for f in found}
    not_found = [t for u, t in target_urls if t not in found_titles]
    if not_found:
        print(f"  未找到: {', '.join(not_found)}")
