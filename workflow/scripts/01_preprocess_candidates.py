#!/usr/bin/env python3
"""
选题预处理脚本

功能：
1. 读取采集数据（x.jsonl, weibo.jsonl, rss.jsonl）
2. 去重（相同URL）
3. 时效过滤（24h/48h）
4. 信源打标（一手官方/一手媒体/二手编译）
5. 输出候选新闻CSV

输出：workflow/output/candidates_YYYY-MM-DD.csv
"""

import json
import csv
import sys
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
V2_ROOT = PROJECT_ROOT / "v2"
WORKFLOW_ROOT = PROJECT_ROOT / "workflow"
OUTPUT_DIR = WORKFLOW_ROOT / "output"

# 确保输出目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 信源配置
SOURCE_CONFIG = {
    "official_accounts": [
        "openai", "googleai", "googledrive", "deepmind", "nvidia", "amd",
        "intel", "apple", "samsung", "huawei", "xiaomi", "oneplus",
        "sama", "satyanadella", "tim_cook", "elonmusk"
    ],
    "tier1_media": [
        "bloomberg", "reuters", "techcrunch", "theverge", "wired",
        "arstechnica", "mittechreview", "9to5mac", "appleinsider",
        "9to5google", "sammobile", "androidpolice"
    ],
    "tier2_media": [
        "机器之心", "量子位", "新智元", "36氪", "虎嗅", "爱范儿",
        "钛媒体", "少数派", "品玩"
    ]
}


def parse_date(date_str):
    """解析各种日期格式"""
    if not date_str or date_str == "None":
        return None
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",  # 无秒格式
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%a %b %d %H:%M:%S +0000 %Y",  # Twitter格式
        "%a %b %d %H:%M:%S %z %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def get_source_tier(source_name, source_url=""):
    """
    判断信源级别
    返回: (tier, label)
    tier: 1=一手官方, 2=一手媒体, 3=二手编译
    label: 标签文字
    """
    source_lower = source_name.lower()
    
    # 检查官方账号
    for official in SOURCE_CONFIG["official_accounts"]:
        if official.lower() in source_lower:
            return (1, "一手官方")
    
    # 检查权威媒体
    for media in SOURCE_CONFIG["tier1_media"]:
        if media.lower() in source_lower:
            return (2, "一手媒体")
    
    # 检查二级媒体
    for media in SOURCE_CONFIG["tier2_media"]:
        if media.lower() in source_lower:
            return (3, "二手编译")
    
    # 根据URL判断
    if source_url:
        domain = urlparse(source_url).netloc.lower()
        if any(x in domain for x in ["x.com", "twitter.com"]):
            return (3, "社区讨论")
        if "weibo.com" in domain:
            return (3, "社区讨论")
    
    return (3, "二手编译")


def load_jsonl(filepath):
    """加载jsonl文件"""
    records = []
    if not filepath.exists():
        return records
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                records.append(record)
            except json.JSONDecodeError:
                continue
    return records


def extract_x_records(records):
    """提取X/Twitter记录"""
    results = []
    for r in records:
        try:
            # 处理嵌套结构
            if "data" in r:
                items = r["data"] if isinstance(r["data"], list) else [r["data"]]
            else:
                items = [r]
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                # 支持atom格式（新）和原始格式（旧）
                source = item.get("source", {})
                if isinstance(source, dict):
                    source_name = source.get("author", "Unknown")
                    url = source.get("url", "")
                    created_at = source.get("timestamp", "")
                    content = item.get("title", item.get("text", ""))
                else:
                    # 旧格式
                    author = item.get("author", {})
                    source_name = author.get("screenName", author.get("name", "Unknown"))
                    url = ""
                    if "source" in item and isinstance(item["source"], dict):
                        url = item["source"].get("url", "")
                    if not url and "id" in item:
                        url = f"https://x.com/{source_name}/status/{item['id']}"
                    created_at = item.get("createdAtLocal", item.get("createdAt", ""))
                    content = item.get("text", "")
                
                results.append({
                    "platform": "X",
                    "title": content[:100] + "..." if len(content) > 100 else content,
                    "content": content,
                    "source_name": source_name,
                    "source_url": url,
                    "created_at": created_at,
                    "metrics": json.dumps(item.get("metrics", {}))
                })
        except Exception as e:
            continue
    return results


def extract_weibo_records(records):
    """提取微博记录"""
    results = []
    for r in records:
        try:
            # 处理嵌套结构
            if "data" in r:
                items = r["data"] if isinstance(r["data"], list) else [r["data"]]
            else:
                items = [r]
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                # 支持atom格式（新）和原始格式（旧）
                source = item.get("source", {})
                if isinstance(source, dict):
                    source_name = source.get("author", item.get("username", "Unknown"))
                    url = source.get("url", "")
                    created_at = source.get("timestamp", "")
                    content = item.get("title", item.get("content_raw", ""))
                else:
                    # 旧格式
                    source_name = item.get("username", item.get("nickname", "Unknown"))
                    url = ""
                    if "source" in item and isinstance(item["source"], dict):
                        url = item["source"].get("url", "")
                    created_at = item.get("created_at", "")
                    content = item.get("content_raw", "")
                
                results.append({
                    "platform": "微博",
                    "title": content[:100] + "..." if len(content) > 100 else content,
                    "content": content,
                    "source_name": source_name,
                    "source_url": url,
                    "created_at": created_at,
                    "metrics": f"转发:{item.get('reposts_count', 0)} 评论:{item.get('comments_count', 0)}"
                })
        except Exception as e:
            continue
    return results


def extract_rss_records(records):
    """提取RSS记录"""
    results = []
    for r in records:
        try:
            # 处理嵌套结构
            if "data" in r:
                items = r["data"] if isinstance(r["data"], list) else [r["data"]]
            else:
                items = [r]
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                # 支持atom格式（新）和原始格式（旧）
                source = item.get("source", {})
                if isinstance(source, dict) and source.get("platform") == "rss":
                    # atom格式
                    source_name = source.get("author", "Unknown")
                    url = source.get("url", "")
                    created_at = source.get("timestamp", "")
                    title = item.get("title", "")
                    content = item.get("summary", "")
                else:
                    # 旧格式
                    source_name = "Unknown"
                    if "source" in item and isinstance(item["source"], dict):
                        source_name = item["source"].get("name", "Unknown")
                    
                    # 获取URL
                    url = ""
                    if "source" in item and isinstance(item["source"], dict):
                        url = item["source"].get("url", "")
                    if not url:
                        url = item.get("link", "")
                    
                    created_at = item.get("published", item.get("pubDate", ""))
                    title = item.get("title", "")
                    content = item.get("summary", item.get("content", ""))
                
                results.append({
                    "platform": "RSS",
                    "title": title,
                    "content": content,
                    "source_name": source_name,
                    "source_url": url,
                    "created_at": created_at,
                    "metrics": ""
                })
        except Exception as e:
            continue
    return results


def filter_by_time(records, hours=48):
    """按时间过滤"""
    cutoff = datetime.now() - timedelta(hours=hours)
    filtered = []
    
    for r in records:
        created_at = parse_date(str(r.get("created_at", "")))
        if created_at and created_at >= cutoff:
            filtered.append(r)
    
    return filtered


def deduplicate(records):
    """按URL去重"""
    seen_urls = set()
    unique = []
    
    for r in records:
        url = r.get("source_url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(r)
        elif not url:
            # 没有URL的，用内容哈希
            content_hash = hash(r.get("content", "")[:100])
            if content_hash not in seen_urls:
                seen_urls.add(content_hash)
                unique.append(r)
    
    return unique


def categorize_by_module(record):
    """
    简单分类到模块
    返回: 模块名称 或 None
    """
    content = (record.get("title", "") + " " + record.get("content", "")).lower()
    source_name = record.get("source_name", "").lower()
    
    # AI模型与产品
    ai_keywords = ["ai", "llm", "gpt", "claude", "gemini", "model", "openai", "anthropic", "deepseek", "agent"]
    if any(k in content for k in ai_keywords):
        return "AI模型与产品"
    
    # 芯片与算力
    chip_keywords = ["nvidia", "gpu", "chip", "tsmc", "半导体", "算力", "h100", "b200", "blackwell"]
    if any(k in content for k in chip_keywords):
        return "芯片与算力"
    
    # 手机与消费电子
    mobile_keywords = ["iphone", "samsung", "xiaomi", "huawei", "android", "ios", "手机", "折叠屏"]
    if any(k in content for k in mobile_keywords):
        return "手机与消费电子"
    
    # 游戏行业
    gaming_keywords = ["game", "gaming", "xbox", "playstation", "switch", "游戏", "steam"]
    if any(k in content for k in gaming_keywords):
        return "游戏行业"
    
    # 政策与监管
    policy_keywords = ["policy", "regulation", "ban", "制裁", "出口管制", "反垄断"]
    if any(k in content for k in policy_keywords):
        return "政策与监管"
    
    # 默认：科技行业动态
    return "科技行业动态"


def main():
    # 获取日期参数
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📅 处理日期: {date_str}")
    
    # 数据目录
    data_dir = V2_ROOT / "archive" / "daily" / date_str
    
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        sys.exit(1)
    
    # 加载数据
    print("📂 加载采集数据...")
    all_records = []
    
    # X数据
    x_file = data_dir / "x.jsonl"
    if x_file.exists():
        x_records = extract_x_records(load_jsonl(x_file))
        all_records.extend(x_records)
        print(f"  ✅ X: {len(x_records)} 条")
    
    # 微博数据
    weibo_file = data_dir / "weibo.jsonl"
    if weibo_file.exists():
        weibo_records = extract_weibo_records(load_jsonl(weibo_file))
        all_records.extend(weibo_records)
        print(f"  ✅ 微博: {len(weibo_records)} 条")
    
    # RSS数据
    rss_file = data_dir / "rss.jsonl"
    if rss_file.exists():
        rss_records = extract_rss_records(load_jsonl(rss_file))
        all_records.extend(rss_records)
        print(f"  ✅ RSS: {len(rss_records)} 条")
    
    print(f"\n📊 原始数据: {len(all_records)} 条")
    
    # 去重
    all_records = deduplicate(all_records)
    print(f"📊 去重后: {len(all_records)} 条")
    
    # 时效过滤（48小时）
    all_records = filter_by_time(all_records, hours=48)
    print(f"📊 48h内: {len(all_records)} 条")
    
    # 添加信源标签和分类
    print("🏷️  打标签...")
    for r in all_records:
        tier, label = get_source_tier(r["source_name"], r["source_url"])
        r["source_tier"] = tier
        r["source_label"] = label
        r["module"] = categorize_by_module(r)
    
    # 按信源级别排序
    all_records.sort(key=lambda x: x["source_tier"])
    
    # 输出CSV
    output_file = OUTPUT_DIR / f"candidates_{date_str}.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if all_records:
            writer = csv.DictWriter(f, fieldnames=all_records[0].keys())
            writer.writeheader()
            writer.writerows(all_records)
    
    print(f"\n✅ 输出: {output_file}")
    print(f"   共 {len(all_records)} 条候选新闻")
    
    # 统计
    print("\n📈 统计:")
    print(f"  按平台: X={sum(1 for r in all_records if r['platform']=='X')}, "
          f"微博={sum(1 for r in all_records if r['platform']=='微博')}, "
          f"RSS={sum(1 for r in all_records if r['platform']=='RSS')}")
    print(f"  按信源: 一手官方={sum(1 for r in all_records if r['source_label']=='一手官方')}, "
          f"一手媒体={sum(1 for r in all_records if r['source_label']=='一手媒体')}, "
          f"二手编译={sum(1 for r in all_records if r['source_label']=='二手编译')}")
    
    modules = {}
    for r in all_records:
        m = r["module"]
        modules[m] = modules.get(m, 0) + 1
    print(f"  按模块: {', '.join(f'{k}={v}' for k, v in sorted(modules.items(), key=lambda x: -x[1]))}")


if __name__ == "__main__":
    main()
