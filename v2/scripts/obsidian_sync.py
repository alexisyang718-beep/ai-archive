#!/usr/bin/env python3
"""
Obsidian Sync — JSONL → Obsidian Markdown 同步脚本

职责：
1. 读取 archive/daily/YYYY-MM-DD.jsonl
2. 生成 Obsidian Markdown 笔记（Daily/ Entities/ Topics/）
3. 使用 wiki-link 建立笔记间的关联

使用：
    python3 obsidian_sync.py                       # 同步今天
    python3 obsidian_sync.py --date 2026-03-18     # 指定日期
    python3 obsidian_sync.py --from-date 2026-03-01 --to-date 2026-03-18  # 范围
"""

import json, sys, os, re, argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore

# ============ 配置 ============
OBSIDIAN_VAULT = Path("~/Documents/Obsidian/资讯").expanduser()

CATEGORY_NAMES = {
    "ai_models": "🤖 AI 模型与产品", "mobile": "📱 手机与消费电子",
    "chips": "🔧 芯片与算力", "gaming": "🎮 游戏行业",
    "tech_industry": "🏢 科技行业动态", "policy": "📜 政策与监管",
    "github": "📦 GitHub", "other": "📋 其他",
}
TRUST_LABELS = {"L1": "🟢 L1 一手源", "L2": "🟡 L2 权威报道", "L3": "🟠 L3 二手转载"}
CONTENT_TYPE_LABELS = {
    "official": "官方公告", "exclusive": "独家爆料", "firsthand_test": "一手实测",
    "original_analysis": "原创分析", "report": "媒体报道", "interview": "采访",
    "commentary": "评论观点", "translation": "翻译编译", "repost": "转载",
}


# 渠道配置
CHANNEL_NAMES = {
    "x": "📱 X/Twitter",
    "weibo": "📡 微博",
    "rss": "📰 RSS",
}
CHANNEL_ICONS = {
    "x": "📱",
    "weibo": "📡",
    "rss": "📰",
}


class ObsidianSyncer:
    def __init__(self, vault_path: Optional[Path] = None):
        self.vault = vault_path or OBSIDIAN_VAULT
        self.daily_dir = self.vault / "Daily"
        self.entity_dir = self.vault / "Entities"
        self.topic_dir = self.vault / "Topics"
        self.store = AtomStore()
        for d in [self.daily_dir, self.entity_dir, self.topic_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def generate_daily_note(self, date: str, channel_dir: Path) -> Optional[Path]:
        """生成每日预选题笔记：按话题聚合，显示内容数量和权威信源"""
        # 汇总所有渠道（去重）
        atoms = self.store.query_by_date(date)
        if not atoms:
            print(f"  ⚠️ {date} 没有数据，跳过"); return None
        
        # 按 URL 再次去重（同一内容可能在不同渠道有不同ID）
        seen_urls = set()
        unique_atoms = []
        for a in atoms:
            url = a.get("source", {}).get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_atoms.append(a)
            elif not url:
                unique_atoms.append(a)
        atoms = unique_atoms
        print(f"  📝 URL去重后: {len(atoms)} 条")

        # 统计渠道数量
        from atom_store import CHANNELS
        channel_counts = {}
        for ch in CHANNELS:
            ch_atoms = self.store.query_by_date_channel_raw(date, ch)
            channel_counts[ch] = len(ch_atoms)

        lines = ["---", f"date: {date}",
                 f"total_atoms: {len(atoms)}",
                 f"channels: x={channel_counts.get('x',0)}, weibo={channel_counts.get('weibo',0)}, rss={channel_counts.get('rss',0)}",
                 "---", "",
                 f"# {date} 科技资讯预选题", "",
                 f"📊 采集概况: X({channel_counts.get('x',0)}) + 微博({channel_counts.get('weibo',0)}) + RSS({channel_counts.get('rss',0)}) = **{len(atoms)} 条**",
                 "",
                 "## 📁 渠道详情", ""]

        # 链接到各渠道笔记
        for ch in ["x", "weibo", "rss"]:
            if channel_counts.get(ch, 0) > 0:
                lines.append(f"- [[{ch}|{CHANNEL_NAMES.get(ch, ch)}]]: {channel_counts[ch]} 条")
        lines.append("")

        # 按话题聚合（去重后）
        lines += ["---", "", "## 🔥 预选题池（按话题聚合）", ""]

        # 按分类 -> 话题 -> 内容 聚合
        by_cat = defaultdict(lambda: defaultdict(list))
        for a in atoms:
            cat = a.get("category", "other")
            # 用实体或标题关键词作为话题
            entities = a.get("entities", [])
            topic = entities[0] if entities else a.get("title", "其他")[:30]
            by_cat[cat][topic].append(a)

        for cat, topics in sorted(by_cat.items()):
            lines += [f"### {CATEGORY_NAMES.get(cat, cat)}", ""]

            # 按话题数量排序
            sorted_topics = sorted(topics.items(), key=lambda x: len(x[1]), reverse=True)

            for topic, topic_atoms in sorted_topics[:10]:  # 每类最多10个话题
                # 按权威度排序
                trust_order = {"L1": 0, "L2": 1, "L3": 2}
                sorted_atoms = sorted(topic_atoms, key=lambda a: trust_order.get(a.get("trust_default", "L3"), 2))

                # 取最权威的前3条
                top_atoms = sorted_atoms[:3]

                lines.append(f"#### {topic} ({len(topic_atoms)} 条)")

                for a in top_atoms:
                    t = a.get("trust_final") or a.get("trust_default", "L3")
                    author = a.get("source", {}).get("author", "")
                    url = a.get("source", {}).get("url", "")
                    title = (a.get("title_zh") or a.get("title", ""))[:60]
                    lines.append(f"- [{title}]({url}) — {author} `{t}`")

                lines.append("")

        md = self.daily_dir / f"{date}.md"
        md.write_text("\n".join(lines), encoding="utf-8")
        print(f"  ✅ 每日笔记: {md}"); return md

    def update_entity_notes(self, date: str):
        """按 entity 追加到 Entities/ 笔记"""
        atoms = self.store.query_by_date(date)
        ea = defaultdict(list)
        for a in atoms:
            for e in a.get("entities",[]): ea[e].append(a)
        for entity, eatoms in ea.items():
            self._append_entity(entity, date, eatoms)
        print(f"  ✅ 更新 {len(ea)} 个 Entity 笔记")

    def _append_entity(self, entity, date, atoms):
        safe = entity.replace("/","-").replace("\\","-").replace(":","-")
        md = self.entity_dir / f"{safe}.md"
        new = [f"### {date}"]
        for a in atoms:
            t = a.get("trust_final") or a.get("trust_default","L3")
            title = (a.get("title_zh") or a.get("title",""))[:80]
            url = a.get("source",{}).get("url","")
            author = a.get("source",{}).get("author","")
            new += [f"- [{title}]({url})", f"  - 信源: {author} `{TRUST_LABELS.get(t,t)}`",
                    f"  - ← [[{date}]]"]
        new.append("")
        if md.exists():
            c = md.read_text(encoding="utf-8")
            if f"### {date}" in c: return
            m = re.search(r'\n(### \d{4}-\d{2}-\d{2})', c)
            if m: c = c[:m.start()+1] + "\n".join(new) + "\n" + c[m.start()+1:]
            else: c += "\n" + "\n".join(new)
            md.write_text(c, encoding="utf-8")
        else:
            lines = ["---", f"entity: {entity}", f"created: {date}", "---", "",
                     f"# {entity} 新闻时间线", ""] + new
            md.write_text("\n".join(lines), encoding="utf-8")

    def update_topic_notes(self, date: str):
        """按板块追加到 Topics/ 笔记"""
        atoms = self.store.query_by_date(date)
        by_cat = defaultdict(list)
        for a in atoms: by_cat[a.get("category","other")].append(a)
        TF = {"ai_models":"AI-Models.md","mobile":"Mobile.md","chips":"Chips.md",
              "gaming":"Gaming.md","tech_industry":"Tech-Industry.md","policy":"Policy.md","github":"GitHub.md"}
        for cat, ca in by_cat.items():
            fn = TF.get(cat)
            if not fn: continue
            self._append_topic(fn, cat, date, ca)
        print(f"  ✅ 更新 {len(by_cat)} 个 Topic 笔记")

    def _append_topic(self, fn, cat, date, atoms):
        md = self.topic_dir / fn
        new = [f"### {date} ({len(atoms)} 条)"]
        for a in atoms:
            title = (a.get("title_zh") or a.get("title",""))[:80]
            url = a.get("source",{}).get("url","")
            new.append(f"- [{title}]({url}) ← [[{date}]]")
        new.append("")
        if md.exists():
            c = md.read_text(encoding="utf-8")
            if f"### {date}" in c: return
            m = re.search(r'\n(### \d{4}-\d{2}-\d{2})', c)
            if m: c = c[:m.start()+1] + "\n".join(new) + "\n" + c[m.start()+1:]
            else: c += "\n" + "\n".join(new)
            md.write_text(c, encoding="utf-8")
        else:
            lines = ["---", f"topic: {cat}", f"created: {date}", "---", "",
                     f"# {CATEGORY_NAMES.get(cat,cat)}", ""] + new
            md.write_text("\n".join(lines), encoding="utf-8")

    def _fmt(self, atom, compact=False):
        title = (atom.get("title_zh") or atom.get("title","无标题"))[:80]
        author = atom.get("source",{}).get("author","")
        url = atom.get("source",{}).get("url","")
        t = atom.get("trust_final") or atom.get("trust_default","L3")
        tags = atom.get("tags",[])
        if compact:
            return [f"- [{title}]({url}) — {author} `{t}` {' '.join(f'#{x}' for x in tags[:3])}"]
        entities = atom.get("entities",[])
        ct = CONTENT_TYPE_LABELS.get(atom.get("content_type",""),"")
        cat = CATEGORY_NAMES.get(atom.get("category",""),"")
        lines = [f"### {title}", f"- **信源**: [{author}]({url}) `{TRUST_LABELS.get(t,t)}`"]
        if ct: lines.append(f"- **类型**: {ct}")
        if cat: lines.append(f"- **板块**: {cat}")
        if tags: lines.append(f"- **标签**: {' '.join(f'#{x}' for x in tags)}")
        if entities: lines.append(f"- **实体**: {', '.join(f'[[{e}]]' for e in entities)}")
        s = atom.get("summary_zh","")
        if s: lines.append(f"- **摘要**: {s[:200]}")
        return lines

    def generate_channel_notes(self, date: str, channel_dir: Path):
        """为每个渠道生成独立的 Markdown 笔记（渠道内不去重）"""
        from atom_store import CHANNELS
        
        # 渠道文件名编号映射
        channel_prefix = {"x": "01", "weibo": "02", "rss": "03"}
        
        for channel in CHANNELS:
            # 直接从渠道文件读取，不做去重
            atoms = self.store.query_by_date_channel_raw(date, channel)
            if not atoms:
                continue
            
            lines = ["---", f"date: {date}", f"channel: {channel}", 
                     f"total_atoms: {len(atoms)}", "---", "",
                     f"# {CHANNEL_NAMES.get(channel, channel)} — {date}", ""]
            
            # 按分类分组
            by_cat = defaultdict(list)
            for a in atoms:
                by_cat[a.get("category", "other")].append(a)
            
            for cat, ca in sorted(by_cat.items()):
                lines += [f"## {CATEGORY_NAMES.get(cat, cat)} ({len(ca)} 条)", ""]
                for a in ca:
                    lines += self._fmt(a, compact=False) + [""]
            
            prefix = channel_prefix.get(channel, "00")
            md = channel_dir / f"{prefix}_{channel}.md"
            md.write_text("\n".join(lines), encoding="utf-8")
            print(f"  ✅ 渠道笔记: {prefix}_{channel}.md ({len(atoms)} 条)")
    
    def sync_date(self, date):
        print(f"\n📝 同步 {date} 到 Obsidian")
        
        # 创建 Daily/日期/ 子目录
        day_dir = self.daily_dir / date
        day_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成渠道笔记（在 Daily/日期/ 下）
        self.generate_channel_notes(date, day_dir)
        
        # 生成每日预选题笔记（汇总，去重）
        self.generate_daily_note(date, day_dir)
        
        # 更新实体和话题笔记
        self.update_entity_notes(date)
        self.update_topic_notes(date)
        
        print(f"  ✅ {date} 同步完成")

    def sync_range(self, start, end):
        cur = datetime.strptime(start, "%Y-%m-%d")
        e = datetime.strptime(end, "%Y-%m-%d")
        while cur <= e:
            self.sync_date(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=1)


def main():
    p = argparse.ArgumentParser(description="Obsidian 同步")
    p.add_argument("--date", default=None)
    p.add_argument("--from-date", dest="from_date")
    p.add_argument("--to-date", dest="to_date")
    p.add_argument("--entities-only", action="store_true")
    p.add_argument("--vault", default=None, help="Obsidian vault 路径")
    args = p.parse_args()

    vault = Path(args.vault).expanduser() if args.vault else None
    syncer = ObsidianSyncer(vault)

    if args.from_date and args.to_date:
        syncer.sync_range(args.from_date, args.to_date)
    else:
        date = args.date or datetime.now().strftime("%Y-%m-%d")
        if args.entities_only:
            syncer.update_entity_notes(date)
        else:
            syncer.sync_date(date)

if __name__ == "__main__":
    main()
