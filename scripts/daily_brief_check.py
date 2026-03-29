#!/usr/bin/env python3
"""
日报质量检查脚本
在生成日报前执行，确保所有新闻都有有效来源
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime

class DailyBriefChecker:
    def __init__(self, date_str):
        self.date_str = date_str
        self.errors = []
        self.warnings = []
        self.base_path = Path("/Users/yangliu/Documents/Claude Code/codebuddy/tech-daily-brief")
        
    def load_selection_report(self):
        """加载选题报告"""
        report_path = self.base_path / f"v2/docs/daily_selection_{self.date_str}_final.md"
        if not report_path.exists():
            report_path = self.base_path / f"v2/docs/daily_selection_{self.date_str}.md"
        
        if not report_path.exists():
            self.errors.append(f"❌ 选题报告不存在: {report_path}")
            return None
            
        return report_path.read_text(encoding='utf-8')
    
    def parse_selection_report(self, content):
        """解析选题报告，提取所有新闻条目"""
        items = []
        lines = content.split('\n')
        current_item = {}
        
        for line in lines:
            # 匹配标题行 (✅序号 或 普通序号)
            title_match = re.match(r'^[✅\s]*(?:\d+)\.\s*\*\*(.+?)\*\*', line)
            if title_match:
                if current_item:
                    items.append(current_item)
                current_item = {'title': title_match.group(1), 'selected': '✅' in line}
            
            # 匹配来源行
            elif line.strip().startswith('- **来源**:'):
                source = line.split(':', 1)[1].strip()
                current_item['source'] = source
            
            # 匹配URL行
            elif line.strip().startswith('- **URL**:'):
                url = line.split(':', 1)[1].strip()
                current_item['url'] = url
        
        if current_item:
            items.append(current_item)
            
        return items
    
    def check_sources(self, items):
        """检查信源有效性"""
        invalid_items = []
        
        for item in items:
            # 检查是否入选
            if not item.get('selected'):
                continue
                
            title = item.get('title', '')
            source = item.get('source', '')
            url = item.get('url', '')
            
            # 检查来源是否为"补充"
            if source == '补充' or '待补充' in source:
                invalid_items.append({
                    'title': title,
                    'reason': '来源为"补充"，无原始信源',
                    'source': source,
                    'url': url
                })
                continue
            
            # 检查URL是否为空或待补充
            if not url or url == '(待补充)' or '待补充' in url:
                invalid_items.append({
                    'title': title,
                    'reason': 'URL为空或待补充',
                    'source': source,
                    'url': url
                })
                continue
            
            # 检查URL格式
            if not url.startswith(('http://', 'https://')):
                invalid_items.append({
                    'title': title,
                    'reason': f'URL格式错误: {url}',
                    'source': source,
                    'url': url
                })
        
        return invalid_items
    
    def verify_urls_in_json(self, items):
        """验证URL是否存在于采集的JSON中"""
        # 加载所有采集数据
        all_urls = set()
        for date in [self.date_str, self.date_str.replace('-', '')]:
            for channel in ['x', 'weibo', 'rss']:
                jsonl_path = self.base_path / f"v2/archive/daily/{date}/{channel}.jsonl"
                if jsonl_path.exists():
                    with open(jsonl_path) as f:
                        for line in f:
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    url = data.get('url', '')
                                    if url:
                                        all_urls.add(url)
                                except:
                                    pass
        
        # 检查每个入选新闻的URL
        missing_urls = []
        for item in items:
            if not item.get('selected'):
                continue
                
            url = item.get('url', '')
            # 跳过微信文章（可能来自搜索补充）
            if 'mp.weixin.qq.com' in url:
                continue
                
            # 检查URL是否在采集数据中
            if url and url not in all_urls:
                missing_urls.append({
                    'title': item.get('title', ''),
                    'url': url,
                    'source': item.get('source', '')
                })
        
        return missing_urls
    
    def run_checks(self):
        """执行所有检查"""
        print(f"=== 日报质量检查: {self.date_str} ===\n")
        
        # 1. 加载选题报告
        content = self.load_selection_report()
        if not content:
            return False
        
        print(f"✅ 选题报告已加载\n")
        
        # 2. 解析新闻条目
        items = self.parse_selection_report(content)
        selected_count = sum(1 for item in items if item.get('selected'))
        print(f"📊 总条目: {len(items)}, 入选: {selected_count}\n")
        
        # 3. 检查信源有效性
        print("🔍 检查信源有效性...")
        invalid_items = self.check_sources(items)
        
        if invalid_items:
            print(f"❌ 发现 {len(invalid_items)} 条无效信源:\n")
            for item in invalid_items:
                print(f"  标题: {item['title']}")
                print(f"  原因: {item['reason']}")
                print(f"  来源: {item['source']}")
                print(f"  URL: {item['url']}")
                print()
            self.errors.append(f"有 {len(invalid_items)} 条新闻无有效信源")
        else:
            print("✅ 所有信源有效\n")
        
        # 4. 验证URL在JSON中
        print("🔍 验证URL在采集数据中...")
        missing_urls = self.verify_urls_in_json(items)
        
        if missing_urls:
            print(f"⚠️  {len(missing_urls)} 条URL未在采集数据中找到:\n")
            for item in missing_urls:
                print(f"  标题: {item['title']}")
                print(f"  URL: {item['url']}")
                print(f"  来源: {item['source']}")
                print()
            self.warnings.append(f"{len(missing_urls)} 条URL需要手动验证")
        else:
            print("✅ 所有URL已验证\n")
        
        # 5. 输出总结
        print("=" * 50)
        print("📋 检查总结")
        print("=" * 50)
        
        if self.errors:
            print(f"\n❌ 错误: {len(self.errors)} 项")
            for error in self.errors:
                print(f"   - {error}")
        
        if self.warnings:
            print(f"\n⚠️  警告: {len(self.warnings)} 项")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ 所有检查通过！可以开始撰写日报。")
            return True
        
        if self.errors:
            print("\n❌ 存在错误，请先修复后再撰写日报！")
            return False
        else:
            print("\n⚠️  存在警告，请确认后继续。")
            return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now().strftime("%Y%m%d")
    
    checker = DailyBriefChecker(date_str)
    result = checker.run_checks()
    sys.exit(0 if result else 1)
