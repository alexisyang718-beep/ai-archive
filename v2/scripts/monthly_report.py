#!/usr/bin/env python3
"""
Monthly Report — 月报生成脚本（含趋势发现 + 跨天关联）

核心功能：
1. 30 天事件时间线（按公司/按主题两种视图）
2. Entity 频率统计 + 与上月环比
3. 跨天关联发现（"1号A新闻 + 10号B新闻 + 20号C新闻 → 趋势"）
4. 趋势信号自动识别

使用：
    python3 monthly_report.py                       # 当月
    python3 monthly_report.py --month 2026-03       # 指定月
"""

import sys, json, argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore

REPORTS_DIR = Path(__file__).parent.parent / "archive" / "reports" / "monthly"
OBSIDIAN_MONTHLY = Path("~/Documents/Obsidian/资讯/Monthly").expanduser()
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
OBSIDIAN_MONTHLY.mkdir(parents=True, exist_ok=True)

CATEGORY_NAMES = {
    "ai_models": "🤖 AI 模型与产品", "mobile": "📱 手机与消费电子",
    "chips": "🔧 芯片与算力", "gaming": "🎮 游戏行业",
    "tech_industry": "🏢 科技行业动态", "policy": "📜 政策与监管",
    "github": "📦 GitHub", "other": "📋 其他",
}


def get_month_range(month_str: str):
    """返回 (start_date, end_date) 格式 YYYY-MM-DD"""
    y, m = map(int, month_str.split("-"))
    start = f"{y}-{m:02d}-01"
    if m == 12: end_d = datetime(y+1, 1, 1) - timedelta(days=1)
    else: end_d = datetime(y, m+1, 1) - timedelta(days=1)
    return start, end_d.strftime("%Y-%m-%d")


def get_prev_month(month_str: str) -> str:
    y, m = map(int, month_str.split("-"))
    if m == 1: return f"{y-1}-12"
    return f"{y}-{m-1:02d}"


def find_trend_signals(atoms, prev_atoms):
    """
    趋势信号发现：
    1. 统计当月 entity 频率
    2. 对比上月 entity 频率
    3. 增长率 > 100% 或新增 entity → 标记为趋势信号
    """
    cur_ent = Counter()
    for a in atoms:
        for e in a.get("entities",[]): cur_ent[e] += 1

    prev_ent = Counter()
    for a in prev_atoms:
        for e in a.get("entities",[]): prev_ent[e] += 1

    signals = []
    for entity, count in cur_ent.most_common(50):
        prev_count = prev_ent.get(entity, 0)
        if prev_count == 0 and count >= 3:
            signals.append({"entity": entity, "cur": count, "prev": 0,
                           "type": "new", "desc": f"🆕 新兴话题：本月出现 {count} 次，上月未出现"})
        elif prev_count > 0:
            growth = (count - prev_count) / prev_count * 100
            if growth >= 100 and count >= 5:
                signals.append({"entity": entity, "cur": count, "prev": prev_count,
                               "type": "surge", "desc": f"🔥 热度暴增：{prev_count}→{count}（+{growth:.0f}%）"})
            elif growth >= 50 and count >= 5:
                signals.append({"entity": entity, "cur": count, "prev": prev_count,
                               "type": "rising", "desc": f"📈 持续上升：{prev_count}→{count}（+{growth:.0f}%）"})
    return signals


def find_cross_day_links(atoms):
    """
    跨天关联发现：找到同一 entity 在不同天的 atoms，形成事件链。
    返回：{entity: [{date, atoms}, ...]} 只返回跨 3 天以上的。
    """
    ent_timeline = defaultdict(lambda: defaultdict(list))
    for a in atoms:
        date = a.get("date","")
        for e in a.get("entities",[]):
            ent_timeline[e][date].append(a)

    chains = {}
    for entity, date_map in ent_timeline.items():
        if len(date_map) >= 3:  # 至少跨 3 天
            chains[entity] = sorted(date_map.items(), key=lambda x: x[0])
    return chains


def generate_monthly(store: AtomStore, month_str: str):
    start, end = get_month_range(month_str)
    atoms = store.query_by_date_range(start, end)
    if not atoms:
        print(f"⚠️ {month_str} 无数据"); return

    # 上月数据（用于环比）
    prev_month = get_prev_month(month_str)
    ps, pe = get_month_range(prev_month)
    prev_atoms = store.query_by_date_range(ps, pe)

    # 统计
    ent_freq = Counter()
    tag_freq = Counter()
    by_cat = defaultdict(list)
    by_date = defaultdict(list)

    for a in atoms:
        for e in a.get("entities",[]): ent_freq[e] += 1
        for t in a.get("tags",[]): tag_freq[t] += 1
        by_cat[a.get("category","other")].append(a)
        by_date[a.get("date","")].append(a)

    # 趋势信号
    signals = find_trend_signals(atoms, prev_atoms)
    # 跨天关联
    chains = find_cross_day_links(atoms)

    lines = [
        f"# 月报 {month_str}（{start} ~ {end}）", "",
        f"- 总 Atoms: **{len(atoms)}**",
        f"- 入选日报: **{sum(1 for a in atoms if a.get('in_daily_brief'))}**",
        f"- 上月 Atoms: **{len(prev_atoms)}**", "",
        "---", "",

        "## 🔥 趋势信号", "",
    ]

    if signals:
        lines += ["| Entity | 本月 | 上月 | 信号 |", "|--------|------|------|------|"]
        for s in signals[:15]:
            lines.append(f"| [[{s['entity']}]] | {s['cur']} | {s['prev']} | {s['desc']} |")
    else:
        lines.append("*暂无显著趋势信号*")

    lines += ["", "## 🔗 跨天事件链（同一实体 ≥3 天出现）", ""]
    for entity, timeline in sorted(chains.items(), key=lambda x: -len(x[1]))[:10]:
        lines.append(f"### [[{entity}]]（跨 {len(timeline)} 天）")
        for date, day_atoms in timeline:
            titles = [f"{(a.get('title_zh') or a.get('title',''))[:50]}" for a in day_atoms[:2]]
            lines.append(f"- **{date}**: {' / '.join(titles)}")
        lines.append("")

    lines += ["## 📊 TOP 30 Entities（环比）", "",
              "| # | Entity | 本月 | 上月 | 变化 |",
              "|---|--------|------|------|------|"]
    prev_ent = Counter()
    for a in prev_atoms:
        for e in a.get("entities",[]): prev_ent[e] += 1
    for i, (e, c) in enumerate(ent_freq.most_common(30), 1):
        pc = prev_ent.get(e, 0)
        delta = f"+{c-pc}" if c > pc else (f"{c-pc}" if c < pc else "=")
        lines.append(f"| {i} | [[{e}]] | {c} | {pc} | {delta} |")

    lines += ["", "## 📦 按板块汇总", ""]
    for cat in ["ai_models","mobile","chips","gaming","tech_industry","policy","github","other"]:
        ca = by_cat.get(cat, [])
        if not ca: continue
        sel = sum(1 for a in ca if a.get("in_daily_brief"))
        lines += [f"### {CATEGORY_NAMES.get(cat,cat)}", f"- 总量 {len(ca)} 条，精选 {sel} 条", ""]

    lines += ["", "---", "",
              "## 💡 月度复盘观察（TODO: AI/人工填写）", "",
              "> 综合以上趋势信号和跨天事件链，本月行业核心动向：", "",
              "1. ", "2. ", "3. ", ""]

    content = "\n".join(lines)
    p1 = REPORTS_DIR / f"{month_str}.md"
    p1.write_text(content, encoding="utf-8")
    print(f"✅ 月报写入: {p1}")

    p2 = OBSIDIAN_MONTHLY / f"{month_str}.md"
    p2.write_text(content, encoding="utf-8")
    print(f"✅ Obsidian 月报: {p2}")


def main():
    p = argparse.ArgumentParser(description="月报生成（含趋势发现）")
    p.add_argument("--month", default=None, help="指定月份，如 2026-03")
    args = p.parse_args()
    store = AtomStore()
    month = args.month or datetime.now().strftime("%Y-%m")
    generate_monthly(store, month)

if __name__ == "__main__":
    main()
