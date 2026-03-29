#!/usr/bin/env python3
"""
Obsidian 资讯提取脚本
功能：按日期范围提取资讯，供日报生成使用
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta

# ============ 配置 ============
OBSIDIAN_VAULT = Path("~/Documents/Obsidian/资讯").expanduser()
OUTPUT_FILE = Path("~/.codebuddy/daily_news.json").expanduser()

def parse_markdown_table(content):
    """解析 Markdown 表格"""
    items = []
    lines = content.split("\n")
    
    in_table = False
    for line in lines:
        line = line.strip()
        
        # 表头
        if line.startswith("| 日期 |"):
            in_table = True
            continue
        
        # 跳过分隔符
        if in_table and line.startswith("|" and "---" in line:
            continue
        
        # 数据行
        if in_table and line.startswith("|") and "|" in line[1:]:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 6:
                items.append({
                    "date": parts[0],      # 日期
                    "time": parts[1],      # 时间
                    "title": parts[2],     # 标题
                    "source": parts[3],    # 来源
                    "summary": parts[4],   # 摘要
                    "tags": parts[5],      # 标签
                    "url": parts[6] if len(parts) > 6 else ""  # 链接
                })
    
    return items

def fetch_news(days=1):
    """获取最近N天的资讯"""
    all_items = []
    
    # 获取当月和上月的文件
    now = datetime.now()
    months = [now.strftime("%Y-%m")]
    if now.day <= 5:  # 月初可能需要读上月
        last_month = now - timedelta(days=5)
        months.append(last_month.strftime("%Y-%m"))
    
    for month_key in months:
        md_file = OBSIDIAN_VAULT / f"{month_key}.md"
        if md_file.exists():
            content = md_file.read_text(encoding="utf-8")
            items = parse_markdown_table(content)
            all_items.extend(items)
    
    # 按日期筛选
    cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    filtered = [item for item in all_items if item["date"] >= cutoff]
    
    # 按时间倒序
    filtered.sort(key=lambda x: (x["date"], x["time"]), reverse=True)
    
    return filtered

def main():
    # 默认获取昨天+今天的资讯
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    
    items = fetch_news(days)
    
    # 输出 JSON 供其他脚本使用
    output = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "count": len(items),
        "items": items
    }
    
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
