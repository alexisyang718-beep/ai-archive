import re
with open('brief/2026-03-19.html', 'r') as f:
    content = f.read()

bodies = re.findall(r'<div class="item-body">(.*?)</div>', content, re.DOTALL)
insights = re.findall(r'<div class="insight-content">(.*?)</div>', content, re.DOTALL)
titles = re.findall(r'<div class="item-title">\s*<span class="tag[^"]*">[^<]+</span>\s*(.*?)\s*</div>', content, re.DOTALL)

def strip_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

print('=== 正文字数 (上限 400 字) ===')
for i, body in enumerate(bodies):
    clean = strip_html(body)
    chars = len(clean)
    title_clean = strip_html(titles[i]) if i < len(titles) else f'Item {i}'
    status = '❌ 超标' if chars > 400 else '✅'
    print(f'{i+1}. [{chars}字] {status} {title_clean[:50]}')

print()
print('=== 洞察字数 (上限 300 字) ===')
for i, insight in enumerate(insights):
    clean = strip_html(insight)
    chars = len(clean)
    title_clean = strip_html(titles[i]) if i < len(titles) else f'Item {i}'
    status = '❌ 超标' if chars > 300 else '✅'
    print(f'{i+1}. [{chars}字] {status} {title_clean[:50]}')
