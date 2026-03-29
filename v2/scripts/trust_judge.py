#!/usr/bin/env python3
"""
Trust Judge — 置信度精判器

职责：
1. 在写日报时，对每条候选新闻精判 trust_final
2. 根据 content_type 和内容信号词判断置信度
3. 精判结果写回 Atom

使用方式：
    # 精判当日所有 atoms
    python3 trust_judge.py --date 2026-03-18
    
    # 精判指定 atom
    python3 trust_judge.py --id atom_20260318_042
    
    # 只输出建议，不写入
    python3 trust_judge.py --date 2026-03-18 --dry-run
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 添加 v2/scripts 到 path
sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore


# ====================================================================
# 置信度判断规则
# ====================================================================

class TrustJudge:
    """
    置信度精判器
    
    核心原则：信源置信度跟着内容走，不跟着人走。
    同一个 @数码闲聊站，发独家爆料 = L1，转发新闻 = L3。
    """
    
    # L1 信号词（独家/一手信息）
    L1_SIGNALS = [
        "exclusive", "独家", "首发", "据记者获悉", "本报了解到",
        "breaking", "just in", "first reported",
        "hands-on", "实测", "上手", "体验报告",
        "official", "官方", "公告", "宣布",
        "we're releasing", "we're launching", "introducing",
    ]
    
    # L3 信号词（转载/二手信息）
    # 注意：短词需要带空格边界避免误匹配
    L3_SIGNALS = [
        "编译自", "据xxx报道", "translated", "translation",
        "reposted from", "转自", "来源：",
        "转发", "repost",
        "据外媒", "据路透社", "据彭博",
    ]
    
    # L3 信号词（需要边界检查的短词）
    L3_BOUNDARY_SIGNALS = ["rt ", " rt ", "via "]
    
    def judge(self, atom: Dict) -> Tuple[str, str]:
        """
        精判一条 Atom 的置信度。
        
        Args:
            atom: Atom 字典
            
        Returns:
            (trust_final, trust_reason)
        """
        # 提取字段
        title = atom.get("title", "")
        title_zh = atom.get("title_zh", "")
        summary = atom.get("summary_zh", "")
        content_type = atom.get("content_type", "commentary")
        author_type = atom.get("source", {}).get("author_type", "")
        author = atom.get("source", {}).get("author", "")
        
        # 合并文本用于信号词检测
        full_text = f"{title} {title_zh} {summary}"
        text_lower = full_text.lower()
        
        # ========================================
        # 判断规则（按优先级）
        # ========================================
        
        # 规则 1: content_type 判断（最可靠的结构化信号）
        if content_type == "official":
            return ("L1", "官方公告/声明")
        elif content_type == "exclusive":
            return ("L1", "独家爆料")
        elif content_type == "firsthand_test":
            return ("L1", "一手实测")
        elif content_type == "translation":
            return ("L3", "翻译/编译内容")
        elif content_type == "repost":
            return ("L3", "转发/转载内容")
        
        # 规则 2: L1 信号词检测（可提升 content_type 不明确的条目）
        for signal in self.L1_SIGNALS:
            if signal.lower() in text_lower:
                return ("L1", f"检测到 L1 信号词: '{signal}'")
        
        # 规则 3: L3 信号词检测
        for signal in self.L3_SIGNALS:
            if signal.lower() in text_lower:
                return ("L3", f"检测到 L3 信号词: '{signal}'")
        # L3 边界信号词（需要空格边界）
        for signal in self.L3_BOUNDARY_SIGNALS:
            if signal in text_lower or text_lower.startswith(signal.lstrip()):
                return ("L3", f"检测到 L3 信号词: '{signal.strip()}'")
        
        # 规则 4: 剩余 content_type 判断
        if content_type == "original_analysis":
            if any(kw in text_lower for kw in ["data", "数据", "survey", "调研", "统计"]):
                return ("L1", "原创分析（含自有数据）")
            else:
                return ("L2", "原创分析（无自有数据）")
        elif content_type == "report":
            if author_type in ["media", "official"]:
                return ("L2", "权威媒体报道")
            else:
                return ("L3", "非权威来源报道")
        
        # 规则 4: author_type 判断（兜底）
        if author_type == "official":
            return ("L1", "官方账号发布")
        elif author_type == "ceo_cto":
            return ("L1", "公司高管发布")
        elif author_type == "media":
            return ("L2", "媒体账号发布")
        elif author_type == "kol":
            return ("L2", "KOL 发布")
        else:
            return ("L3", "普通来源")
    
    def judge_batch(self, atoms: List[Dict], dry_run: bool = False) -> List[Dict]:
        """
        批量精判。
        
        Args:
            atoms: Atom 列表
            dry_run: 是否只输出建议，不写入
            
        Returns:
            更新后的 Atom 列表
        """
        store = AtomStore()
        updated_atoms = []
        
        for atom in atoms:
            atom_id = atom.get("id", "")
            title = atom.get("title", "")[:50]
            
            # 精判
            trust_final, trust_reason = self.judge(atom)
            
            print(f"\n[{atom_id}] {title}...")
            print(f"  置信度: {trust_final}")
            print(f"  原因: {trust_reason}")
            
            if not dry_run and atom_id:
                # 写回
                ok = store.update_atom(atom_id, {
                    "trust_final": trust_final,
                    "trust_reason": trust_reason,
                })
                if ok:
                    print(f"  ✅ 已更新")
                else:
                    print(f"  ⚠️ 更新失败")
            
            # 更新 atom 对象
            atom["trust_final"] = trust_final
            atom["trust_reason"] = trust_reason
            updated_atoms.append(atom)
        
        return updated_atoms
    
    def get_statistics(self, atoms: List[Dict]) -> Dict:
        """
        统计精判结果。
        """
        stats = {
            "total": len(atoms),
            "L1": 0,
            "L2": 0,
            "L3": 0,
            "by_category": {},
        }
        
        for atom in atoms:
            trust = atom.get("trust_final", "L3")
            stats[trust] = stats.get(trust, 0) + 1
            
            category = atom.get("category", "other")
            if category not in stats["by_category"]:
                stats["by_category"][category] = {"L1": 0, "L2": 0, "L3": 0}
            stats["by_category"][category][trust] += 1
        
        return stats


# ====================================================================
# CLI 入口
# ====================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Trust Judge — 置信度精判器")
    parser.add_argument("--date", type=str, default=None,
                        help="精判指定日期的 atoms（格式 YYYY-MM-DD）")
    parser.add_argument("--id", type=str, default=None,
                        help="精判指定 atom ID")
    parser.add_argument("--dry-run", action="store_true",
                        help="只输出建议，不写入")
    
    args = parser.parse_args()
    
    store = AtomStore()
    judge = TrustJudge()
    
    if args.id:
        # 精判单个 atom
        atom = store.query_by_id(args.id)
        if not atom:
            print(f"❌ Atom 不存在: {args.id}")
            sys.exit(1)
        
        trust_final, trust_reason = judge.judge(atom)
        
        print(f"\n{'='*60}")
        print(f"Atom ID: {args.id}")
        print(f"标题: {atom.get('title', '')[:60]}")
        print(f"{'='*60}")
        print(f"置信度: {trust_final}")
        print(f"原因: {trust_reason}")
        
        if not args.dry_run:
            ok = store.update_atom(args.id, {
                "trust_final": trust_final,
                "trust_reason": trust_reason,
            })
            if ok:
                print("\n✅ 已更新")
            else:
                print("\n⚠️ 更新失败")
    
    elif args.date:
        # 精判指定日期的所有 atoms
        atoms = store.query_by_date(args.date)
        if not atoms:
            print(f"❌ 未找到 {args.date} 的 atoms")
            sys.exit(1)
        
        print(f"\n{'='*60}")
        print(f"精判日期: {args.date}")
        print(f"共 {len(atoms)} 条 atoms")
        print(f"{'='*60}")
        
        updated_atoms = judge.judge_batch(atoms, dry_run=args.dry_run)
        
        # 统计
        stats = judge.get_statistics(updated_atoms)
        print(f"\n{'='*60}")
        print("📊 精判统计")
        print(f"{'='*60}")
        print(f"总计: {stats['total']}")
        print(f"L1: {stats['L1']} ({stats['L1']/max(stats['total'],1)*100:.1f}%)")
        print(f"L2: {stats['L2']} ({stats['L2']/max(stats['total'],1)*100:.1f}%)")
        print(f"L3: {stats['L3']} ({stats['L3']/max(stats['total'],1)*100:.1f}%)")
        print(f"\n按板块:")
        for cat, trust_stats in stats["by_category"].items():
            print(f"  {cat}: L1={trust_stats['L1']}, L2={trust_stats['L2']}, L3={trust_stats['L3']}")
        
        if args.dry_run:
            print("\n⚠️ [DRY RUN] 未写入数据")
        else:
            print("\n✅ 已写入所有精判结果")
    
    else:
        # 精判今天的 atoms
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"未指定日期，默认精判今天: {today}")
        
        atoms = store.query_by_date(today)
        if not atoms:
            print(f"❌ 今天还没有采集数据")
            print(f"请先运行: python3 v2/scripts/collector.py")
            sys.exit(1)
        
        updated_atoms = judge.judge_batch(atoms, dry_run=args.dry_run)
        stats = judge.get_statistics(updated_atoms)
        
        print(f"\n{'='*60}")
        print("📊 精判统计")
        print(f"{'='*60}")
        print(f"总计: {stats['total']}")
        print(f"L1: {stats['L1']}, L2: {stats['L2']}, L3: {stats['L3']}")


if __name__ == "__main__":
    main()
