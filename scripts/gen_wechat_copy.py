#!/usr/bin/env python3
"""生成微信公众号「浏览器复制粘贴」专用 HTML：所有 inline style，table 模拟卡片"""
import re
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

# 路径基准：脚本所在目录的上级即 ai-daily-brief/
PROJECT_DIR = Path(__file__).resolve().parent.parent
BRIEF_DIR = PROJECT_DIR / "brief"

SRC = BRIEF_DIR / "2026-03-10.html"
DST = BRIEF_DIR / "2026-03-10-wechat-copy.html"

# 颜色
A = "#C96442"; T = "#1A1A1A"; T2 = "#6B6560"; T3 = "#9B9590"
BG = "#FAF9F5"; BGW = "#F5F0E8"; CARD = "#FFFFFF"
BD = "#E8E2D9"; BDL = "#F0EBE3"; IBG = "#FFF8F5"

TAG = {
    "tag-hot":("#C96442","#FEF0EB"), "tag-new":("#5A8F6B","#EBF5EE"),
    "tag-money":("#B8863B","#FBF4E8"), "tag-chip":("#7B6B9D","#F2EFF8"),
    "tag-agent":("#4A7B9D","#EBF2F7"), "tag-phone":("#4A8F8F","#EBF5F5"),
    "tag-policy":("#5A8F6B","#EBF5EE"), "tag-game":("#4A7B9D","#EBF2F7"),
}

def tag_span(el):
    c, bg = A, "#FEF0EB"
    for cls in el.get("class",[]):
        if cls in TAG: c, bg = TAG[cls]; break
    return (f'<span style="display:inline-block;font-size:12px;padding:2px 8px;'
            f'border-radius:20px;font-weight:500;color:{c};'
            f'background-color:{bg};margin-right:6px;">{el.get_text(strip=True)}</span>')

def fix_strong(html):
    return re.sub(r'<strong>', f'<strong style="color:{T};font-weight:600;">', html)

def fix_em(html):
    return re.sub(r'<em[^>]*>', f'<em style="color:{A};font-style:normal;font-weight:600;">', html)

def stat_span(el):
    t = fix_em(el.decode_contents())
    return (f'<span style="display:inline-block;background-color:{BGW};padding:4px 12px;'
            f'border-radius:20px;font-size:12px;color:{T2};'
            f'border:1px solid {BDL};margin-right:6px;margin-bottom:4px;">{t}</span>')

def source_html(el):
    h = el.decode_contents()
    h = re.sub(r'<a ', f'<a style="color:{A};text-decoration:none;font-weight:500;" ', h)
    return f'<p style="font-size:12px;color:{T3};padding-top:8px;margin-bottom:0;border-top:1px solid {BDL};">{h}</p>'

def card_wrap(inner, bg=CARD):
    return (f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom:14px;">'
            f'<tr><td style="background-color:{bg};border:1px solid {BDL};'
            f'border-radius:12px;padding:18px 22px;">{inner}</td></tr></table>')

soup = BeautifulSoup(SRC.read_text("utf-8"), "html.parser")
P = []

# ─── 标题 ───
P.append(f'<div style="text-align:center;padding:40px 0 20px;">'
         f'<h1 style="font-size:28px;font-weight:700;color:{T};margin-bottom:6px;font-family:Georgia,serif;">AI Daily Brief</h1>'
         f'<p style="color:{T3};font-size:14px;">2026年3月10日 · 周二</p>'
         f'<div style="width:40px;height:2px;background-color:{A};margin:20px auto;"></div></div>')

# ─── 核心洞察 ───
sc = soup.select_one(".summary-card")
if sc:
    P.append(f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom:24px;">'
             f'<tr><td style="background-color:{BGW};border:1px solid {BD};border-radius:12px;'
             f'padding:20px 24px;font-size:15px;line-height:1.9;color:{T2};">'
             f'{fix_strong(sc.decode_contents())}</td></tr></table>')

# ─── 目录 ───
toc = soup.select_one(".toc")
if toc:
    items = toc.select("li a")
    rows = ""
    for i in range(0, len(items), 2):
        cells = ""
        for j in range(2):
            if i+j < len(items):
                a = items[i+j]
                ic = a.select_one(".toc-icon")
                icon = ic.get_text(strip=True) if ic else ""
                txt = a.get_text(strip=True).replace(icon,"",1).strip() if icon else a.get_text(strip=True)
                cells += f'<td style="padding:6px 8px;font-size:14px;color:{T2};">{icon} {txt}</td>'
            else:
                cells += '<td></td>'
        rows += f'<tr>{cells}</tr>'
    P.append(f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom:28px;">'
             f'<tr><td style="background-color:{CARD};border:1px solid {BD};border-radius:12px;padding:20px 24px;">'
             f'<p style="font-size:11px;font-weight:600;color:{T3};letter-spacing:1.5px;margin-bottom:12px;">目录</p>'
             f'<table cellpadding="0" cellspacing="0" border="0" width="100%">{rows}</table>'
             f'</td></tr></table>')

# ─── 分隔线 ───
P.append(f'<div style="height:1px;background-color:{BD};margin:24px 0;"></div>')

# ─── 各板块 ───
for sec in soup.select("section.section"):
    sh = sec.select_one(".section-header")
    if sh:
        ic = sh.select_one(".icon")
        icon = ic.get_text(strip=True) if ic else ""
        h2 = sh.select_one("h2")
        title = h2.get_text(strip=True) if h2 else ""
        P.append(f'<div style="margin-top:40px;margin-bottom:16px;padding-bottom:10px;border-bottom:1px solid {BD};">'
                 f'<h2 style="font-size:20px;font-weight:600;color:{T};font-family:Georgia,serif;">{icon} {title}</h2></div>')

    # GitHub 项目
    gh = sec.select(".gh-item")
    if gh:
        cells = []
        for g in gh:
            ne = g.select_one(".gh-name"); de = g.select_one(".gh-desc"); se = g.select_one(".gh-star")
            nh = ""
            if ne:
                aa = ne.select_one("a")
                if aa:
                    nh = f'<a href="{aa.get("href","#")}" style="color:{A};text-decoration:none;font-weight:600;font-size:13px;">{aa.get_text(strip=True)}</a>'
                else:
                    nh = f'<span style="font-weight:600;font-size:13px;">{ne.get_text(strip=True)}</span>'
            dd = de.get_text(strip=True) if de else ""
            ss = se.get_text(strip=True) if se else ""
            cells.append(f'<td style="background-color:{CARD};border:1px solid {BDL};border-radius:10px;'
                        f'padding:14px 16px;vertical-align:top;width:50%;">'
                        f'<p style="margin-bottom:6px;">{nh}</p>'
                        f'<p style="font-size:12px;color:{T2};line-height:1.6;margin-bottom:6px;">{dd}</p>'
                        f'<p style="font-size:12px;color:#B8863B;font-weight:500;">{ss}</p></td>')
        rows = ""
        for i in range(0, len(cells), 2):
            rows += "<tr>" + cells[i] + (cells[i+1] if i+1<len(cells) else "<td></td>") + "</tr>"
        P.append(f'<table cellpadding="4" cellspacing="8" border="0" width="100%" style="margin-bottom:16px;">{rows}</table>')
        continue

    # 新闻条目
    for item in sec.select(".item"):
        inner = ""
        # 标题+tag
        te = item.select_one(".item-title")
        if te:
            tags = "".join(tag_span(t) for t in te.select(".tag"))
            for t in te.select(".tag"): t.decompose()
            txt = te.get_text(strip=True)
            inner += f'<p style="font-size:16px;font-weight:600;color:{T};margin-bottom:8px;line-height:1.5;">{tags}{txt}</p>'
        # 正文
        be = item.select_one(".item-body")
        if be:
            bh = fix_strong(be.decode_contents())
            inner += f'<div style="font-size:14px;color:{T2};line-height:1.85;margin-bottom:10px;">{bh}</div>'
        # 统计标签
        sr = item.select_one(".stat-row")
        if sr:
            stats = "".join(stat_span(s) for s in sr.select(".stat"))
            inner += f'<p style="margin:10px 0;">{stats}</p>'
        # 来源
        so = item.select_one(".item-source")
        if so:
            inner += source_html(so)
        # 洞察 —— 用 table 包裹确保底色在微信中保留
        ib = item.select_one(".insight-box")
        if ib:
            lbl = ib.select_one(".insight-label")
            cnt = ib.select_one(".insight-content")
            lbl_t = lbl.get_text(strip=True) if lbl else "💡 深度洞察"
            cnt_h = fix_strong(cnt.decode_contents()) if cnt else ""
            inner += (f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top:14px;">'
                     f'<tr><td style="background-color:{IBG};border-top:2px solid {A};'
                     f'border-radius:0 0 10px 10px;padding:14px 18px;font-size:14px;color:{T2};line-height:1.85;">'
                     f'<p style="color:{A};font-size:15px;font-weight:bold;margin-bottom:10px;">{lbl_t}</p>'
                     f'<div style="line-height:1.85;">{cnt_h}</div>'
                     f'</td></tr></table>')
        P.append(card_wrap(inner))

# ─── 页脚 ───
P.append(f'<div style="text-align:center;padding:40px 0 50px;border-top:1px solid {BD};margin-top:32px;">'
         f'<p style="font-size:14px;font-weight:600;color:{T2};margin-bottom:4px;font-family:Georgia,serif;">AI Daily Brief</p>'
         f'<p style="color:{T3};font-size:12px;line-height:2;">由 AI 编辑团队策展 · 每日更新<br>内容综合自全球科技媒体与官方信源</p></div>')

# ─── 输出 ───
body = "\n".join(P)
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>AI Daily Brief - 微信复制版</title></head>
<body style="font-family:-apple-system,'PingFang SC','Noto Sans SC',sans-serif;background:{BG};color:{T};line-height:1.8;margin:0;padding:0;">
<div style="max-width:780px;margin:0 auto;padding:0 24px;">
{body}
</div>
</body>
</html>'''

DST.write_text(html, encoding="utf-8")
print(f"✅ 已生成: {DST}")
print(f"   大小: {len(html):,} bytes")
