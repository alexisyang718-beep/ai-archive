#!/usr/bin/env python3
"""
采集监控报告生成器

功能：
1. 生成每次采集的详细报告
2. 监控采集健康状态（成功率、异常告警）
3. 对比历史数据发现漏采
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from collector import AUTHOR_LEARNER_AVAILABLE
if AUTHOR_LEARNER_AVAILABLE:
    from author_learner import get_learner


class CollectionMonitor:
    """采集监控器"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "archive" / "daily"
        self.data_dir = data_dir
        
        # 报告输出目录
        self.report_dir = Path(__file__).parent.parent / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    def analyze_collection(self, date: str, channel: str) -> Dict:
        """
        分析单次采集数据
        
        Returns:
            {
                "total": 总数,
                "by_category": 分类分布,
                "by_author": 作者分布,
                "by_trust": 可信度分布,
                "other_details": other分类详情,
                "issues": 发现的问题
            }
        """
        jsonl_path = self.data_dir / date / f"{channel}.jsonl"
        
        if not jsonl_path.exists():
            return {"error": f"文件不存在: {jsonl_path}"}
        
        atoms = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        atoms.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        # 基础统计
        by_category = Counter(a.get('category', 'other') for a in atoms)
        by_author = Counter(a.get('source', {}).get('author', 'unknown') for a in atoms)
        by_trust = Counter(a.get('trust_default', 'L3') for a in atoms)
        
        # other分类详情
        other_atoms = [a for a in atoms if a.get('category') == 'other']
        other_by_author = Counter(a.get('source', {}).get('author', 'unknown') for a in other_atoms)
        
        # 发现问题
        issues = []
        
        # 1. other分类占比过高
        other_pct = len(other_atoms) / len(atoms) * 100 if atoms else 0
        if other_pct > 40:
            issues.append(f"⚠️ other分类占比过高: {other_pct:.1f}%")
        
        # 2. 作者集中度异常（可能漏采）
        if by_author:
            top_author_pct = by_author.most_common(1)[0][1] / len(atoms) * 100
            if top_author_pct > 30:
                issues.append(f"⚠️ 作者集中度过高: {by_author.most_common(1)[0][0]} 占 {top_author_pct:.1f}%")
        
        # 3. 样本数异常
        if len(atoms) < 10:
            issues.append(f"⚠️ 采集数量过少: 仅 {len(atoms)} 条")
        
        return {
            "total": len(atoms),
            "by_category": dict(by_category.most_common()),
            "by_author": dict(by_author.most_common(10)),
            "by_trust": dict(by_trust),
            "other_count": len(other_atoms),
            "other_pct": round(other_pct, 1),
            "other_top_authors": dict(other_by_author.most_common(10)),
            "issues": issues
        }
    
    def generate_report(self, date: str) -> str:
        """生成完整的采集监控报告"""
        lines = []
        lines.append("=" * 70)
        lines.append(f"📊 采集监控报告 - {date}")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        
        for channel in ["x", "weibo", "rss"]:
            lines.append(f"\n{'─' * 70}")
            lines.append(f"📡 渠道: {channel.upper()}")
            lines.append('─' * 70)
            
            result = self.analyze_collection(date, channel)
            
            if "error" in result:
                lines.append(f"❌ {result['error']}")
                continue
            
            # 基础统计
            lines.append(f"\n总计: {result['total']} 条")
            
            # 分类分布
            lines.append(f"\n📂 分类分布:")
            for cat, count in result['by_category'].items():
                pct = count / result['total'] * 100
                bar = '█' * int(pct / 5)
                lines.append(f"  {cat:20s} {count:4d} ({pct:5.1f}%) {bar}")
            
            # other分类详情
            if result['other_count'] > 0:
                lines.append(f"\n📋 other分类详情 ({result['other_count']}条, {result['other_pct']}%):")
                for author, count in list(result['other_top_authors'].items())[:5]:
                    lines.append(f"  {author}: {count}条")
            
            # 可信度分布
            lines.append(f"\n⭐ 可信度分布:")
            for trust, count in result['by_trust'].items():
                pct = count / result['total'] * 100
                lines.append(f"  {trust}: {count} ({pct:.1f}%)")
            
            # 问题告警
            if result['issues']:
                lines.append(f"\n🚨 发现的问题:")
                for issue in result['issues']:
                    lines.append(f"  {issue}")
            else:
                lines.append(f"\n✅ 未发现明显问题")
        
        # 学习器状态
        if AUTHOR_LEARNER_AVAILABLE:
            learner = get_learner()
            lines.append(f"\n{'=' * 70}")
            lines.append(f"📚 自动学习器状态")
            lines.append(f"{'=' * 70}")
            lines.append(f"已学习作者: {len(learner.learned_authors)} 个")
            if learner.learned_authors:
                cat_dist = Counter(learner.learned_authors.values())
                lines.append(f"分类分布: {dict(cat_dist)}")
        
        lines.append(f"\n{'=' * 70}")
        lines.append("报告生成完成")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def save_report(self, date: str) -> Path:
        """保存报告到文件"""
        report = self.generate_report(date)
        report_path = self.report_dir / f"{date}_monitor_report.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return report_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="采集监控报告")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--channel", choices=["x", "weibo", "rss", "all"], default="all")
    parser.add_argument("--save", action="store_true", help="保存到文件")
    
    args = parser.parse_args()
    
    monitor = CollectionMonitor()
    
    if args.save:
        report_path = monitor.save_report(args.date)
        print(f"✅ 报告已保存: {report_path}")
    else:
        print(monitor.generate_report(args.date))


if __name__ == "__main__":
    main()
