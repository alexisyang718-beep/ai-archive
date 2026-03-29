#!/usr/bin/env python3
"""
Weibo 并行采集 → Atom JSONL 脚本
用法：
    python3 scripts/weibo_to_atoms.py                    # 全量采集今日
    python3 scripts/weibo_to_atoms.py --date 2026-03-20  # 指定日期
    python3 scripts/weibo_to_atoms.py --max-per-user 5  # 每人N条
"""

import json, os, sys, argparse, re
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import wait
import subprocess
import yaml

# ============ 配置 ============
BASE_DIR = Path(__file__).parent.parent / "v2" / "archive"
TODAY = datetime.now().strftime("%Y-%m-%d")

WEIBO_CLI = Path.home() / ".local" / "bin" / "weibo"
OBSIDIAN_VAULT = Path("~/Documents/Obsidian/资讯").expanduser()

# 分类关键词
CATEGORY_KEYWORDS = {
    "ai_models": ["AI", "大模型", "LLM", "GPT", "Claude", "Gemini", "DeepSeek", "ChatGPT", "AGI", "模型", "AGI", "AIGC", "生成式AI", "LLM", "多模态", "Agent", "智能体", "具身智能"],
    "mobile": ["手机", "iPhone", "华为", "小米", "OPPO", "vivo", "荣耀", "三星", "苹果", "折叠屏", "旗舰机", "平板", "穿戴", "耳机", "手表"],
    "chips": ["芯片", "处理器", "CPU", "GPU", "半导体", "晶圆", "光刻", "NVIDIA", "AMD", "英特尔", "高通", "麒麟", "昇腾", "GPU"],
    "gaming": ["游戏", "Steam", "Epic", "腾讯游戏", "网易游戏", "米哈游", "原神", "王者荣耀", "Unity", "虚幻引擎", "电竞", "主机", "PS5", "Xbox", "Switch"],
    "tech_industry": ["互联网", "腾讯", "阿里", "字节", "百度", "美团", "京东", "拼多多", "电商", "云计算", "SaaS", "数字化", "科技公司"],
    "policy": ["政策", "监管", "工信部", "商务部", "发改委", "反垄断", "数据安全", "合规", "出海", "制裁", "出口管制"],
}

AUTHOR_TYPE_MAP = {
    "official": ["官方", "官网", "有限公司"],
    "ceo_cto": ["CEO", "cto", "首席执行", "创始人", "董事长", "总裁"],
    "media": ["APP", "媒体", "周刊", "日报", "资讯", "新闻", "财经"],
    "kol": ["博主", "达人", "观察", "点评"],
}

def get_weibo_cli_path():
    if WEIBO_CLI.exists():
        return str(WEIBO_CLI)
    return "weibo"

def load_weibo_config():
    config_path = Path(__file__).parent.parent / "config" / "weibo_users.yaml"
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("weibo_users", [])

def fetch_user_weibo(uid, username, max_results=5):
    """用 UID 拉用户主页，30秒超时"""
    cmd = [get_weibo_cli_path(), "weibos", str(uid), "-n", str(max_results), "--json"]
    env = {**os.environ, "PATH": "/Users/yangliu/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"}
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            items = data.get("list", [])
            if items:
                return username, uid, items
    except Exception:
        pass
    return username, uid, []

def classify_category(text):
    """根据文本内容分类"""
    text_lower = text.lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[cat] = score
    if not scores:
        return "tech_industry"
    return max(scores, key=scores.get)

def detect_author_type(username, description=""):
    """根据用户名和描述判断作者类型"""
    text = f"{username} {description}".lower()
    if any(t in text for t in ["官方", "官网", "有限公司", "股份", "集团"]):
        return "official"
    if any(t in text for t in ["ceo", "cto", "首席", "创始人", "董事长", "总裁", "ceo"]):
        return "ceo_cto"
    if any(t in text for t in ["app", "媒体", "周刊", "资讯", "新闻", "财经", "日报"]):
        return "media"
    return "kol"

def extract_entities(text):
    """简单提取公司/产品实体"""
    entities = []
    companies = ["OpenAI", "DeepMind", "Meta", "Anthropic", "Google", "Microsoft", "Apple", "NVIDIA",
                 "字节", "腾讯", "阿里", "百度", "小米", "华为", "OPPO", "vivo", "荣耀", "三星",
                 "高通", "AMD", "英特尔", "Intel", "英伟达", "特斯拉", "比亚迪", "理想", "小鹏", "蔚来",
                 "美团", "京东", "拼多多", "网易", "快手", "抖音", "小红书"]
    for c in companies:
        if c in text:
            entities.append(c)
    return list(set(entities))[:5]

def parse_weibo_date(date_str):
    """解析微博时间字符串为 ISO 格式"""
    # 格式: "Fri Mar 20 16:51:13 +0800 2026"
    try:
        dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except:
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

def weibo_to_atom(weibo_item, username, uid, date):
    """将一条微博转换为 Atom 格式"""
    text = weibo_item.get("text", "")
    # 清理HTML标签
    text_clean = re.sub(r'<[^>]+>', '', text)

    # 生成 title（取前50字）
    title = text_clean[:80].strip()
    if len(text_clean) > 80:
        title += "..."

    # 提取URL
    urls = weibo_item.get("urls", [])
    url = urls[0] if urls else f"https://weibo.com/{uid}/{weibo_item.get('mid', '')}"

    # 判断内容类型
    if "官方" in username or "官方账号" in text_clean:
        content_type = "official"
    elif any(kw in text_clean for kw in ["刚刚", "获悉", "爆料", "独家", "内部"]):
        content_type = "exclusive"
    elif any(kw in text_clean for kw in ["评测", "体验", "上手", "实测", "测试"]):
        content_type = "firsthand_test"
    else:
        content_type = "report"

    # 信任等级
    author_type = detect_author_type(username)
    trust = "L1" if author_type in ("official", "ceo_cto") else "L2" if author_type == "media" else "L3"

    atom = {
        "id": "",  # 稍后生成
        "date": date,
        "title": title,
        "title_zh": title,
        "summary_zh": text_clean[:200] + ("..." if len(text_clean) > 200 else ""),
        "source": {
            "platform": "weibo",
            "author": username,
            "author_type": author_type,
            "url": url,
            "timestamp": parse_weibo_date(weibo_item.get("created_at", "")),
        },
        "content_type": content_type,
        "trust_default": trust,
        "trust_final": None,
        "trust_reason": None,
        "category": classify_category(text_clean),
        "tags": [],
        "entities": extract_entities(text_clean),
        "metrics": {
            "likes": weibo_item.get("attitudes_count", 0),
            "reposts": weibo_item.get("reposts_count", 0),
            "replies": weibo_item.get("comments_count", 0),
        },
        "in_daily_brief": False,
        "brief_date": None,
        "related_atoms": [],
        "full_text_fetched": False,
        "full_text_path": None,
    }
    return atom

def main():
    parser = argparse.ArgumentParser(description="Weibo → Atom JSONL")
    parser.add_argument("--date", default=TODAY)
    parser.add_argument("--max-per-user", type=int, default=20)
    parser.add_argument("--parallel", type=int, default=10)
    args = parser.parse_args()

    date = args.date
    max_per_user = args.max_per_user
    users = load_weibo_config()

    print(f"📡 开始并行采集 {len(users)} 个微博账号 ({date})...")

    # 并行拉取所有用户
    all_weibos = {}
    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = {
            executor.submit(fetch_user_weibo, u.get("uid", ""), u["name"], max_per_user): u
            for u in users if u.get("uid")
        }
        done = 0
        for future in as_completed(futures):
            done += 1
            username, uid, items = future.result()
            if items:
                all_weibos[username] = items
            print(f"  [{done}/{len(users)}] @{username}: {len(items)} 条", flush=True)

    print(f"\n✅ 成功采集 {len(all_weibos)} 个账号，共 {sum(len(v) for v in all_weibos.values())} 条微博")

    # 转换为 Atoms
    atoms = []
    uid_map = {u["name"]: u.get("uid", "") for u in users}
    now = datetime.now()
    cutoff = now - timedelta(hours=48)

    for username, weibos in all_weibos.items():
        uid = uid_map.get(username, "")
        for i, w in enumerate(weibos):
            # 时间过滤：跳过48小时前的帖子（移除时区信息以支持比较）
            ts_str = w.get("created_at", "")
            try:
                dt = datetime.strptime(ts_str, "%a %b %d %H:%M:%S %z %Y")
                dt_naive = dt.replace(tzinfo=None)  # 去掉时区，与cutoff统一
                if dt_naive < cutoff:
                    continue
            except Exception:
                pass

            atom = weibo_to_atom(w, username, uid, date)
            atom["id"] = f"weibo_{date.replace('-','')}_{len(atoms)+1:03d}"
            atoms.append(atom)

    print(f"📝 生成 {len(atoms)} 个 Atoms")

    # 保存到 JSONL
    daily_dir = Path(__file__).parent.parent / "v2" / "archive" / "daily" / date
    daily_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = daily_dir / f"weibo.jsonl"

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for atom in atoms:
            f.write(json.dumps(atom, ensure_ascii=False) + "\n")

    print(f"💾 已保存到 {jsonl_path}")

    # 同时保存一份原始 JSON（方便调试）
    raw_path = daily_dir / "weibo_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({"date": date, "users": {k: v for k, v in all_weibos.items()}}, f, ensure_ascii=False, indent=2)
    print(f"💾 原始JSON已保存到 {raw_path}")

    # 统计
    cats = {}
    for a in atoms:
        cat = a["category"]
        cats[cat] = cats.get(cat, 0) + 1
    print("\n📊 分类统计:")
    for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {cnt}")

    return len(atoms)

if __name__ == "__main__":
    sys.exit(main())