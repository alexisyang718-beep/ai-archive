#!/usr/bin/env python3
"""
Atom Store — v2 系统核心存储引擎（简化版）

职责：
1. 将 Atom 写入 JSONL 文件（按日期文件夹存储）
2. 按日期/渠道检索 Atoms
3. 生成唯一 Atom ID

存储结构：
- archive/daily/YYYY-MM-DD/x.jsonl        ← X/Twitter 渠道
- archive/daily/YYYY-MM-DD/weibo.jsonl    ← 微博渠道
- archive/daily/YYYY-MM-DD/rss.jsonl      ← RSS渠道

使用方式：
    from atom_store import AtomStore
    store = AtomStore()
    
    # 按渠道存储
    store.save_atoms_batch(atoms, channel="x")
    
    # 查询单渠道
    atoms = store.query_by_date("2026-03-19", channel="x")
    
    # 查询全部
    atoms = store.query_by_date("2026-03-19")
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import Counter
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# ============ 配置 ============
BASE_DIR = Path(__file__).parent.parent / "archive"
DAILY_DIR = BASE_DIR / "daily"

# 合法的渠道名
CHANNELS = {"x", "weibo", "rss"}


class AtomStore:
    """Atom 存储引擎（简化版）"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else BASE_DIR
        self.daily_dir = self.base_dir / "daily"
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self._id_counters: Dict[str, int] = {}

    def _date_dir(self, date: str) -> Path:
        """返回日期文件夹路径"""
        return self.daily_dir / date

    def _jsonl_path(self, date: str, channel: str) -> Path:
        """返回 JSONL 文件路径"""
        return self._date_dir(date) / f"{channel}.jsonl"

    def _ensure_date_dir(self, date: str):
        """确保日期文件夹存在"""
        self._date_dir(date).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalize_url(url: str) -> str:
        """规范化 URL 用于去重"""
        if not url:
            return ""
        url = url.rstrip("/")
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            cleaned = {k: v for k, v in params.items() 
                       if not k.startswith("utm_") and k not in ("ref", "source", "from")}
            new_query = urlencode(cleaned, doseq=True)
            return urlunparse(parsed._replace(query=new_query))
        except Exception:
            return url

    def _load_existing_urls(self, date: str) -> Set[str]:
        """加载当日已有 URL（全局去重）"""
        urls = set()
        date_path = self._date_dir(date)
        if not date_path.exists():
            return urls
        
        for ch in CHANNELS:
            jsonl_path = date_path / f"{ch}.jsonl"
            if jsonl_path.exists():
                with open(jsonl_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            atom = json.loads(line)
                            source = atom.get("source", {})
                            url = source.get("url", "") if isinstance(source, dict) else str(source)
                            normalized = self._normalize_url(url)
                            if normalized:
                                urls.add(normalized)
                        except json.JSONDecodeError:
                            continue
        return urls

    def generate_id(self, date: str) -> str:
        """生成唯一 Atom ID: atom_YYYYMMDD_NNN"""
        date_compact = date.replace("-", "")
        if date not in self._id_counters:
            total = 0
            date_path = self._date_dir(date)
            if date_path.exists():
                for ch in CHANNELS:
                    jsonl_path = date_path / f"{ch}.jsonl"
                    if jsonl_path.exists():
                        with open(jsonl_path, "r", encoding="utf-8") as f:
                            total += sum(1 for line in f if line.strip())
            self._id_counters[date] = total + 1
        
        num = self._id_counters[date]
        self._id_counters[date] = num + 1
        return f"atom_{date_compact}_{num:03d}"

    def save_atoms_batch(self, atoms: List[Dict], channel: str) -> List[str]:
        """批量保存 Atoms"""
        if not atoms or channel not in CHANNELS:
            return []
        
        date = atoms[0].get("date", datetime.now().strftime("%Y-%m-%d"))
        self._ensure_date_dir(date)
        
        # 去重
        existing_urls = self._load_existing_urls(date)
        seen_urls: Set[str] = set()
        unique_atoms = []
        
        for atom in atoms:
            url = atom.get("source", {}).get("url", "")
            normalized = self._normalize_url(url)
            if normalized and (normalized in seen_urls or normalized in existing_urls):
                continue
            if normalized:
                seen_urls.add(normalized)
            unique_atoms.append(atom)
        
        ids = []
        jsonl_path = self._jsonl_path(date, channel)
        
        with open(jsonl_path, "a", encoding="utf-8") as f:
            for atom in unique_atoms:
                if "id" not in atom or not atom["id"]:
                    atom["id"] = self.generate_id(date)
                atom.setdefault("channel", channel)
                atom.setdefault("in_daily_brief", False)
                atom.setdefault("trust_final", None)
                atom.setdefault("trust_reason", None)
                f.write(json.dumps(atom, ensure_ascii=False) + "\n")
                ids.append(atom["id"])
        
        return ids

    def query_by_date(self, date: str, channel: Optional[str] = None) -> List[Dict]:
        """查询指定日期的 Atoms"""
        atoms = []
        date_path = self._date_dir(date)
        if not date_path.exists():
            return atoms
        
        channels_to_query = [channel] if channel and channel in CHANNELS else list(CHANNELS)
        seen_ids = set()
        
        for ch in channels_to_query:
            jsonl_path = date_path / f"{ch}.jsonl"
            if jsonl_path.exists():
                with open(jsonl_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                atom = json.loads(line)
                                atom_id = atom.get("id", "")
                                if atom_id not in seen_ids:
                                    seen_ids.add(atom_id)
                                    atoms.append(atom)
                            except json.JSONDecodeError:
                                continue
        return atoms

    def query_by_date_channel(self, date: str, channel: str) -> List[Dict]:
        """查询指定日期和渠道的 Atoms"""
        atoms = []
        jsonl_path = self._jsonl_path(date, channel)
        if not jsonl_path.exists():
            return atoms
        
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        atoms.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return atoms

    def get_daily_stats(self, date: str) -> Dict:
        """获取某天统计"""
        result = {"date": date, "channels": {}, "total": 0}
        date_path = self._date_dir(date)
        
        for ch in sorted(CHANNELS):
            jsonl_path = date_path / f"{ch}.jsonl"
            exists = jsonl_path.exists()
            count = 0
            categories = Counter()
            
            if exists:
                atoms = self.query_by_date_channel(date, ch)
                count = len(atoms)
                categories = Counter(a.get("category", "other") for a in atoms)
            
            result["channels"][ch] = {
                "file": f"{ch}.jsonl",
                "exists": exists,
                "count": count,
                "categories": dict(categories),
            }
            result["total"] += count
        
        return result

    def get_channel_status(self, date: str) -> Dict:
        """获取渠道状态（供 collector_cron.py 使用）"""
        return self.get_daily_stats(date)


def create_atom(
    title: str,
    summary_zh: str,
    platform: str,
    author: str,
    author_type: str,
    url: str,
    content_type: str,
    category: str,
    tags: List[str],
    entities: List[str],
    date: Optional[str] = None,
    title_zh: Optional[str] = None,
    **kwargs
) -> Dict:
    """便捷函数：创建一个 Atom 字典"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    L1_TYPES = {"official", "ceo_cto", "researcher", "expert_kol"}
    L2_TYPES = {"media", "kol", "analyst", "insider"}
    
    if author_type in L1_TYPES:
        trust_default = "L1"
    elif author_type in L2_TYPES:
        trust_default = "L2"
    else:
        trust_default = "L3"
    
    atom = {
        "id": None,
        "date": date,
        "title": title,
        "title_zh": title_zh or title,
        "summary_zh": summary_zh,
        "source": {
            "platform": platform,
            "author": author,
            "author_type": author_type,
            "url": url,
        },
        "content_type": content_type,
        "trust_default": trust_default,
        "category": category,
        "tags": [t.lower() for t in tags],
        "entities": entities,
        "in_daily_brief": False,
        "trust_final": None,
        "trust_reason": None,
    }
    
    if "upstream_url" in kwargs:
        atom["source"]["upstream_url"] = kwargs["upstream_url"]
    if "timestamp" in kwargs:
        atom["source"]["timestamp"] = kwargs["timestamp"]
    
    # 处理额外字段（embedded_urls, quotes_tweet, is_quoted_tweet, 等）
    extra_fields = [
        "embedded_urls", "quotes_tweet", "is_quoted_tweet", "quoted_by",
        "retweeted_by", "is_repost", "reposted_from", "metrics", "channel"
    ]
    for field in extra_fields:
        if field in kwargs:
            atom[field] = kwargs[field]
    
    return atom


# ============ CLI 入口 ============
if __name__ == "__main__":
    import sys
    
    store = AtomStore()
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python atom_store.py stats <date>              # 查看某天统计")
        print("  python atom_store.py query <date>              # 查看某天全部")
        print("  python atom_store.py query <date> <channel>    # 查看某天某渠道")
        print(f"\n可用渠道: {', '.join(sorted(CHANNELS))}")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "stats" and len(sys.argv) >= 3:
        stats = store.get_daily_stats(sys.argv[2])
        print(f"\n📊 {stats['date']} 采集状态:")
        print(f"{'─'*60}")
        for ch, info in stats["channels"].items():
            icon = "✅" if info["exists"] and info["count"] > 0 else "❌"
            cats = ", ".join(f"{k}:{v}" for k, v in sorted(info["categories"].items(), key=lambda x: -x[1])[:3])
            print(f"  {icon} {ch:8s} │ {info['count']:4d} 条 │ {cats}")
        print(f"{'─'*60}")
        print(f"  合计: {stats['total']} 条\n")
    
    elif cmd == "query" and len(sys.argv) >= 3:
        channel = sys.argv[3] if len(sys.argv) >= 4 else None
        atoms = store.query_by_date(sys.argv[2], channel=channel)
        label = f" [{channel}]" if channel else ""
        print(f"\n{sys.argv[2]}{label}: {len(atoms)} 条\n")
        for a in atoms[:20]:  # 最多显示20条
            print(f"[{a['id']}] [{a.get('trust_default', '?')}] {a.get('title_zh', a['title'])[:60]}")
            print(f"  信源: {a['source']['author']} ({a['source']['platform']})")
            print()
    
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)
