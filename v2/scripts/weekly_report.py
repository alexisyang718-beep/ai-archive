#!/usr/bin/env python3
"""
Weekly Report — 周报生成脚本

读取 7 天的 Atoms → 按 entity/tag 聚合 → 输出周报 Markdown。

使用：
    python3 weekly_report.py                       # 当前周
    python3 weekly_report.py --week 2026-W12       # 指定周
    python3 weekly_report.py --from-date 2026-03-11 --to-date 2026-03-17
"""

import sys, json, argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore

REPORTS_DIR = Path(__file__).parent.parent / "archive" / "reports" / "weekly"
OBSIDIAN_WEEKLY = Path("~/Documents/Obsidian/资讯/Weekly").expanduser()
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
OBSIDIAN_WEEKLY.mkdir(parents=True, exist_ok=True)

CATEGORY_NAMES = {
    "ai_models": "🤖 AI 模型与产品", "mobile": "📱 手机与消费电子",
    "chips": "🔧 芯片与算力", "gaming": "🎮 游戏行业",
    "tech_industry": "🏢 科技行业动态", "policy": "📜 政策与监管",
    "github": "📦 GitHub", "other": "📋 其他",
}


def generate_weekly(store: AtomStore, start: str, end: str, week_label: str):
    atoms = store.query_by_date_range(start, end)
    if not atoms:
        print(f"⚠️ {start}~{end} 无数据"); return

    # 统计
    ent_freq = Counter()
    tag_freq = Counter()
    by_cat = defaultdict(list)
    by_date = defaultdict(list)
    by_trust = Counter()

    for a in atoms:
        for e in a.get("entities",[]): ent_freq[e] += 1
        for t in a.get("tags",[]): tag_freq[t] += 1
        by_cat[a.get("category","other")].append(a)
        by_date[a.get("date","")].append(a)
        by_trust[a.get("trust_default","L3")] += 1

    lines = [
        f"# 周报 {week_label}（{start} ~ {end}）", "",
        f"- 总 Atoms: **{len(atoms)}**",
        f"- 入选日报: **{sum(1 for a in atoms if a.get('in_daily_brief'))}**",
        f"- 置信度分布: L1={by_trust.get('L1',0)}, L2={by_trust.get('L2',0)}, L3={by_trust.get('L3',0)}", "",
        "---", "",
        "## 🔥 TOP 20 Entities（本周最热公司/产品）", "",
        "| # | Entity | 出现次数 |", "|---|--------|---------|",
    ]
    for i, (e, c) in enumerate(ent_freq.most_common(20), 1):
        lines.append(f"| {i} | [[{e}]] | {c} |")

    lines += ["", "## 🏷️ TOP 20 Tags", "",
              "| # | Tag | 次数 |", "|---|-----|------|"]
    for i, (t, c) in enumerate(tag_freq.most_common(20), 1):
        lines.append(f"| {i} | #{t} | {c} |")

    lines += ["", "## 📊 按板块汇总", ""]
    for cat in ["ai_models","mobile","chips","gaming","tech_industry","policy","github","other"]:
        ca = by_cat.get(cat, [])
        if not ca: continue
        lines += [f"### {CATEGORY_NAMES.get(cat,cat)} ({len(ca)} 条)", ""]
        selected = [a for a in ca if a.get("in_daily_brief")]
        if selected:
            lines.append("**入选日报：**")
            for a in selected:
                title = (a.get("title_zh") or a.get("title",""))[:60]
                lines.append(f"- [{a['date']}] {title}")
            lines.append("")
        lines.append(f"总量 {len(ca)} 条（精选 {len(selected)}）\n")

    lines += ["", "## 📅 每日数据量", "",
              "| 日期 | 总量 | 精选 | L1 | L2 | L3 |",
              "|------|------|------|----|----|-----|"]
    for d in sorted(by_date.keys()):
        da = by_date[d]
        sel = sum(1 for a in da if a.get("in_daily_brief"))
        l1 = sum(1 for a in da if a.get("trust_default")=="L1")
        l2 = sum(1 for a in da if a.get("trust_default")=="L2")
        l3 = sum(1 for a in da if a.get("trust_default")=="L3")
        lines.append(f"| {d} | {len(da)} | {sel} | {l1} | {l2} | {l3} |")

    lines += ["", "---", "",
              "## 💡 趋势信号（TODO: AI 辅助分析）", "",
              "> 以下区域供 AI 或人工填写本周趋势观察：", "",
              "1. ", "2. ", "3. ", ""]

    content = "\n".join(lines)

    # 写入 archive
    p1 = REPORTS_DIR / f"{week_label}.md"
    p1.write_text(content, encoding="utf-8")
    print(f"✅ 周报写入: {p1}")

    # 写入 Obsidian
    p2 = OBSIDIAN_WEEKLY / f"{week_label}.md"
    p2.write_text(content, encoding="utf-8")
    print(f"✅ Obsidian 周报: {p2}")


def main():
    p = argparse.ArgumentParser(description="周报生成")
    p.add_argument("--week", help="指定周，如 2026-W12")
    p.add_argument("--from-date", dest="from_date")
    p.add_argument("--to-date", dest="to_date")
    args = p.parse_args()

    store = AtomStore()

    if args.from_date and args.to_date:
        start, end = args.from_date, args.to_date
        week_label = f"{start}_to_{end}"
    elif args.week:
        # ISO week → date range
        y, w = args.week.split("-W")
        d = datetime.strptime(f"{y}-W{w}-1", "%Y-W%W-%w")
        start = d.strftime("%Y-%m-%d")
        end = (d + timedelta(days=6)).strftime("%Y-%m-%d")
        week_label = args.week
    else:
        # 当前周（周一到今天）
        today = datetime.now()
        mon = today - timedelta(days=today.weekday())
        start = mon.strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
        week_label = today.strftime("%Y-W%W")

    generate_weekly(store, start, end, week_label)

if __name__ == "__main__":
    main()
