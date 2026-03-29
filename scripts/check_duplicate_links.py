#!/usr/bin/env python3
"""
检查日报中是否有重复的链接
"""

import re
import sys
from pathlib import Path
from collections import defaultdict


def check_duplicate_links(html_path):
    """检查HTML中的重复链接"""
    if not Path(html_path).exists():
        print(f"❌ 文件不存在: {html_path}")
        return False
    
    content = Path(html_path).read_text(encoding='utf-8')
    
    # 提取所有链接
    links = re.findall(r'href="([^"]+)"', content)
    
    # 统计重复
    link_count = defaultdict(list)
    for i, link in enumerate(links):
        # 忽略锚点链接和javascript
        if link.startswith(('#', 'javascript:', 'mailto:')):
            continue
        link_count[link].append(i)
    
    # 找出重复
    duplicates = {k: v for k, v in link_count.items() if len(v) > 1}
    
    if duplicates:
        print(f"⚠️  发现 {len(duplicates)} 个重复链接:\n")
        for link, positions in duplicates.items():
            print(f"  链接: {link}")
            print(f"  出现次数: {len(positions)}")
            print()
        return False
    else:
        print("✅ 未发现重复链接")
        return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 check_duplicate_links.py <html_path>")
        sys.exit(1)
    
    result = check_duplicate_links(sys.argv[1])
    sys.exit(0 if result else 1)
