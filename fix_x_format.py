import json
from pathlib import Path

x_path = Path("v2/archive/daily/2026-03-27/x.jsonl")
if x_path.exists():
    content = x_path.read_text()
    try:
        data = json.loads(content)
        if isinstance(data, list):
            print(f"X数据: JSON数组 {len(data)} 条，转换为JSONL...")
            with open(x_path, 'w') as f:
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            print("✅ X数据格式已修复")
    except:
        print("X数据格式正常或已修复")
