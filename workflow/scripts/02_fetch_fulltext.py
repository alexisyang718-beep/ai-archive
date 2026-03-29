#!/usr/bin/env python3
"""
全文抓取脚本

功能：
1. 读取选题报告中的URL列表
2. 使用Jina Reader批量抓取原文
3. 缓存原文内容
4. 输出原文缓存JSON

输出：workflow/output/fulltext_YYYY-MM-DD.json
"""

import json
import sys
import time
import re
from pathlib import Path
from urllib.parse import urlparse
import subprocess

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
WORKFLOW_ROOT = PROJECT_ROOT / "workflow"
OUTPUT_DIR = WORKFLOW_ROOT / "output"

# 确保输出目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_urls_from_selection(selection_file):
    """从选题报告中提取URL"""
    urls = []
    
    with open(selection_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 匹配Markdown链接格式: [text](url) 或 - **URL**: url
    # 匹配 - **URL**: https://...
    url_pattern = r'\*\*URL\*\*:\s*(https?://\S+)'
    matches = re.findall(url_pattern, content)
    urls.extend(matches)
    
    # 去重
    urls = list(dict.fromkeys(urls))
    
    return urls


def fetch_with_jina(url, retries=3):
    """使用Jina Reader抓取全文"""
    jina_url = f"https://r.jina.ai/{url}"
    
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["curl", "-s", "-L", "--max-time", "30", jina_url],
                capture_output=True,
                text=True,
                timeout=35
            )
            
            if result.returncode == 0 and result.stdout:
                content = result.stdout.strip()
                # 检查是否返回错误
                if content and not content.startswith("{"):
                    return {
                        "success": True,
                        "content": content,
                        "length": len(content)
                    }
            
            time.sleep(2)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            continue
    
    return {
        "success": False,
        "content": "",
        "error": "Failed to fetch"
    }


def fetch_with_tavily(url, retries=2):
    """使用tavily_extract作为备选"""
    # 这里可以集成tavily MCP
    # 暂时返回失败，使用Jina Reader为主
    return {
        "success": False,
        "content": "",
        "error": "Tavily not implemented"
    }


def main():
    # 获取日期参数
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📅 处理日期: {date_str}")
    
    # 读取选题报告
    selection_file = PROJECT_ROOT / "v2" / "docs" / f"daily_selection_{date_str}.md"
    
    if not selection_file.exists():
        print(f"❌ 选题报告不存在: {selection_file}")
        print("请先生成选题报告")
        sys.exit(1)
    
    # 提取URL
    print("📂 提取URL...")
    urls = extract_urls_from_selection(selection_file)
    print(f"  找到 {len(urls)} 个URL")
    
    if not urls:
        print("⚠️ 没有找到URL")
        sys.exit(0)
    
    # 批量抓取
    print("\n🌐 抓取全文...")
    results = {}
    
    for i, url in enumerate(urls, 1):
        print(f"  [{i}/{len(urls)}] {url[:60]}...", end=" ")
        
        # 跳过X/Twitter/微博链接（不需要抓取全文）
        domain = urlparse(url).netloc.lower()
        if any(x in domain for x in ["x.com", "twitter.com", "weibo.com"]):
            print("跳过(社交媒体)")
            results[url] = {
                "success": True,
                "content": "[社交媒体内容，使用原文]",
                "skipped": True
            }
            continue
        
        # 抓取
        result = fetch_with_jina(url)
        
        if result["success"]:
            print(f"✅ ({result['length']} chars)")
            results[url] = result
        else:
            print(f"❌ {result.get('error', 'Unknown')}")
            results[url] = result
        
        # 限速，避免请求过快
        time.sleep(1)
    
    # 保存结果
    output_file = OUTPUT_DIR / f"fulltext_{date_str}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 输出: {output_file}")
    
    # 统计
    success_count = sum(1 for r in results.values() if r.get("success"))
    skipped_count = sum(1 for r in results.values() if r.get("skipped"))
    failed_count = len(results) - success_count
    
    print(f"\n📈 统计:")
    print(f"  成功: {success_count - skipped_count}")
    print(f"  跳过(社交媒体): {skipped_count}")
    print(f"  失败: {failed_count}")


if __name__ == "__main__":
    from datetime import datetime
    main()
