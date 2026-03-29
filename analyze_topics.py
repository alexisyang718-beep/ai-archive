#!/usr/bin/env python3
import json
from pathlib import Path

base_path = Path("v2/archive/daily/2026-03-27")
all_items = []

# X数据
x_path = base_path / "x.jsonl"
if x_path.exists():
    with open(x_path) as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    text = data.get('text', '')
                    author = data.get('author', 'Unknown')
                    all_items.append({'source': f'X:{author}', 'text': text, 'channel': 'X'})
                except:
                    pass

# 微博数据
weibo_path = base_path / "weibo.jsonl"
if weibo_path.exists():
    with open(weibo_path) as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    text = data.get('content', '') or data.get('text', '')
                    author = data.get('user', {}).get('screen_name', 'Unknown') if isinstance(data.get('user'), dict) else 'Unknown'
                    all_items.append({'source': f'微博:{author}', 'text': text, 'channel': '微博'})
                except:
                    pass

# RSS数据
rss_path = base_path / "rss.jsonl"
if rss_path.exists():
    with open(rss_path) as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    title = data.get('title', '')
                    source = data.get('source', 'Unknown')
                    all_items.append({'source': f'RSS:{source}', 'text': title, 'channel': 'RSS'})
                except:
                    pass

print(f"=== 潜在选题分析 (共{len(all_items)}条) ===\n")

categories = {
    '🤖 AI模型与产品': ['AI', 'GPT', 'Claude', 'OpenAI', 'Anthropic', 'Gemini', 'LLM', 'model'],
    '📱 手机与消费电子': ['iPhone', 'Apple', 'Samsung', '手机', 'MacBook', 'iPad'],
    '🔧 芯片与算力': ['芯片', 'NVIDIA', 'GPU', 'AI芯片', '算力', 'Intel', 'AMD'],
    '🎮 游戏行业': ['游戏', 'Switch', 'Nintendo', 'PlayStation', 'Xbox'],
    '🏛️ 科技行业动态': ['收购', 'IPO', '融资', '财报', 'Meta', 'Google', 'Amazon'],
    '📜 政策与监管': ['监管', '政策', '法律', '诉讼', '反垄断']
}

for cat_name, keywords in categories.items():
    matches = []
    for item in all_items:
        text = item['text'].lower()
        if any(kw.lower() in text for kw in keywords):
            matches.append(item)
    
    if matches:
        print(f"{cat_name}: {len(matches)}条")
        for i, m in enumerate(matches[:3]):
            text = m['text'][:70] + '...' if len(m['text']) > 70 else m['text']
            print(f"  {i+1}. [{m['source']}] {text}")
        print()
