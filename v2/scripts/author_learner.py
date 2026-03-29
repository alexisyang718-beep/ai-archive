#!/usr/bin/env python3
"""
作者分类自动学习模块

功能：
1. 自动为新账号推断分类（基于其内容关键词）
2. 学习结果持久化到 learned_authors.json
3. 支持人工审核和修正
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple


class AuthorCategoryLearner:
    """
    作者分类自动学习器
    
    原理：基于作者历史内容的关键词分布，自动推断其所属分类
    """
    
    # 分类关键词（从 collector.py 同步）
    CATEGORY_KEYWORDS = {
        "ai_models": [
            "openai", "chatgpt", "anthropic", "deepmind", "google ai", "meta ai",
            "mistral", "deepseek", "perplexity", "huggingface", "hugging face",
            "gpt-4", "gpt-4o", "gpt-5", "claude", "gemini", "llama", "grok",
            "midjourney", "copilot", "sora", "dall-e", "dall·e", "stable diffusion",
            "runway", "flux", "whisper", "llm", "大模型", "大语言模型",
            "transformer", "diffusion model", "neural network", "deep learning",
            "machine learning", "reinforcement learning", "rlhf", "rag",
            "fine-tune", "finetune", "微调", "embedding", "prompt engineering",
            "ai agent", "ai coding", "agentic", "mcp protocol", "aigc", "generative ai",
            "reasoning model", "chain of thought", "multimodal", "多模态",
        ],
        "chips": [
            "nvidia", "amd", "intel", "tsmc", "samsung", "qualcomm", "broadcom",
            "gpu", "cpu", "tpu", "npu", "asic", "fpga", "chip", "芯片",
            "semiconductor", "晶圆", "光刻", "euv", "3nm", "5nm", "7nm",
            "h100", "h200", "b200", "gb200", "a100", "rtx", "cuda",
            "摩尔线程", "华为昇腾", "寒武纪", "海光", "景嘉微",
        ],
        "mobile": [
            "iphone", "ipad", "ios", "android", "pixel", "galaxy", "samsung",
            "xiaomi", "oppo", "vivo", "huawei", "荣耀", "一加", "oneplus",
            "smartphone", "tablet", "折叠屏", "fold", "app store", "play store",
            "手机", "平板", "移动", "5g", "6g", "基带", "屏幕", "摄像头",
        ],
        "gaming": [
            "playstation", "xbox", "nintendo", "switch", "steam", "epic",
            "game", "gaming", "gamer", "rpg", "fps", "moba", "手游",
            "原神", "王者荣耀", "黑神话", "gta", "使命召唤", "塞尔达",
            "虚幻引擎", "unity", "游戏", "主机", "手柄",
        ],
        "software_dev": [
            "github", "gitlab", "vscode", "cursor", "windsurf", "copilot",
            "javascript", "typescript", "python", "rust", "go", "java",
            "react", "vue", "nextjs", "node.js", "docker", "kubernetes",
            "aws", "azure", "gcp", "cloudflare", "vercel", "supabase",
            "api", "sdk", "framework", "library", "开源", "open source",
            "frontend", "backend", "fullstack", "devops", "database",
        ],
        "tech_industry": [
            "startup", "vc", "investment", "funding", "ipo", "acquisition",
            "apple", "microsoft", "google", "amazon", "meta", "tesla",
            "spacex", "starlink", "neuralink", "boring company",
            "ceo", "founder", "entrepreneur", "独角兽", "估值", "融资",
            "财报", "earnings", "revenue", "market cap", "股价",
            "ycombinator", "yc", "sequoia", "a16z", "老虎基金",
        ],
        "policy": [
            "regulation", "regulatory", "law", "bill", "policy", "政府",
            "制裁", "sanction", "tariff", "关税", "贸易", "trade",
            "sec", "ftc", "doj", "欧盟", "gdpr", "antitrust", "反垄断",
            "中美关系", "china", "biden", "trump", "congress", "senate",
            "election", "投票", "选举", "地缘政治", "geopolitics",
        ],
        "crypto_web3": [
            "bitcoin", "ethereum", "crypto", "cryptocurrency", "blockchain",
            "nft", "defi", "web3", "token", "btc", "eth", "solana",
            "交易所", "binance", "coinbase", "钱包", "智能合约",
        ],
        "ev_auto": [
            "tesla", "byd", "nio", "xpev", "li auto", "rivian", "lucid",
            "ev", "electric vehicle", "电动车", "新能源汽车", "自动驾驶",
            "fsd", "autopilot", "battery", "充电桩", "续航",
        ],
        "internet_tech": [
            "google", "search", "youtube", "tiktok", "twitter", "x.com",
            "meta", "facebook", "instagram", "whatsapp", "snapchat",
            "social media", "社交平台", "算法", "推荐", "信息流",
            "电商", "e-commerce", "amazon", "alibaba", "jd", "pdd",
        ],
    }
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        初始化学习器
        
        Args:
            data_dir: 数据目录，默认使用 v2/data
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 学习结果存储文件
        self.learned_file = self.data_dir / "learned_authors.json"
        self.confidence_file = self.data_dir / "author_confidence.json"
        
        # 加载已学习的映射
        self.learned_authors: Dict[str, str] = self._load_json(self.learned_file)
        self.author_confidence: Dict[str, Dict] = self._load_json(self.confidence_file)
        
        # 编译关键词正则
        self._regex_cache = {}
    
    def _load_json(self, path: Path) -> dict:
        """加载JSON文件"""
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_json(self, path: Path, data: dict):
        """保存JSON文件"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _build_regex(self, keyword: str):
        """为关键词构建匹配正则（带缓存）"""
        if keyword not in self._regex_cache:
            if keyword.isascii() and len(keyword) <= 4 and keyword.isalpha():
                self._regex_cache[keyword] = re.compile(
                    r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE
                )
            else:
                self._regex_cache[keyword] = None
        return self._regex_cache[keyword]
    
    def _kw_in_text(self, kw: str, text_lower: str) -> bool:
        """检查关键词是否在文本中"""
        regex = self._build_regex(kw)
        if regex is not None:
            return bool(regex.search(text_lower))
        return kw in text_lower
    
    def analyze_content(self, texts: List[str]) -> Tuple[Optional[str], Dict, float]:
        """
        分析内容，推断分类
        
        Args:
            texts: 文本列表（作者的多条推文）
            
        Returns:
            (分类, 详细得分, 置信度)
        """
        if not texts:
            return None, {}, 0.0
        
        # 合并所有文本
        combined_text = "\n".join(texts)
        text_lower = combined_text.lower()
        
        # 计算各分类得分
        cat_scores = {}
        cat_matches = defaultdict(list)  # 记录匹配到的关键词
        
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            score = 0
            matched_kws = []
            for kw in keywords:
                if self._kw_in_text(kw, text_lower):
                    score += 1
                    matched_kws.append(kw)
            
            if score > 0:
                cat_scores[cat] = score
                cat_matches[cat] = matched_kws
        
        if not cat_scores:
            return None, dict(cat_matches), 0.0
        
        # 找出最高分和次高分
        sorted_scores = sorted(cat_scores.items(), key=lambda x: x[1], reverse=True)
        top_cat, top_score = sorted_scores[0]
        
        # 计算置信度
        confidence = 0.0
        if len(sorted_scores) == 1:
            # 只有一个分类有匹配，置信度中等
            confidence = min(0.6, top_score / 10)
        else:
            # 有多个分类匹配，看分差
            second_score = sorted_scores[1][1]
            gap = top_score - second_score
            
            if gap >= 5:
                # 分差大，置信度高
                confidence = min(0.9, 0.5 + gap / 10)
            elif gap >= 2:
                # 分差中等，置信度中等
                confidence = min(0.7, 0.4 + gap / 10)
            else:
                # 分差小，置信度低
                confidence = min(0.5, 0.3 + gap / 10)
        
        # 如果匹配的关键词太少，降低置信度
        if top_score < 2:
            confidence *= 0.5
        
        return top_cat, dict(cat_matches), round(confidence, 2)
    
    def learn_author(self, author: str, texts: List[str], 
                     min_confidence: float = 0.5,
                     min_samples: int = 3) -> Optional[str]:
        """
        学习作者分类
        
        Args:
            author: 作者名（如 @username 或 username）
            texts: 作者的文本内容列表
            min_confidence: 最小置信度阈值
            min_samples: 最小样本数
            
        Returns:
            推断的分类，如果置信度不足返回 None
        """
        # 标准化作者名
        author_key = author.lower().strip().lstrip('@')
        
        # 检查是否已学习过
        if author_key in self.learned_authors:
            return self.learned_authors[author_key]
        
        # 样本不足
        if len(texts) < min_samples:
            return None
        
        # 分析内容
        category, matches, confidence = self.analyze_content(texts)
        
        if category and confidence >= min_confidence:
            # 保存学习结果
            self.learned_authors[author_key] = category
            self.author_confidence[author_key] = {
                "category": category,
                "confidence": confidence,
                "samples": len(texts),
                "matches": {k: len(v) for k, v in matches.items() if k == category}
            }
            
            # 持久化
            self._save_json(self.learned_file, self.learned_authors)
            self._save_json(self.confidence_file, self.author_confidence)
            
            return category
        
        return None
    
    def batch_learn_from_jsonl(self, jsonl_path: Path, 
                                min_confidence: float = 0.5,
                                min_samples: int = 3) -> Dict[str, str]:
        """
        从 JSONL 文件批量学习作者分类
        
        Args:
            jsonl_path: JSONL 文件路径
            min_confidence: 最小置信度
            min_samples: 最小样本数
            
        Returns:
            新学习的作者映射 {author: category}
        """
        # 按作者聚合内容
        author_texts = defaultdict(list)
        
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    atom = json.loads(line)
                    author = atom.get('source', {}).get('author', '')
                    if not author:
                        continue
                    
                    # 标准化作者名
                    author_key = author.lower().strip().lstrip('@')
                    
                    # 收集文本
                    text = atom.get('title', '') + ' ' + atom.get('summary_zh', '')
                    if text.strip():
                        author_texts[author_key].append(text)
                except json.JSONDecodeError:
                    continue
        
        # 学习新作者
        new_learned = {}
        for author, texts in author_texts.items():
            category = self.learn_author(author, texts, min_confidence, min_samples)
            if category:
                new_learned[author] = category
        
        return new_learned
    
    def get_author_category(self, author: str, 
                           fallback_to_learn: bool = True) -> Optional[str]:
        """
        获取作者分类
        
        Args:
            author: 作者名
            fallback_to_learn: 是否允许自动学习
            
        Returns:
            分类，未知返回 None
        """
        author_key = author.lower().strip().lstrip('@')
        
        # 1. 检查已学习的映射
        if author_key in self.learned_authors:
            return self.learned_authors[author_key]
        
        return None
    
    def generate_report(self) -> str:
        """生成学习报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("作者分类自动学习报告")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"已学习作者总数: {len(self.learned_authors)}")
        lines.append("")
        
        # 按分类统计
        cat_counts = Counter(self.learned_authors.values())
        lines.append("分类分布:")
        for cat, count in cat_counts.most_common():
            lines.append(f"  {cat}: {count}")
        lines.append("")
        
        # 高置信度作者
        high_conf = [(a, d) for a, d in self.author_confidence.items() 
                     if d.get('confidence', 0) >= 0.7]
        lines.append(f"高置信度作者 (>=0.7): {len(high_conf)}")
        for author, data in sorted(high_conf, key=lambda x: x[1]['confidence'], reverse=True)[:10]:
            lines.append(f"  @{author}: {data['category']} (置信度 {data['confidence']})")
        lines.append("")
        
        # 低置信度作者
        low_conf = [(a, d) for a, d in self.author_confidence.items() 
                    if d.get('confidence', 0) < 0.5]
        lines.append(f"低置信度作者 (<0.5): {len(low_conf)}")
        for author, data in sorted(low_conf, key=lambda x: x[1]['confidence'])[:5]:
            lines.append(f"  @{author}: {data['category']} (置信度 {data['confidence']})")
        
        return "\n".join(lines)


# 便捷函数
def get_learner() -> AuthorCategoryLearner:
    """获取学习器实例（单例模式）"""
    if not hasattr(get_learner, '_instance'):
        get_learner._instance = AuthorCategoryLearner()
    return get_learner._instance


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="作者分类自动学习")
    parser.add_argument("--date", default="2026-03-23", help="日期")
    parser.add_argument("--channel", default="x", help="渠道")
    parser.add_argument("--report", action="store_true", help="生成报告")
    
    args = parser.parse_args()
    
    learner = AuthorCategoryLearner()
    
    if args.report:
        print(learner.generate_report())
    else:
        # 批量学习
        jsonl_path = Path(__file__).parent.parent / "archive" / "daily" / args.date / f"{args.channel}.jsonl"
        
        if not jsonl_path.exists():
            print(f"❌ 文件不存在: {jsonl_path}")
            sys.exit(1)
        
        print(f"📚 从 {jsonl_path} 批量学习...")
        new_learned = learner.batch_learn_from_jsonl(jsonl_path)
        
        print(f"\n✅ 新学习 {len(new_learned)} 个作者:")
        for author, cat in sorted(new_learned.items()):
            conf = learner.author_confidence.get(author, {}).get('confidence', 'N/A')
            print(f"  @{author}: {cat} (置信度: {conf})")
        
        print(f"\n📊 总计已学习: {len(learner.learned_authors)} 个作者")
