#!/usr/bin/env python3
"""
过滤X数据 - 按时间范围筛选并重新分类

使用方式：
    python3 filter_x_data.py --date 2026-03-23 --start-time "2026-03-23 10:00"
"""

import json
import sys
import shutil
from datetime import datetime
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore

# 6大板块关键词映射
CATEGORY_KEYWORDS = {
    "ai_models": [
        "openai", "gpt", "chatgpt", "gpt-4", "gpt-4o", "gpt-5", "o1", "o3",
        "claude", "anthropic", "sonnet", "opus",
        "gemini", "google", "bard", "deepmind",
        "llama", "meta", "meta ai",
        "kimi", "月之暗面", "moonshot",
        "deepseek", "深度求索",
        "qwen", "通义千问", "通义", "阿里",
        "智谱", "glm", "glm-5", "chatglm",
        "minimax", "海螺",
        "stepfun", "阶跃",
        "baichuan", "百川",
        "01.ai", "零一",
        "yi", "李开复",
        "ai模型", "大模型", "llm", "多模态",
        "agent", "智能体", "ai助手",
        "manus", "cursor", "windsurf", "devin",
        "ai写作", "ai绘画", "ai视频", "ai音乐",
    ],
    "mobile": [
        "iphone", "ipad", "macbook", "apple", "ios", "vision pro",
        "samsung", "galaxy", "android",
        "xiaomi", "小米", "红米", "redmi", "澎湃",
        "huawei", "华为", "鸿蒙", "harmonyos", "mate", "pura",
        "oppo", "vivo", "一加", "oneplus", "iqoo", "realme",
        "honor", "荣耀",
        "pixel", "google",
        "smartphone", "手机", "平板", "可穿戴",
        "折叠屏", "fold", "flip",
        "芯片", "soc", "处理器",
    ],
    "chips": [
        "nvidia", "英伟达", "黄仁勋", "jensen huang",
        "tsmc", "台积电",
        "intel", "英特尔", "amd",
        "gpu", "芯片", "semiconductor", "半导体",
        "ai芯片", "ai chip",
        "h100", "h200", "b100", "b200", "gb200", "blackwell",
        "a100", "cuda",
        "昇腾", "ascend", "华为芯片",
        "算力", "compute", "数据中心",
        "ai服务器", "ai infrastructure",
        "制程", "nm工艺", "晶圆",
        "高通", "qualcomm", "联发科", "mediatek",
        "npu", "tpu",
        "光刻机", "asml",
        "特斯拉", "tesla", "马斯克",
        "比亚迪", "byd", "蔚来", "nio", "小鹏", "xpeng",
        "理想汽车", "li auto",
        "电动车", "电动汽车", "ev",
        "自动驾驶", "autonomous driving",
        "智能驾驶", "智驾", "lidar",
    ],
    "gaming": [
        "nintendo", "switch", "switch 2", "ns2", "任天堂", "马里奥", "塞尔达", "zelda",
        "sony", "playstation", "ps5", "ps5 pro", "ps6", "playstation 5",
        "microsoft", "xbox", "xbox series",
        "steam", "steam deck", "valve",
        "游戏", "game", "gaming", "主机游戏", "掌机",
        "黑神话", "悟空", "wukong", "game science",
        "原神", "genshin", "米哈游", "mihoyo",
        "王者荣耀", "和平精英",
        "gta", "gta6", "侠盗猎车",
        "gdc", "游戏开发者大会",
        "ign", "gamespot", "metacritic",
    ],
    "tech_industry": [
        "腾讯", "tencent", "微信", "wechat",
        "阿里巴巴", "alibaba", "淘宝", "天猫",
        "字节跳动", "bytedance", "抖音", "tiktok",
        "百度", "baidu",
        "美团", "meituan",
        "京东", "jd",
        "拼多多", "pinduoduo",
        "网易", "netease",
        "bilibili", "哔哩哔哩",
        "小红书",
        "meta", "facebook", "instagram", "whatsapp",
        "amazon", "aws",
        "google", "alphabet", "youtube",
        "microsoft", "azure",
        "apple",
        "netflix", "spotify",
        "uber", "airbnb",
        "startup", "独角兽", "融资", "ipo", "上市",
        "并购", "acquisition", "投资",
        "财报", "earnings", "revenue",
        "裁员", "layoff",
    ],
    "policy": [
        "监管", "regulation",
        "反垄断", "antitrust",
        "数据安全", "data security", "隐私", "privacy",
        "gdpr",
        "出口管制", "export control", "制裁", "sanction",
        "关税", "tariff",
        "中美", "china us", "贸易战",
        "欧盟", "european union",
        "人工智能法案", "ai act",
        "算法备案",
        "内容审核", "content moderation",
        "网络安全", "cybersecurity",
        "芯片法案", "chips act",
        "通胀削减法案", "ira",
    ],
}


def parse_timestamp(ts_str: str) -> datetime:
    """解析时间戳"""
    if not ts_str:
        return datetime.min
    try:
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt)
            except:
                continue
        if "T" in ts_str:
            ts_str = ts_str.replace("T", " ")[:16]
            return datetime.strptime(ts_str, "%Y-%m-%d %H:%M")
    except:
        pass
    return datetime.min


def classify_content(text: str) -> str:
    """基于关键词分类内容"""
    text_lower = text.lower()
    scores = {}
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw.lower() in text_lower:
                score += 1
        if score > 0:
            scores[category] = score
    
    if scores:
        return max(scores, key=scores.get)
    return "tech_industry"  # 默认分类


def filter_and_reclassify(date: str, start_time_str: str):
    """
    过滤时间范围并重新分类
    
    Args:
        date: 日期 YYYY-MM-DD
        start_time_str: 开始时间 "YYYY-MM-DD HH:MM"
    """
    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
    
    print(f"\n{'='*60}")
    print(f"🔍 过滤X数据")
    print(f"{'='*60}")
    print(f"日期: {date}")
    print(f"时间范围: {start_time_str} 至今")
    
    # 读取数据
    store = AtomStore()
    atoms = store.query_by_date_channel(date, "x")
    
    print(f"\n原始数据: {len(atoms)} 条")
    
    # 备份
    date_path = store.base_dir / "daily" / date
    backup_path = store.base_dir / "backup" / date
    backup_path.mkdir(parents=True, exist_ok=True)
    
    x_file = date_path / "x.jsonl"
    backup_file = backup_path / f"x_filtered_{datetime.now().strftime('%H%M%S')}.jsonl"
    
    if x_file.exists():
        shutil.copy2(x_file, backup_file)
        print(f"已备份: {backup_file}")
    
    # 过滤和重新分类
    filtered_atoms = []
    for atom in atoms:
        ts_str = atom.get("source", {}).get("timestamp", "")
        tweet_time = parse_timestamp(ts_str)
        
        if tweet_time >= start_time:
            # 重新分类
            text = atom.get("summary_zh", "") or atom.get("title", "")
            new_category = classify_content(text)
            atom["category"] = new_category
            
            # 更新tags
            tags = []
            for cat, keywords in CATEGORY_KEYWORDS.items():
                for kw in keywords:
                    if kw.lower() in text.lower():
                        tags.append(kw.lower().replace(" ", "_"))
            atom["tags"] = list(set(tags))[:5]  # 最多5个tags
            
            filtered_atoms.append(atom)
    
    print(f"过滤后: {len(filtered_atoms)} 条")
    
    # 统计
    cats = Counter(a.get("category", "unknown") for a in filtered_atoms)
    print(f"\n板块分布:")
    for cat, count in cats.most_common():
        print(f"  {cat}: {count}")
    
    # 保存
    if filtered_atoms:
        with open(x_file, 'w', encoding='utf-8') as f:
            for atom in filtered_atoms:
                f.write(json.dumps(atom, ensure_ascii=False) + '\n')
        print(f"\n💾 已保存 {len(filtered_atoms)} 条到 x.jsonl")
    else:
        print("\n⚠️ 没有数据需要保存")
    
    print(f"{'='*60}")
    
    return filtered_atoms


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="过滤X数据")
    parser.add_argument("--date", default="2026-03-23", help="日期")
    parser.add_argument("--start-time", default="2026-03-23 10:00", help="开始时间")
    args = parser.parse_args()
    
    filter_and_reclassify(args.date, args.start_time)
