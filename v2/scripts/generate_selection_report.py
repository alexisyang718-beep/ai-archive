#!/usr/bin/env python3
"""
实时选题报告生成器

功能：
1. 读取当日采集的所有 Atom 数据
2. 按分类整理生成 Markdown 选题报告
3. 支持定时刷新（--watch 模式）

输出格式：
- v2/docs/daily/YYYY-MM-DD/selection_report.md

使用方式：
    # 生成一次报告
    python3 generate_selection_report.py
    
    # 定时刷新（每5分钟）
    python3 generate_selection_report.py --watch
    
    # 指定日期
    python3 generate_selection_report.py --date 2026-03-20
"""

import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List

# 添加 v2/scripts 到 path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore

# ============ 配置 ============
V2_ROOT = Path(__file__).parent.parent
DOCS_DIR = V2_ROOT / "docs"

# 分类显示名称
CATEGORY_NAMES = {
    "ai_models": "🤖 AI 模型与产品",
    "mobile": "📱 手机与消费电子",
    "chips": "🔧 芯片与算力",
    "gaming": "🎮 游戏行业",
    "tech_industry": "🏢 科技行业动态",
    "policy": "📜 政策与监管",
    "software_dev": "💻 开发者与软件工程",
    "internet_tech": "🌐 互联网科技",
    "ev_auto": "🚗 电动汽车",
    "crypto_web3": "₿ 加密与 Web3",
    "other": "📋 其他",
}

# 可信度图标
TRUST_ICONS = {
    "L1": "🟢",
    "L2": "🟡", 
    "L3": "🟠",
}

# 平台图标
PLATFORM_ICONS = {
    "x": "𝕏",
    "weibo": "📡",
    "rss": "📰",
}

# 内容类型标签
CONTENT_TYPE_LABELS = {
    "official": "官方",
    "exclusive": "独家",
    "firsthand_test": "实测",
    "original_analysis": "原创分析",
    "report": "报道",
    "commentary": "评论",
    "repost": "转发",
}


class SelectionReportGenerator:
    """选题报告生成器"""
    
    def __init__(self, date: str = None):
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.store = AtomStore()
        self.report_dir = DOCS_DIR / "daily" / self.date
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
    def load_all_atoms(self) -> List[Dict]:
        """加载当日所有 Atoms"""
        return self.store.query_by_date(self.date)
    
    def group_by_category(self, atoms: List[Dict]) -> Dict[str, List[Dict]]:
        """按分类分组"""
        groups = defaultdict(list)
        for atom in atoms:
            cat = atom.get("category", "other")
            groups[cat].append(atom)
        return groups
    
    def format_atom(self, atom: Dict, index: int) -> str:
        """格式化单条新闻为 Markdown"""
        lines = []
        
        # 基础信息
        trust = atom.get("trust_default", "L3")
        trust_icon = TRUST_ICONS.get(trust, "⚪")
        
        source = atom.get("source", {})
        platform = source.get("platform", "unknown")
        platform_icon = PLATFORM_ICONS.get(platform, "📄")
        
        author = source.get("author", "未知")
        author_type = source.get("author_type", "")
        url = source.get("url", "")
        
        # 标题（优先中文标题）
        title = atom.get("title_zh") or atom.get("title", "无标题")
        
        # 内容摘要
        summary = atom.get("summary_zh", "")
        
        # 内容类型
        content_type = atom.get("content_type", "")
        ct_label = CONTENT_TYPE_LABELS.get(content_type, content_type)
        
        # 实体标签
        entities = atom.get("entities", [])
        entity_str = ", ".join(entities[:5]) if entities else ""
        
        # 互动数据（仅 X/微博）
        metrics = atom.get("metrics", {})
        metrics_str = ""
        if metrics:
            likes = metrics.get("likes", 0)
            retweets = metrics.get("retweets", 0)
            replies = metrics.get("replies", 0) or metrics.get("comments", 0)
            if likes or retweets or replies:
                metrics_str = f"❤️{likes} 🔁{retweets} 💬{replies}"
        
        # 生成 Markdown
        lines.append(f"### {index}. {trust_icon} {title}")
        lines.append("")
        
        # 元信息行
        meta_parts = [
            f"{platform_icon} **{author}**",
            f"类型: {ct_label}" if ct_label else "",
            f"可信度: {trust}",
            metrics_str,
        ]
        lines.append(" | ".join(p for p in meta_parts if p))
        lines.append("")
        
        # 内容摘要
        if summary:
            # 清理摘要，限制长度
            summary_clean = summary.strip().replace("\n", " ")
            if len(summary_clean) > 300:
                summary_clean = summary_clean[:300] + "..."
            lines.append(f"**内容**: {summary_clean}")
            lines.append("")
        
        # 原始链接
        if url:
            lines.append(f"🔗 [原始信源]({url})")
        
        # 实体标签
        if entity_str:
            lines.append(f"🏷️ {entity_str}")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        return "\n".join(lines)
    
    def generate_report(self) -> str:
        """生成完整报告"""
        atoms = self.load_all_atoms()
        
        if not atoms:
            return f"# 选题报告 - {self.date}\n\n暂无数据。请先运行采集脚本。\n"
        
        # 按分类分组
        by_category = self.group_by_category(atoms)
        
        # 按可信度排序（L1优先）
        for cat in by_category:
            by_category[cat].sort(
                key=lambda a: {"L1": 0, "L2": 1, "L3": 2}.get(a.get("trust_default", "L3"), 2)
            )
        
        # 生成 Markdown
        lines = []
        lines.append(f"# 📋 选题报告 - {self.date}")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**总计**: {len(atoms)} 条")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 统计概览
        lines.append("## 📊 统计概览")
        lines.append("")
        
        # 按分类统计
        for cat_key in ["ai_models", "mobile", "chips", "gaming", "tech_industry", "policy", "other"]:
            if cat_key in by_category:
                cat_name = CATEGORY_NAMES.get(cat_key, cat_key)
                count = len(by_category[cat_key])
                lines.append(f"- {cat_name}: {count} 条")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 详细内容（按分类）
        category_order = [
            "ai_models", "mobile", "chips", "gaming", 
            "tech_industry", "policy", "software_dev",
            "internet_tech", "ev_auto", "crypto_web3", "other"
        ]
        
        for cat_key in category_order:
            if cat_key not in by_category:
                continue
            
            cat_name = CATEGORY_NAMES.get(cat_key, cat_key)
            cat_atoms = by_category[cat_key]
            
            lines.append(f"## {cat_name}")
            lines.append(f"*{len(cat_atoms)} 条*")
            lines.append("")
            
            for i, atom in enumerate(cat_atoms, 1):
                lines.append(self.format_atom(atom, i))
        
        return "\n".join(lines)
    
    def save_report(self) -> Path:
        """保存报告到文件"""
        report = self.generate_report()
        report_path = self.report_dir / "selection_report.md"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        
        return report_path
    
    def watch_mode(self, interval: int = 300):
        """定时刷新模式"""
        print(f"👀 启动定时刷新模式（每 {interval} 秒）")
        print(f"📁 报告保存位置: {self.report_dir}/selection_report.md")
        print("按 Ctrl+C 停止\n")
        
        try:
            while True:
                report_path = self.save_report()
                atoms = self.load_all_atoms()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 已更新: {report_path} ({len(atoms)} 条)")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n👋 已停止")


def main():
    parser = argparse.ArgumentParser(description="生成实时选题报告")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"),
                        help="指定日期 (YYYY-MM-DD)")
    parser.add_argument("--watch", action="store_true",
                        help="定时刷新模式")
    parser.add_argument("--interval", type=int, default=300,
                        help="刷新间隔秒数（默认300秒=5分钟）")
    parser.add_argument("--output", type=str,
                        help="输出文件路径（默认 v2/docs/daily/YYYY-MM-DD/selection_report.md）")
    
    args = parser.parse_args()
    
    generator = SelectionReportGenerator(date=args.date)
    
    if args.watch:
        # 定时刷新模式
        generator.watch_mode(interval=args.interval)
    else:
        # 单次生成
        report_path = generator.save_report()
        atoms = generator.load_all_atoms()
        print(f"✅ 选题报告已生成: {report_path}")
        print(f"📊 共 {len(atoms)} 条内容")
        
        # 按分类统计
        by_cat = generator.group_by_category(atoms)
        if by_cat:
            print("\n分类统计:")
            for cat_key in ["ai_models", "mobile", "chips", "gaming", "tech_industry", "policy", "other"]:
                if cat_key in by_cat:
                    cat_name = CATEGORY_NAMES.get(cat_key, cat_key)
                    print(f"  {cat_name}: {len(by_cat[cat_key])} 条")


if __name__ == "__main__":
    main()
