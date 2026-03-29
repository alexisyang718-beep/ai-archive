#!/usr/bin/env python3
"""
Obsidian 资讯同步脚本
功能：爬取新闻 → 去重 → 写入 Obsidian Markdown 表格
"""

import os
import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
import subprocess
from deep_translator import GoogleTranslator

# 翻译器（英译中）
translator = GoogleTranslator(source='auto', target='zh-CN')

# ============ 配置 ============
OBSIDIAN_VAULT = Path("~/Documents/Obsidian/资讯").expanduser()
DATA_FILE = Path("~/.codebuddy/news_cache.json").expanduser()
LOG_FILE = Path("~/.codebuddy/news_sync.log").expanduser()

# 确保目录存在
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

# ============ 资讯来源（复用现有采集逻辑）===========
RSS_SOURCES = [
    # AI 媒体
    "https://news.ycombinator.com/rss",
    "https://www.techmeme.com/feed.xml",
    # 中文科技
    "https://www.36kr.com/feed/",
    "https://www.qbitai.com/feed",
]

# ============ 工具函数 ============

def log(msg):
    """日志记录"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get_content_hash(title, source):
    """生成内容哈希，用于去重"""
    raw = f"{title}|{source}".lower()
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def load_cache():
    """加载已有缓存"""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"items": [], "hashes": set()}

def save_cache(cache):
    """保存缓存"""
    # hashes 必须是可序列化类型
    cache["hashes"] = list(cache.get("hashes", []))
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def fetch_rss(url):
    """爬取 RSS"""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "30", url],
            capture_output=True, text=True, timeout=35
        )
        return result.stdout
    except Exception as e:
        log(f"获取 RSS 失败 {url}: {e}")
        return ""

def parse_rss(xml_content, source_name):
    """简单解析 RSS"""
    items = []
    import re
    # 提取 item
    item_pattern = r"<item>(.*?)</item>"
    for match in re.finditer(item_pattern, xml_content, re.DOTALL):
        item_xml = match.group(1)
        title = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", item_xml)
        if not title:
            title = re.search(r"<title>(.*?)</title>", item_xml)
        
        link = re.search(r"<link>(.*?)</link>", item_xml)
        
        if title and link:
            items.append({
                "title": title.group(1).strip(),
                "url": link.group(1).strip(),
                "source": source_name
            })
    return items

def fetch_all_news():
    """获取所有资讯"""
    all_items = []
    
    # 1. 读取已有的采集数据（如果存在）
    tech_brief_data = Path("brief").glob("*.html")
    # TODO: 可以复用 tech-daily-brief 的采集结果
    
    # 2. 爬取 RSS
    for rss_url in RSS_SOURCES:
        source_name = rss_url.split("//")[1].split("/")[0]
        xml = fetch_rss(rss_url)
        if xml:
            items = parse_rss(xml, source_name)
            all_items.extend(items)
            log(f"从 {source_name} 获取 {len(items)} 条")
    
    return all_items

def get_month_file():
    """获取当月 Markdown 文件"""
    month_key = datetime.now().strftime("%Y-%m")
    md_file = OBSIDIAN_VAULT / f"{month_key}.md"
    
    # 如果文件不存在，创建表头
    if not md_file.exists():
        header = f"""# {month_key} 资讯

| 日期 | 时间 | 标题 | 来源 | 摘要 | 标签 | 原始链接 |
|------|------|------|------|------|------|----------|
"""
        md_file.write_text(header, encoding="utf-8")
        log(f"创建月度文件: {md_file}")
    
    return md_file

def deduplicate(new_items, cache):
    """去重，返回不重复的items"""
    # 确保 hashes 是 set 类型
    existing_hashes = set(cache.get("hashes", []))
    new_hashes = []
    unique_items = []
    
    for item in new_items:
        h = get_content_hash(item["title"], item["source"])
        if h not in existing_hashes and h not in new_hashes:
            new_hashes.append(h)
            unique_items.append(item)
    
    # 更新缓存
    existing_hashes.update(new_hashes)
    cache["hashes"] = list(existing_hashes)
    return unique_items

def write_to_obsidian(items):
    """写入 Obsidian Markdown 表格"""
    if not items:
        log("没有新资讯需要写入")
        return 0
    
    md_file = get_month_file()
    
    # 读取现有内容
    content = md_file.read_text(encoding="utf-8")
    lines = content.split("\n")
    
    # 在表格最后添加新行（找到最后一个 | 后插入）
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    
    new_lines = []
    for item in items:
        # 翻译标题
        original_title = item["title"]
        try:
            translated = translator.translate(original_title)
            # 如果翻译结果不为空，使用翻译；否则保留原文
            title = translated if translated and len(translated) > 5 else original_title
        except Exception:
            title = original_title  # 翻译失败保留原文
        
        # 截取标题（翻译后）
        title = title[:80] + "..." if len(title) > 80 else title
        
        # 生成标签（从来源推断）
        tags = "AI"  # 默认标签
        if "36kr" in item["source"]:
            tags = "科技"
        elif "techmeme" in item["source"]:
            tags = "科技"
        
        row = f"| {date_str} | {time_str} | {title} | {item['source']} | - | {tags} | [链接]({item['url']}) |"
        new_lines.append(row)
    
    # 找到表格分隔符位置，插入新行
    sep_idx = None
    for i, line in enumerate(lines):
        if line.startswith("|") and "---" in line:
            sep_idx = i
            break
    
    if sep_idx:
        # 插入新行
        lines = lines[:sep_idx+1] + new_lines + lines[sep_idx+1:]
        md_file.write_text("\n".join(lines), encoding="utf-8")
        log(f"写入 {len(items)} 条资讯到 {md_file.name}")
    
    return len(items)

# ============ 主流程 ============

def main():
    log("=" * 40)
    log("开始同步资讯到 Obsidian")
    
    # 1. 加载缓存
    cache = load_cache()
    original_hashes = set(cache.get("hashes", []))
    
    # 2. 爬取资讯
    all_items = fetch_all_news()
    log(f"共获取 {len(all_items)} 条资讯")
    
    # 3. 去重
    unique_items = deduplicate(all_items, cache)
    log(f"去重后新增 {len(unique_items)} 条")
    
    # 4. 写入 Obsidian
    count = write_to_obsidian(unique_items)
    
    # 5. 保存缓存
    if unique_items:
        save_cache(cache)
        log(f"缓存已更新，共 {len(cache.get('hashes', []))} 条")
    
    log(f"完成！写入 {count} 条")

if __name__ == "__main__":
    main()
