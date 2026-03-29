#!/usr/bin/env python3
"""
话题聚类与热度排序模块

功能：
1. 将多条内容聚合成话题（如"Qwen3.5发布"）
2. 计算话题热度
3. 按热度排序输出
"""

import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime
import math


@dataclass
class Atom:
    """内容原子"""
    id: str
    title: str
    summary: str
    author: str
    platform: str
    url: str
    category: str
    entities: List[str]
    tags: List[str]
    timestamp: str
    metrics: Dict = field(default_factory=dict)
    trust: str = "L3"


@dataclass
class Topic:
    """话题"""
    id: str
    name: str  # 话题名称（如"Qwen3.5发布"）
    category: str
    keywords: Set[str]  # 核心关键词
    atoms: List[Atom] = field(default_factory=list)
    
    # 热度计算
    heat_score: float = 0.0
    
    def add_atom(self, atom: Atom):
        """添加内容到话题"""
        self.atoms.append(atom)
        self._update_heat()
    
    def _update_heat(self):
        """更新热度分数"""
        if not self.atoms:
            self.heat_score = 0
            return
        
        # 热度计算公式
        heat = 0
        
        for atom in self.atoms:
            # 1. 基础分（可信度）
            trust_score = {"L1": 3, "L2": 2, "L3": 1}.get(atom.trust, 1)
            
            # 2. 互动数据（仅X/微博有）
            engagement = 0
            if atom.platform == "x":
                likes = atom.metrics.get("likes", 0)
                retweets = atom.metrics.get("retweets", 0)
                replies = atom.metrics.get("replies", 0)
                views = atom.metrics.get("views", 0)
                # 互动加权
                engagement = likes + retweets * 2 + replies * 3
                # 浏览量作为辅助（防止刷量）
                if views > 0:
                    engagement = max(engagement, views * 0.001)
            elif atom.platform == "weibo":
                likes = atom.metrics.get("likes", 0)
                retweets = atom.metrics.get("retweets", 0)
                comments = atom.metrics.get("comments", 0)
                engagement = likes + retweets * 2 + comments * 3
            
            # 3. 时效性（越新越好）
            time_score = 1.0  # 默认
            if atom.timestamp:
                try:
                    # 简化处理，实际应该解析时间
                    time_score = 1.0
                except:
                    pass
            
            # 4. 平台权重
            platform_weight = {"x": 1.2, "weibo": 1.0, "rss": 0.8}.get(atom.platform, 0.8)
            
            # 综合计算
            atom_score = (trust_score * 10 + math.log1p(engagement)) * platform_weight * time_score
            heat += atom_score
        
        # 信源多样性加成（同一话题多个信源更有价值）
        unique_authors = len(set(a.author for a in self.atoms))
        diversity_bonus = math.log1p(unique_authors) * 5
        
        self.heat_score = round(heat + diversity_bonus, 2)
    
    def get_summary(self) -> str:
        """获取话题摘要"""
        if not self.atoms:
            return ""
        # 按可信度排序，取最高可信度的摘要
        sorted_atoms = sorted(self.atoms, 
                             key=lambda a: {"L1": 3, "L2": 2, "L3": 1}.get(a.trust, 1),
                             reverse=True)
        return sorted_atoms[0].summary[:200]
    
    def get_top_sources(self, n: int = 3) -> List[str]:
        """获取主要信源"""
        author_counts = Counter(a.author for a in self.atoms)
        return [author for author, _ in author_counts.most_common(n)]


class TopicCluster:
    """话题聚类器"""
    
    # 实体关键词（用于匹配）
    # 格式: (关键词, 优先级, 类别) 优先级数字越小越优先
    ENTITY_KEYWORDS = {
        # 手机产品 (高优先级)
        ("galaxy s26", 1, "device"), ("s26", 2, "device"),
        ("galaxy s25", 1, "device"), ("s25", 2, "device"),
        ("iphone 16", 1, "device"), ("iphone 17", 1, "device"),
        ("iphone", 3, "device"), ("pixel", 3, "device"),
        ("xiaomi", 3, "device"), ("oppo", 3, "device"), ("vivo", 3, "device"),
        ("vision pro", 2, "device"),
        # 功能/特性
        ("airdrop", 4, "feature"), ("ios", 4, "software"), ("android", 4, "software"),
        ("harmonyos", 4, "software"),
        # AI模型
        ("qwen3.5", 1, "ai"), ("qwen", 2, "ai"),
        ("kimi", 2, "ai"), ("glm-5", 1, "ai"), ("glm", 2, "ai"),
        ("gpt-5", 1, "ai"), ("gpt-4o", 1, "ai"), ("gpt-4", 2, "ai"),
        ("claude", 2, "ai"), ("gemini", 2, "ai"), ("deepseek", 2, "ai"),
        ("llama", 2, "ai"), ("grok", 2, "ai"), ("mistral", 2, "ai"),
        ("minimax", 2, "ai"), ("abab", 3, "ai"),
        # AI产品
        ("sora", 2, "ai_product"), ("dall-e", 2, "ai_product"), ("midjourney", 2, "ai_product"),
        ("runway", 2, "ai_product"), ("stable diffusion", 2, "ai_product"), ("flux", 2, "ai_product"),
        ("copilot", 2, "ai_product"), ("cursor", 2, "ai_product"), ("windsurf", 2, "ai_product"),
        ("devin", 2, "ai_product"), ("codex", 2, "ai_product"), ("gstack", 2, "ai_product"),
        # 公司
        ("openai", 3, "company"), ("anthropic", 3, "company"), ("google", 3, "company"),
        ("deepmind", 3, "company"), ("meta", 3, "company"), ("nvidia", 3, "company"),
        ("alibaba", 3, "company"), ("baidu", 3, "company"), ("tencent", 3, "company"),
        ("bytedance", 3, "company"), ("moonshot", 3, "company"), ("zhipu", 3, "company"),
        ("rakuten", 3, "company"), ("乐天", 3, "company"), ("stepfun", 3, "company"), ("阶跃星辰", 3, "company"),
        # 芯片
        ("h100", 2, "chip"), ("h200", 2, "chip"), ("b200", 2, "chip"), ("gb200", 1, "chip"),
        ("blackwell", 2, "chip"), ("a100", 2, "chip"), ("mi300", 2, "chip"),
        ("tsmc", 3, "company"), ("intel", 3, "company"), ("amd", 3, "company"),
        ("m4", 3, "chip"), ("m5", 3, "chip"),
        # 游戏
        ("黑神话", 2, "game"), ("原神", 2, "game"), ("genshin", 2, "game"),
        ("王者荣耀", 2, "game"), ("steam", 3, "platform"), ("switch", 3, "device"),
        ("ps5", 3, "device"), ("xbox", 3, "device"),
        ("gta6", 1, "game"), ("gta vi", 1, "game"), ("gta 6", 1, "game"),
        # 其他科技
        ("spacex", 3, "company"), ("starlink", 2, "product"), ("tesla", 3, "company"),
        ("cybertruck", 2, "product"), ("fsd", 2, "feature"), ("robotaxi", 2, "product"),
    }
    
    # 人物实体（重要人物，可作为独立实体识别）
    PERSON_KEYWORDS = {
        # AI领域
        "sam altman": "Sam Altman", "sama": "Sam Altman",
        "mark zuckerberg": "Zuckerberg", "zuckerberg": "Zuckerberg", "扎克伯格": "Zuckerberg",
        "sundar pichai": "Sundar Pichai", "pichai": "Sundar Pichai",
        "satya nadella": "Satya Nadella", "nadella": "Satya Nadella",
        "tim cook": "Tim Cook", "cook": "Tim Cook",
        "elon musk": "Elon Musk", "musk": "Elon Musk", "马斯克": "Elon Musk",
        "jensen huang": "Jensen Huang", "黄仁勋": "Jensen Huang",
        "demis hassabis": "Demis Hassabis", "hassabis": "Demis Hassabis",
        "fei-fei li": "Fei-Fei Li", "李飞飞": "Fei-Fei Li",
        "andrew ng": "Andrew Ng", "吴恩达": "Andrew Ng",
        "yann lecun": "Yann LeCun", "lecun": "Yann LeCun",
        "andre karpathy": "Andrej Karpathy", "karpathy": "Andrej Karpathy",
        "jim fan": "Jim Fan",
        "李想": "李想", "雷军": "雷军", "任正非": "任正非",
        # 中国AI
        "杨植麟": "杨植麟", "张鹏": "张鹏", "王小川": "王小川",
        "李开复": "李开复", "李彦宏": "李彦宏", "马云": "马云",
    }
    
    # 动作/事件关键词
    ACTION_KEYWORDS = {
        "发布": ["发布", "推出", "上线", "问世", "亮相", "登场", "launch", "release", "announce", "introduce"],
        "更新": ["更新", "升级", "改版", "迭代", "新版", "v2", "v3", "v4", "update", "upgrade"],
        "兼容": ["兼容", "支持", "适配", "接入", "整合", "集成", "support", "compatible", "integration", "works with"],
        "合作": ["合作", "联手", "结盟", "战略合作", "伙伴关系", "partnership", "collaboration", "team up"],
        "收购": ["收购", "并购", "买下", "控股", "入股", "acquisition", "acquire", "buyout"],
        "裁员": ["裁员", "layoff", "layoffs", "解雇", "离职", "fire", "cut jobs"],
        "财报": ["财报", "营收", "利润", "earnings", "revenue", "financial report", "quarterly"],
        "故障": ["故障", "宕机", "崩溃", "outage", "down", "crash", "failure"],
        "漏洞": ["漏洞", "bug", "安全问题", "security flaw", "vulnerability", "exploit"],
        "降价": ["降价", "打折", "促销", "sale", "price cut", "discount"],
        "涨价": ["涨价", "提价", "price hike", "price increase"],
        "禁售": ["禁售", "禁令", "ban", "prohibition", "blocked", "sanction"],
        "开源": ["开源", "open source", "开源发布", "open-source", "github release"],
        "突破": ["突破", "里程碑", "新纪录", "record", "breakthrough", "milestone"],
        "争议": ["争议", "丑闻", "scandal", "controversy", "backlash", "criticism"],
    }
    
    # 具体事件模式（用于生成事件签名）
    EVENT_PATTERNS = {
        # Meta相关事件
        "meta_ceo_agent": [r'(?:meta\s*)?(?:ceo\s*)?(?:zuckerberg|扎克伯格).*?(?:ceo\s*)?(?:级|level)?\s*(?:ai\s*)?(?:代理|agent)', r'(?:ai\s*)?(?:代理|agent).*?(?:assist|协助).*?(?:zuckerberg|扎克伯格)'],
        "meta_layoff": [r'(?:meta|facebook).*?(?:裁员|layoff|fire|cut\s*jobs)', r'(?:裁员|layoff).*?(?:meta|facebook)'],
        "meta_lobster": [r'(?:meta|facebook).*?(?:龙虾|lobster|自研芯片|ai\s*chip)', r'(?:龙虾|lobster).*?(?:meta|facebook)'],
        "meta_fake_account": [r'(?:meta|facebook).*?(?:封号|ban|fake|虚假|ai\s*生成)', r'(?:fake|虚假).*?(?:meta|facebook)'],
        # Cursor相关事件
        "cursor_kimi": [r'cursor.*?(?:套壳|基于|built\s*on|based\s*on).*?kimi', r'kimi.*?(?:套壳|基于).*?cursor'],
        # OpenAI/GPT相关事件 - 细分到具体版本
        "gpt54_mini_nano": [r'gpt[\s\-]*5\.4[\s\-]*(?:mini|nano)', r'(?:mini|nano).*?gpt[\s\-]*5\.4'],
        "gpt52_wargame": [r'gpt[\s\-]*5\.2.*?(?:兵棋|推演|wargame|模拟|核危机)', r'(?:兵棋|推演|wargame).*?gpt[\s\-]*5\.2'],
        "openai_hiring": [r'(?:openai|奥特曼).*?(?:招聘|扩招|员工|hire|hiring|扩招)', r'(?:招聘|扩招).*?(?:openai|奥特曼)'],
        # MiniMax事件
        "minimax_m27": [r'minimax[\s\-]*m?2\.7', r'm2\.7.*?(?:minimax|发布)'],
        # DeepSeek相关事件 - 细分
        "deepseek_talent_guodaya": [r'(?:deepseek|郭达雅|罗福莉).*?(?:抢|挖|人才|加盟|加入)', r'(?:郭达雅|罗福莉)'],
        "deepseek_rakuten_copy": [r'(?:乐天|rakuten).*?(?:deepseek|套壳|抄袭)', r'(?:套壳|抄袭).*?(?:deepseek|乐天)'],
        "deepseek_xiaomi_hunter": [r'(?:小米|xiaomi).*?(?:hunter|alpha|mimo)', r'(?:hunter|alpha).*?(?:小米|xiaomi)'],
        # Qwen相关事件
        "qwen_release": [r'qwen[\s\-]*\d+\.?\d*.*?(?:发布|release|launch)', r'(?:发布|release).*?qwen[\s\-]*\d+\.?\d*'],
        # DLSS相关事件
        "nvidia_dlss": [r'(?:nvidia|英伟达).*?dlss[\s\-]*\d+', r'dlss[\s\-]*\d+.*?(?:nvidia|英伟达)'],
        # 人才争夺事件
        "ai_talent_war": [r'(?:抢|挖|争夺|hire|poach).*?(?:人才|talent|研究员|researcher)', r'(?:人才|talent).*?(?:争夺|war|抢)'],
        # 马斯克芯片工厂事件
        "musk_terafab": [r'(?:musk|马斯克).*?(?:terafab|芯片工厂|chip\s*plant)', r'(?:terafab|芯片工厂).*?(?:musk|马斯克|tesla|spacex)'],
        # AI交易/实盘实验事件
        "ai_trading_competition": [r'(?:大模型|ai|llm).*?(?:\$10000|10000刀|实盘|交易|trading)', r'(?:实盘|交易|trading).*?(?:大模型|ai|llm|\$10000)'],
        # Gemini具体版本事件
        "gemini_31_flash_lite": [r'gemini[\s\-]*3\.1[\s\-]*flash[\s\-]*lite', r'flash[\s\-]*lite.*?(?:gemini|3\.1)'],
        "gemini_groundsource": [r'(?:groundsource|ground source)', r'gemini.*?(?:groundsource|新闻|数据)'],
    }
    
    def __init__(self):
        self.topics: Dict[str, Topic] = {}
        self.atom_to_topic: Dict[str, str] = {}  # atom_id -> topic_id
    
    def extract_topic_signature(self, text: str) -> Tuple[Set[str], Optional[str], Optional[str], Optional[str]]:
        """
        提取话题签名
        
        Returns:
            (entities, entity_name, action, event_signature) - 实体集合、主实体、动作、事件签名
        """
        text_lower = text.lower()
        entities = set()
        entity_info = []  # [(keyword, priority, category), ...]
        
        # 1. 提取实体（带优先级）
        for keyword, priority, category in self.ENTITY_KEYWORDS:
            if keyword in text_lower:
                entities.add(keyword)
                entity_info.append((keyword, priority, category))
        
        # 2. 提取人物实体（也加入entities集合）
        detected_person = None
        for keyword, person_name in self.PERSON_KEYWORDS.items():
            if keyword in text_lower:
                entities.add(person_name.lower())
                detected_person = person_name
        
        if not entities:
            return set(), None, None, None
        
        # 3. 确定主实体（智能选择真正的主题实体）
        entity_name = self._select_main_entity(text_lower, entities, entity_info, detected_person)
        
        # 4. 提取动作
        action = None
        for action_type, keywords in self.ACTION_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    action = action_type
                    break
            if action:
                break
        
        # 5. 提取事件签名（用于更精确的聚类）
        event_signature = self._extract_event_signature(text_lower)
        
        return entities, entity_name, action, event_signature
    
    def _select_main_entity(self, text: str, entities: Set[str], entity_info: List, detected_person: Optional[str]) -> Optional[str]:
        """
        智能选择主实体 - 识别文本真正的核心主题
        
        策略：
        1. 检查是否有明确的事件签名，优先使用事件签名相关的实体
        2. 分析实体在文本中的位置和频率
        3. 避免将"提及"的实体误认为主实体（如对比时提到的其他模型）
        """
        if not entities:
            return detected_person.lower() if detected_person else None
        
        text_lower = text.lower()
        
        # ========== 特殊规则：根据文本内容模式识别真正的主实体 ==========
        
        # 规则1: 小米Hunter Alpha模型相关
        if any(kw in text_lower for kw in ["hunter alpha", "hunter-alpha", "mimo-v2", "mimo v2"]):
            if "xiaomi" in entities or "小米" in entities:
                return "xiaomi"
        
        # 规则2: Cursor套壳Kimi相关
        if "cursor" in text_lower and any(kw in text_lower for kw in ["kimi", "套壳", "based on", "built on"]):
            if "cursor" in entities:
                return "cursor"
        
        # 规则3: 乐天套壳DeepSeek相关
        if any(kw in text_lower for kw in ["乐天", "rakuten"]) and "deepseek" in text_lower:
            if "rakuten" in entities or "乐天" in entities:
                return "rakuten" if "rakuten" in entities else "乐天"
        
        # 规则4: GPT-5.4 mini/nano发布 - 必须是发布主体
        if any(kw in text_lower for kw in ["gpt-5.4 mini", "gpt-5.4 nano", "gpt 5.4 mini", "gpt 5.4 nano"]):
            if "gpt-5" in entities or "gpt" in entities:
                return "gpt-5"
        
        # 规则5: MiniMax M2.7发布 - 必须是发布主体（排除对比提及的情况）
        if "minimax" in text_lower and ("2.7" in text or "m2.7" in text_lower):
            # 检查是否是MiniMax自己的发布（而非对比提及）
            # 如果标题或开头明确提到MiniMax，则认为是主实体
            if "minimax" in entities:
                # 进一步检查：如果文本主要是关于MiniMax的，则返回minimax
                if any(kw in text_lower for kw in ["minimax.*发布", "minimax.*上线", "minimax.*炸场", "minimax.*重磅"]):
                    return "minimax"
                # 如果MiniMax在文本开头出现，也认为是主实体
                first_sentence = text_lower[:200]
                if "minimax" in first_sentence:
                    return "minimax"
        
        # 规则6: AI兵棋推演实验
        if any(kw in text_lower for kw in ["兵棋", "推演", "wargame", "核危机", "模拟.*gpt", "gpt.*模拟"]):
            # 这是一个多模型参与的事件，使用特殊标记
            return "ai_wargame_experiment"
        
        # 规则7: AI实盘交易实验
        if any(kw in text_lower for kw in ["实盘", "交易", "trading", "$10000", "10000刀", "predictionarena", "给每个大模型.*10000"]):
            return "ai_trading_experiment"
        
        # 规则8: DeepSeek人才争夺
        if "deepseek" in text_lower and any(kw in text_lower for kw in ["郭达雅", "罗福莉", "人才", "挖角", "抢", "加盟", "加入"]):
            if "deepseek" in entities:
                return "deepseek"
        
        # ========== 默认：智能选择主实体 ==========
        
        # 过滤掉可能是"对比提及"的实体（如GPT-5在MiniMax发布文中被提及作为对比）
        # 策略：如果文本明确以某个实体开头，优先选择该实体
        first_100_chars = text_lower[:100]
        
        for entity in entities:
            if entity in first_100_chars:
                # 检查这个实体是否是发布主体
                return entity
        
        # 按优先级和长度选择
        if entity_info:
            # 重新排序：优先选择作为"发布主体"的实体
            # 排除那些明显是对比提及的实体（如GPT在MiniMax文章中）
            filtered_info = []
            for info in entity_info:
                keyword, priority, category = info
                # 如果实体在文本开头出现，降低优先级数字（提高优先级）
                if keyword in first_100_chars:
                    filtered_info.append((keyword, priority - 5, category))  # 提高优先级
                else:
                    filtered_info.append(info)
            
            filtered_info.sort(key=lambda x: (x[1], -len(x[0])))
            return filtered_info[0][0]
        elif detected_person:
            return detected_person.lower()
        else:
            return list(entities)[0]
    
    def _extract_event_signature(self, text: str) -> Optional[str]:
        """提取具体事件签名，用于更精确的聚类"""
        for event_name, patterns in self.EVENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return event_name
        return None
    
    # 模型版本号匹配模式
    VERSION_PATTERN = re.compile(r'(\d+\.\d+[a-z]?\d*|\d+[a-z]?)', re.IGNORECASE)
    
    # 话题命名用的模式（用于生成具体话题名称）
    TOPIC_NAME_PATTERNS = {
        # 模型发布 - 提取版本号
        "model_release": [
            (r'qwen[\s\-]*(\d+\.?\d*[a-z]?\d*)[\s\-]*(\d+b)?', "Qwen {v1} {v2}"),
            (r'gpt[\s\-]*(\d+[o\.]?\d*)', "GPT {v1}"),
            (r'claude[\s\-]*(\d+\.?\d*)', "Claude {v1}"),
            (r'kimi[\s\-]*(k?\d+\.?\d*)', "Kimi {v1}"),
            (r'glm[\s\-]*(\d+\.?\d*)', "GLM {v1}"),
            (r'llama[\s\-]*(\d+\.?\d*)', "Llama {v1}"),
            (r'gemini[\s\-]*(\d+\.?\d*)', "Gemini {v1}"),
        ],
        # 收购事件 - 提取被收购方
        "acquisition": [
            (r'收购[\s\w]*?(\w+)[\s\w]*?(?:公司|团队|初创)', "收购{v1}"),
            (r'acquir(?:ing|e)[\s\w]*?(\w+)', "收购{v1}"),
            (r'(\w+)[\s\w]*?(?:加入|join)[\s\w]*?(?:团队|team)', "收购{v1}"),
        ],
        # 争议事件 - 提取争议核心
        "controversy": [
            (r'(?:套壳|抄袭|侵权|争议)[\s\w]*?(\w+)', "{v1}争议"),
            (r'(\w+)[\s\w]*?(?:套壳|抄袭|侵权)', "{v1}争议"),
            (r'承认[\s\w]*?(\w+)', "{v1}争议"),
            (r'道歉[\s\w]*?(\w+)', "{v1}道歉"),
        ],
        # 功能特性
        "feature": [
            (r'(\w+)[\s\w]*?(?:功能|feature)[\s\w]*?(?:上线|发布|推出)', "{v1}功能"),
            (r'(?:支持|兼容)[\s\w]*?(\w+)', "兼容{v1}"),
            (r'(\w+)[\s\w]*?(?:集成|接入)', "{v1}集成"),
        ],
        # 对比评测
        "comparison": [
            (r'(\w+)[\s\w]*?(?:vs|versus|对比|比较)[\s\w]*(\w+)', "{v1} vs {v2}"),
            (r'(?:对比|比较)[\s\w]*?(\w+)[\s\w]*?(?:和|与|vs)[\s\w]*(\w+)', "{v1} vs {v2}"),
        ],
    }
    
    def generate_topic_name(self, entity: str, action: Optional[str], atoms: List[Atom]) -> str:
        """
        生成具体的话题名称
        
        策略：
        1. 从所有内容文本中提取最具体的事件描述
        2. 根据实体类型和动作选择提取模式
        3. 组合成"实体+具体事件"格式
        """
        # 收集所有文本
        all_text = " ".join([a.title + " " + a.summary for a in atoms])
        all_text_lower = all_text.lower()
        
        # 实体名称映射（更友好的显示名）
        entity_display = self._get_entity_display_name(entity)
        entity_lower = entity.lower()
        
        # 1. 尝试提取模型版本号（最高优先级）
        version_info = self._extract_model_version(all_text_lower, entity)
        if version_info:
            if action:
                return f"{version_info}{self._get_action_display(action)}"
            return f"{version_info}发布"
        
        # 2. 针对特定实体的智能命名（最高优先级，因为有最具体的规则）
        smart_name = self._get_smart_entity_name(entity_lower, all_text_lower)
        if smart_name:
            return smart_name
        
        # 3. 尝试提取具体事件（通用模式匹配）
        event_info = self._extract_specific_event(all_text_lower, entity)
        if event_info:
            return event_info
        
        # 4. 如果有动作，使用实体+动作格式
        if action:
            action_display = self._get_action_display(action)
            # 尝试从内容提取动作对象
            target = self._extract_action_target(all_text_lower, action)
            if target:
                return f"{entity_display}{action_display}{target}"
            # 避免过于笼统的名称如"OpenAI发布"、"DeepSeek发布"
            if entity_lower in ["openai", "deepseek", "gemini", "anthropic", "nvidia"]:
                # 尝试从文本中提取更具体的信息
                specific = self._extract_any_specific_info(all_text_lower, entity_lower)
                if specific:
                    return specific
                return f"{entity_display}动态"  # 使用"动态"而非"发布"
            return f"{entity_display}{action_display}"
        
        # 5. 默认返回（避免使用"相关动态"）
        # 对于容易笼统的实体，尝试提取更具体的信息
        if entity_lower in ["openai", "deepseek", "gemini", "anthropic", "nvidia", "google", "meta"]:
            specific = self._extract_any_specific_info(all_text_lower, entity_lower)
            if specific:
                return specific
            return f"{entity_display}动态"
        return entity_display
    
    def _extract_any_specific_info(self, text: str, entity: str) -> Optional[str]:
        """尝试提取任何具体的信息来命名话题"""
        # 提取产品/模型名
        model_patterns = [
            r'(gpt[\s\-]*\d+[o\.]?\d*)',
            r'(claude[\s\-]*\d+\.?\d*)',
            r'(gemini[\s\-]*\d+\.?\d*)',
            r'(kimi[\s\-]*k?\d+\.?\d*)',
            r'(qwen[\s\-]*\d+\.?\d*)',
            r'(glm[\s\-]*\d+\.?\d*)',
            r'(deepseek[\s\-]*[v\-]?\d*)',
            r'(minimax[\s\-]*m?\d+\.?\d*)',
        ]
        for pattern in model_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                model = match.group(1)
                # 使用友好的显示名而不是直接upper
                model_display = self._get_entity_display_name(model.lower())
                return f"{model_display}相关"
        
        # 提取具体事件关键词
        event_keywords = [
            (r'(?:兵棋|推演|wargame|模拟|核危机)', "兵棋推演"),
            (r'(?:套壳|抄袭|侵权|争议)', "争议"),
            (r'(?:裁员|layoff|fire)', "裁员"),
            (r'(?:招聘|扩招|hire)', "招聘"),
            (r'(?:收购|并购|acquisition)', "收购"),
            (r'(?:财报|营收|revenue)', "财报"),
            (r'(?:开源|open source)', "开源"),
            (r'(?:兼容|支持|适配)', "兼容支持"),
            (r'(?:合作|联手|partnership)', "合作"),
            (r'(?:实盘|交易|trading|\$10000)', "实盘交易"),
            (r'(?:人才|挖角|抢人|talent)', "人才争夺"),
        ]
        for pattern, event_name in event_keywords:
            if re.search(pattern, text, re.IGNORECASE):
                return f"{self._get_entity_display_name(entity)}{event_name}"
        
        return None
    
    def _get_smart_entity_name(self, entity: str, text: str) -> Optional[str]:
        """针对特定实体的智能命名"""
        # Claude 相关（检查实体或文本）
        if "claude" in entity or "claude" in text.lower():
            if "claude code" in text.lower():
                if "codex" in text.lower():
                    return "Claude Code vs Codex对比"
                if "obsidian" in text.lower():
                    return "Claude Code+Obsidian集成"
                if "skill" in text.lower() or "技能" in text:
                    return "Claude Code技能系统"
                if "channel" in text.lower():
                    return "Claude Code Channels功能"
                return "Claude Code使用体验"
            if "codex" in text.lower():
                return "Claude vs Codex对比"
            if "用户" in text or "画像" in text or "profile" in text.lower():
                return "Claude用户画像分析"
        
        # OPPO 相关
        if "oppo" in entity:
            if "find" in text.lower():
                return "OPPO Find N6发布"
            return "OPPO新品"
        
        # Vivo 相关
        if "vivo" in entity:
            if "x" in text.lower() or "fold" in text.lower():
                return "vivo X Fold新品"
            return "vivo新品动态"
        
        # Google 相关
        if "google" in entity:
            # Project Genie
            if "genie" in text.lower():
                return "Google Project Genie"
            # Colab MCP
            if "colab" in text.lower() or "mcp" in text.lower():
                return "Google Colab MCP集成"
            # DeepMind印度合作
            if "india" in text.lower() or "印度" in text:
                return "Google DeepMind印度合作"
            # Gemini更新
            if "gemini" in text.lower():
                return "Google Gemini更新"
            # Android更新
            if "android" in text.lower():
                return "Google Android更新"
            # YouTube相关
            if "youtube" in text.lower() or "播客" in text or "podcast" in text.lower():
                return "YouTube产品动态"
            # 儿童保护/政策
            if "child" in text.lower() or "儿童" in text or "protection" in text.lower():
                return "Google政策动态"
            # 环境/气候研究
            if "contrail" in text.lower() or "尾迹" in text or "climate" in text.lower() or "flight" in text.lower():
                return "Google环境研究"
            # LiteRT/TFLite
            if "litert" in text.lower() or "tflite" in text.lower() or "tensorflow" in text.lower():
                return "Google LiteRT发布"
            return "Google动态"
        
        # 小米相关
        if "xiaomi" in entity or "小米" in entity:
            if "su7" in text.lower() or "汽车" in text:
                return "小米SU7汽车"
            if "15" in text or "16" in text:
                return "小米15/16系列"
            return "小米新品动态"
        
        # Galaxy S26 相关
        if "s26" in entity or "galaxy s26" in entity:
            if "airdrop" in text.lower():
                return "Galaxy S26兼容AirDrop"
            return "Galaxy S26新品"
        
        # Meta 相关 - 提取最核心事件
        if "meta" in entity or "zuckerberg" in entity:
            # 优先检查裁员（因为裁员是明确的事件）
            if "裁员" in text or "layoff" in text.lower() or "fired" in text.lower() or "fire" in text.lower():
                return "Meta大规模裁员"
            # 然后检查CEO代理
            if "ceo" in text.lower() and ("agent" in text.lower() or "代理" in text):
                return "扎克伯格打造CEO级AI代理"
            if "龙虾" in text or "lobster" in text.lower():
                return "Meta自研龙虾安全危机"
            if "封号" in text or "fake" in text.lower():
                return "Meta打击AI虚假账号"
            # 如果提到了Zuckerberg但没有具体事件
            if "zuckerberg" in entity or "扎克伯格" in text:
                return "Zuckerberg动态"
            return "Meta动态"
        
        # GStack 相关 - 提取具体动态
        if "gstack" in entity:
            if "korea" in text.lower() or "韩国" in text:
                return "GStack韩国爆火"
            if "office-hours" in text.lower() or "office hours" in text.lower():
                return "GStack Office Hours功能"
            if "domain" in text.lower() or "域名" in text:
                return "GStack域名相关"
            return "GStack AI编程工具"
        
        # Gemini 相关 - 提取具体应用
        if "gemini" in entity:
            if "3.1" in text or "3.1 pro" in text.lower():
                return "Gemini 3.1 Pro发布"
            if "music" in text.lower() or "音乐" in text or "lyria" in text.lower():
                return "Gemini音乐生成功能"
            if "groundsource" in text.lower():
                return "Gemini Groundsource工具"
            if "engineering" in text.lower() or "工程" in text:
                return "Gemini工程助手应用"
            return "Gemini模型更新"
        
        # SpaceX 相关
        if "spacex" in entity:
            return "SpaceX动态"
        
        # Anthropic 相关
        if "anthropic" in entity:
            # CEO发言/预测
            if "ceo" in text.lower() or "dario" in text.lower() or "amodei" in text.lower() or "律师" in text or "咨询" in text or "金融" in text or "淘汰" in text or "wipe out" in text.lower():
                return "Anthropic CEO预测AI影响"
            # 偏见/教育研究
            if "偏见" in text or "教育" in text or "学历" in text or "educated" in text.lower() or "voice" in text.lower() or "语音" in text:
                return "Anthropic AI偏见研究"
            # 就业/AI暴露度研究
            if "就业" in text or "工作" in text or "job" in text.lower() or "work" in text.lower() or "暴露度" in text or "exposure" in text.lower() or "职业" in text or "程序员" in text:
                return "Anthropic AI就业影响研究"
            # Claude更新
            if "claude 4" in text.lower() or "claude 3.7" in text.lower() or "claude 3.5" in text.lower() or "sonnet" in text.lower() or "opus" in text.lower():
                return "Claude模型更新"
            return "Anthropic动态"
        
        # Kimi 相关
        if "kimi" in entity:
            # 注意力残差论文
            if "attention residual" in text.lower() or "注意力残差" in text or "论文" in text:
                return "Kimi注意力残差论文"
            # 模型发布
            if "k2" in text.lower():
                return "Kimi K2发布"
            # 功能更新
            if "长文本" in text or "长上下文" in text or "探索版" in text:
                return "Kimi功能更新"
            return "Kimi动态"
        
        # Steam 相关
        if "steam" in entity:
            return "Steam平台动态"
        
        # iPhone 相关
        if "iphone" in entity:
            return "iPhone新品动态"
        
        # NVIDIA 相关
        if "nvidia" in entity:
            if "争议" in text or "scandal" in text.lower():
                return "NVIDIA争议"
            return "NVIDIA动态"
        
        return None
    
    def _get_entity_display_name(self, entity: str) -> str:
        """获取实体的友好显示名"""
        entity_map = {
            "qwen": "通义千问",
            "qwen3.5": "Qwen 3.5",
            "qwen3.8": "Qwen 3.8",
            "kimi": "Kimi",
            "glm": "智谱GLM",
            "glm-5": "GLM-5",
            "claude": "Claude",
            "gpt-4": "GPT-4",
            "gpt-4o": "GPT-4o",
            "gpt-5": "GPT-5",
            "gemini": "Gemini",
            "deepseek": "DeepSeek",
            "codex": "Codex",
            "cursor": "Cursor",
            "gstack": "GStack",
            "sora": "Sora",
            "s26": "Galaxy S26",
            "s25": "Galaxy S25",
            "vision pro": "Vision Pro",
            "airdrop": "AirDrop",
            "gta6": "GTA 6",
            "gta vi": "GTA 6",
            "黑神话": "黑神话：悟空",
            "openai": "OpenAI",
            "anthropic": "Anthropic",
            "nvidia": "NVIDIA",
            "h100": "H100",
            "h200": "H200",
            "b200": "B200",
            "gb200": "GB200",
            "tsmc": "台积电",
            "oppo": "OPPO",
            "xiaomi": "小米",
            "apple": "Apple",
            "samsung": "三星",
            "rakuten": "乐天",
            "乐天": "乐天",
            "ai_wargame_experiment": "AI兵棋推演",
            "ai_trading_experiment": "AI实盘交易",
        }
        return entity_map.get(entity.lower(), entity.title())
    
    def _get_action_display(self, action: str) -> str:
        """获取动作的显示名"""
        action_map = {
            "发布": "发布",
            "更新": "更新",
            "兼容": "兼容",
            "支持": "支持",
            "合作": "合作",
            "收购": "收购",
            "裁员": "裁员",
            "财报": "财报",
            "故障": "故障",
            "漏洞": "漏洞",
            "降价": "降价",
            "涨价": "涨价",
            "禁售": "禁售",
            "开源": "开源",
            "突破": "突破",
            "争议": "争议",
        }
        return action_map.get(action, action)
    
    def _extract_model_version(self, text: str, entity: str) -> Optional[str]:
        """提取模型版本号，返回完整名称如'Qwen 3.5 27b'"""
        entity_lower = entity.lower()
        
        # 根据实体类型选择匹配模式
        patterns = {
            "qwen": [
                (r'qwen[\s\-]*(\d+\.?\d*[a-z]?)\s*(\d+b)', "Qwen {v1} {v2}"),
                (r'qwen[\s\-]*(\d+\.?\d*[a-z]?)', "Qwen {v1}"),
            ],
            "kimi": [
                (r'kimi[\s\-]*(k?\d+\.?\d*)', "Kimi {v1}"),
            ],
            "claude": [
                (r'claude[\s\-]*(\d+\.?\d*)', "Claude {v1}"),
            ],
            "gpt": [
                (r'gpt[\s\-]*([45][o\.]?\d*)', "GPT {v1}"),
            ],
            "glm": [
                (r'glm[\s\-]*(\d+\.?\d*)', "GLM {v1}"),
            ],
        }
        
        for key, pattern_list in patterns.items():
            if key in entity_lower:
                for pattern, template in pattern_list:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        v1 = match.group(1).upper() if match.group(1) else ""
                        if len(match.groups()) > 1 and match.group(2):
                            v2 = match.group(2).lower()
                            return template.format(v1=v1, v2=v2)
                        return template.format(v1=v1)
        
        return None
    
    def _extract_specific_event(self, text: str, entity: str) -> Optional[str]:
        """提取具体事件描述"""
        entity_display = self._get_entity_display_name(entity)
        entity_lower = entity.lower()
        
        # 1. 争议事件 - 针对 Cursor 套壳 Kimi 的特殊处理
        if "cursor" in entity_lower:
            # Cursor 套壳争议
            if re.search(r'cursor.*?(?:套壳|基于|使用|built on|based on).*?kimi', text, re.IGNORECASE):
                return "Cursor套壳Kimi争议"
            if re.search(r'cursor.*?composer.*?(?:套壳|基于|使用|kimi)', text, re.IGNORECASE):
                return "Cursor Composer套壳争议"
            if re.search(r'cursor.*?(?:侵权|争议|道歉|承认)', text, re.IGNORECASE):
                return "Cursor模型争议"
        
        # 2. 收购事件 - 提取被收购方（排除常见停用词）
        stop_words = {'the', 'a', 'an', 'its', 'new', 'this', 'that', '公司', '团队'}
        acquisition_patterns = [
            r'收购[\s\w]*?([A-Z][a-zA-Z]+)[\s\w]*?(?:公司|团队|初创|startup)',
            r'(?:openai|google|meta|microsoft)[\s\w]*?acquir(?:ing|e)[\s\w]*?([A-Z][a-zA-Z]+)',
            r'([A-Z][a-zA-Z]+)[\s\w]*?(?:to join|加入)[\s\w]*?(?:openai|google|meta|microsoft)',
            r'([A-Z][a-zA-Z]+)[\s\w]*?被[\s\w]*?(?:openai|google|meta|microsoft)[\s\w]*?收购',
            r'(astral)',  # 特定公司名
        ]
        for pattern in acquisition_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                target = match.group(1).title()
                if target.lower() not in stop_words and len(target) > 1:
                    return f"{entity_display}收购{target}"
        
        # 3. 通用争议事件
        controversy_keywords = ['套壳', '抄袭', '侵权', '道歉', '承认', '争议', 'scandal', 'controversy']
        if any(kw in text.lower() for kw in controversy_keywords):
            # 提取争议对象
            match = re.search(r'(?:套壳|抄袭|侵权|基于|使用)[\s\w]*?([A-Z][a-zA-Z0-9]+)', text, re.IGNORECASE)
            if match:
                target = match.group(1).title()
                if target.lower() not in stop_words and len(target) > 1:
                    return f"{target}套壳争议"
            return f"{entity_display}争议"
        
        # 4. 功能发布 - 提取具体功能
        feature_patterns = [
            (r'(?:推出|发布|上线)[\s\w]*?([A-Z][a-z]+[\w\s]*?)[\s]*?(?:功能|feature)', "{v1}"),
            (r'([A-Z][a-z]+[\w\s]*?)[\s]*?(?:功能|feature)[\s]*?(?:上线|发布|推出)', "{v1}"),
        ]
        for pattern, template in feature_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                feature = match.group(1).strip().title()
                # 过滤掉不合适的捕获
                if feature.lower() not in stop_words and len(feature) > 2 and not feature.startswith('了'):
                    # 如果功能名已经包含实体名，直接返回功能名
                    if entity_display.lower() in feature.lower():
                        return f"{feature}功能"
                    # 否则拼接实体名和功能名
                    return f"{entity_display} {feature}功能"
        
        # 5. 对比评测 - 特别处理 Claude vs Codex
        if "claude" in entity_lower and "codex" in text.lower():
            return "Claude vs Codex对比"
        if "codex" in entity_lower and "claude" in text.lower():
            return "Codex vs Claude对比"
        
        comparison_patterns = [
            (r'(\w+)[\s\w]*?(?:vs|versus|对比|比较)[\s\w]*(\w+)[\s\w]*?(?:评测|对比|分析)', "{v1} vs {v2}对比"),
            (r'(\w+)[\s\w]*?versus[\s\w]*(\w+)', "{v1} vs {v2}对比"),
        ]
        for pattern, template in comparison_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                v1 = match.group(1).title()
                v2 = match.group(2).title()
                if v1.lower() not in stop_words and v2.lower() not in stop_words:
                    return template.format(v1=v1, v2=v2)
        
        # 6. 针对特定实体的智能命名
        if "claude" in entity_lower:
            # 检查是否是 Code 相关
            if "claude code" in text.lower():
                if "obsidian" in text.lower():
                    return "Claude Code+Obsidian集成"
                return "Claude Code使用体验"
        
        # GPT/OpenAI 相关 - 细分具体事件
        if "gpt" in entity_lower or "openai" in entity_lower:
            # 兵棋推演/模拟实验
            if any(kw in text.lower() for kw in ["兵棋", "推演", "wargame", "模拟", "核危机", "超级大国"]):
                return "AI模型兵棋推演实验"
            # GPT-5.4 mini/nano
            if "5.4" in text and any(kw in text.lower() for kw in ["mini", "nano"]):
                return "GPT-5.4 Mini/Nano发布"
            # GPT-5.4 系列
            if "5.4" in text:
                return "GPT-5.4发布"
            # GPT-5.2
            if "5.2" in text:
                return "GPT-5.2相关动态"
            # 招聘/扩招
            if any(kw in text.lower() for kw in ["招聘", "扩招", "员工", "hire", "hiring", "员工翻倍"]):
                return "OpenAI扩招计划"
            # 避免笼统的"OpenAI"
            return None  # 让上层逻辑处理或使用更具体的名称
        
        # AI兵棋推演实验
        if entity_lower == "ai_wargame_experiment":
            return "AI模型兵棋推演实验"
        
        # AI实盘交易实验
        if entity_lower == "ai_trading_experiment":
            return "AI大模型实盘交易实验"
        
        # DeepSeek 相关 - 细分具体事件
        if "deepseek" in entity_lower:
            # 人才争夺/郭达雅/罗福莉
            if any(kw in text.lower() for kw in ["郭达雅", "罗福莉", "抢", "挖", "人才", "加盟", "加入", "挖角"]):
                return "DeepSeek人才争夺"
            # 乐天套壳
            if any(kw in text.lower() for kw in ["乐天", "rakuten", "套壳", "抄袭", "删开源协议"]):
                return "乐天套壳DeepSeek争议"
            # Cursor套壳（涉及DeepSeek）
            if "cursor" in text.lower() and any(kw in text.lower() for kw in ["套壳", "kimi", "基于"]):
                return "Cursor套壳Kimi争议"
            # GEO/投毒/SEO相关
            if any(kw in text.lower() for kw in ["geo", "投毒", "seo", "优化", "灰色产业", "315"]):
                return "DeepSeek GEO优化争议"
            # 避免笼统的"DeepSeek发布"
            return None
        
        # MiniMax 相关
        if "minimax" in entity_lower:
            if "2.7" in text or "m2.7" in text.lower():
                return "MiniMax M2.7发布"
            return "MiniMax动态"
        
        # Gemini 相关 - 细分具体事件
        if "gemini" in entity_lower:
            # Flash-Lite
            if "flash-lite" in text.lower() or "flash lite" in text.lower():
                return "Gemini 3.1 Flash-Lite发布"
            # Groundsource
            if "groundsource" in text.lower():
                return "Gemini Groundsource工具"
            # 工程助手
            if any(kw in text.lower() for kw in ["工程", "engineering", "机器人", "夹爪"]):
                return "Gemini工程助手应用"
            # 避免笼统的"Gemini模型更新"
            return None
        
        # 小米AI相关
        if "xiaomi" in entity_lower or "小米" in entity_lower:
            if any(kw in text.lower() for kw in ["hunter", "alpha", "mimo", "万亿参数"]):
                return "小米Hunter Alpha模型"
            return None
        

        
        # Anthropic 相关 - 细分具体事件
        if "anthropic" in entity_lower:
            # CEO发言/预测
            if any(kw in text.lower() for kw in ["ceo", "dario", "amodei", "预测", "律师", "咨询", "金融", "淘汰", "wipe out"]):
                return "Anthropic CEO预测AI影响"
            # 偏见/教育研究
            if any(kw in text.lower() for kw in ["偏见", "教育", "学历", "educated", "less accurate", "voice ai", "语音"]):
                return "Anthropic AI偏见研究"
            # 就业/AI暴露度研究
            if any(kw in text.lower() for kw in ["就业", "工作", "job", "work", "暴露度", "exposure", "职业", "程序员"]):
                return "Anthropic AI就业影响研究"
            # Claude更新
            if any(kw in text.lower() for kw in ["claude 4", "claude 3.7", "claude 3.5", "sonnet", "opus"]):
                return "Claude模型更新"
            # 避免笼统的"Anthropic动态"
            return None
        
        # Google 相关 - 细分具体事件
        if "google" in entity_lower:
            # Project Genie
            if any(kw in text.lower() for kw in ["genie", "world", "游戏", "世界生成"]):
                return "Google Project Genie"
            # Colab MCP
            if any(kw in text.lower() for kw in ["colab", "mcp", "notebook", "jupyter"]):
                return "Google Colab MCP集成"
            # DeepMind印度合作
            if any(kw in text.lower() for kw in ["india", "印度", "partnership", "合作"]):
                return "Google DeepMind印度合作"
            # Gemini更新
            if any(kw in text.lower() for kw in ["gemini 2", "gemini 1.5", "gemini ultra", "gemini flash"]):
                return "Gemini模型更新"
            # YouTube相关
            if any(kw in text.lower() for kw in ["youtube", "播客", "podcast", "sports", "体育"]):
                return "YouTube产品动态"
            # 儿童保护/政策
            if any(kw in text.lower() for kw in ["child", "儿童", "protection", "保护", "public policy", "政策"]):
                return "Google政策动态"
            # 环境/气候研究
            if any(kw in text.lower() for kw in ["contrail", "尾迹", "climate", "气候", "eco", "环保", "flight", "航班"]):
                return "Google环境研究"
            # 避免笼统的"Google动态"
            return None
        
        return None
    
    def _extract_action_target(self, text: str, action: str) -> Optional[str]:
        """提取动作的对象/目标"""
        # 根据动作类型选择提取模式
        if action in ["收购"]:
            patterns = [
                r'收购[\s\w]*?(\w+)[\s\w]*?(?:公司|团队|startup)',
                r'acquir[\s\w]*?(\w+)',
            ]
        elif action in ["兼容", "支持"]:
            patterns = [
                r'(?:兼容|支持)[\s\w]*?(\w+)',
                r'(?:compatible|support)[\s\w]*?(\w+)',
            ]
        elif action in ["合作"]:
            patterns = [
                r'(?:与|和)[\s\w]*?(\w+)[\s\w]*?(?:合作|联手)',
                r'(?:partner|collaborat)[\s\w]*?(\w+)',
            ]
        else:
            return None
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).title()
        
        return None
    
    def extract_entities(self, text: str) -> Set[str]:
        """从文本中提取实体关键词（向后兼容）"""
        text_lower = text.lower()
        entities = set()
        
        for keyword, priority, category in self.ENTITY_KEYWORDS:
            if keyword in text_lower:
                entities.add(keyword)
        
        return entities
    
    def find_or_create_topic(self, atom: Atom) -> Optional[Topic]:
        """
        为内容找到或创建话题
        
        策略：
        1. 提取话题签名（实体+动作+事件签名）
        2. 优先匹配相同事件签名的话题
        3. 否则匹配实体和动作
        4. 否则创建新话题
        """
        text = f"{atom.title} {atom.summary}"
        entities, main_entity, action, event_signature = self.extract_topic_signature(text)
        
        # 添加atom自带的entities
        entities.update(e.lower() for e in atom.entities)
        
        if not entities or not main_entity:
            return None
        
        # 尝试匹配已有话题
        best_match = None
        best_overlap = 0
        
        for topic_id, topic in self.topics.items():
            # 策略1: 事件签名匹配（最高优先级，跨分类）
            if event_signature and hasattr(topic, 'event_signature') and topic.event_signature == event_signature:
                best_match = topic
                best_overlap = 100  # 事件签名匹配直接选中
                break
            
            # 策略2: 实体重叠 + 动作匹配（同分类）
            if topic.category != atom.category:
                continue  # 不同分类不聚合（事件签名已处理跨分类）
            
            # 核心检查：主实体必须匹配（防止不相关内容被聚类）
            topic_main_entity = getattr(topic, 'main_entity', None)
            if topic_main_entity and main_entity:
                # 检查主实体是否相同或者是包含关系
                if topic_main_entity != main_entity:
                    # 允许部分匹配（如 "qwen" 和 "qwen3.5" 可以匹配）
                    if not (topic_main_entity in main_entity or main_entity in topic_main_entity):
                        continue  # 主实体不匹配，跳过这个话题
            
            overlap = len(entities & topic.keywords)
            
            # 必须有足够的实体重叠才能匹配（防止弱关联内容被聚类）
            if overlap == 0:
                continue  # 没有实体重叠，不能匹配
            
            # 如果有动作，优先匹配相同动作的话题
            if action and hasattr(topic, 'action') and topic.action == action:
                overlap += 5  # 动作匹配加权（降低权重，避免action主导匹配）
            
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = topic
        
        if best_match and best_overlap > 0:
            best_match.add_atom(atom)
            self.atom_to_topic[atom.id] = best_match.id
            return best_match
        
        # 创建新话题
        # 先生成话题名称（传入当前atom作为初始内容）
        topic_name = self.generate_topic_name(main_entity, action, [atom])
        
        topic_id = f"topic_{atom.category}_{main_entity}_{action or 'related'}_{atom.id.split('_')[-1]}"
        
        new_topic = Topic(
            id=topic_id,
            name=topic_name,
            category=atom.category,
            keywords=entities
        )
        new_topic.action = action  # 保存动作用于后续匹配
        new_topic.main_entity = main_entity  # 保存主实体
        new_topic.event_signature = event_signature  # 保存事件签名
        new_topic.add_atom(atom)
        
        self.topics[topic_id] = new_topic
        self.atom_to_topic[atom.id] = topic_id
        
        return new_topic
    
    def cluster_atoms(self, atoms: List[Atom]) -> List[Topic]:
        """批量聚类内容"""
        for atom in atoms:
            self.find_or_create_topic(atom)
        
        # 重新生成话题名称（基于所有atoms的内容）
        for topic in self.topics.values():
            if len(topic.atoms) > 0:
                # 获取话题的主实体和动作
                main_entity = getattr(topic, 'main_entity', None)
                action = getattr(topic, 'action', None)
                if main_entity:
                    # 重新生成名称，传入所有atoms
                    new_name = self.generate_topic_name(main_entity, action, topic.atoms)
                    topic.name = new_name
        
        # 返回按热度排序的话题
        return sorted(self.topics.values(), key=lambda t: t.heat_score, reverse=True)
    
    def get_atom_topic(self, atom_id: str) -> Optional[str]:
        """获取内容所属话题ID"""
        return self.atom_to_topic.get(atom_id)


def load_atoms_from_jsonl(jsonl_path: Path) -> List[Atom]:
    """从JSONL加载内容"""
    atoms = []
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                atom = Atom(
                    id=data.get('id', ''),
                    title=data.get('title', ''),
                    summary=data.get('summary_zh', data.get('title', '')),
                    author=data.get('source', {}).get('author', 'unknown'),
                    platform=data.get('source', {}).get('platform', 'unknown'),
                    url=data.get('source', {}).get('url', ''),
                    category=data.get('category', 'other'),
                    entities=data.get('entities', []),
                    tags=data.get('tags', []),
                    timestamp=data.get('source', {}).get('timestamp', ''),
                    metrics=data.get('metrics', {}),
                    trust=data.get('trust_default', 'L3')
                )
                atoms.append(atom)
            except json.JSONDecodeError:
                continue
    
    return atoms


def generate_topic_report(date: str, channel: str = "all") -> str:
    """生成话题报告"""
    archive_dir = Path(__file__).parent.parent / "archive" / "daily" / date
    
    all_atoms = []
    channels = ["x", "weibo", "rss"] if channel == "all" else [channel]
    
    for ch in channels:
        jsonl_path = archive_dir / f"{ch}.jsonl"
        if jsonl_path.exists():
            atoms = load_atoms_from_jsonl(jsonl_path)
            all_atoms.extend(atoms)
    
    if not all_atoms:
        return "无数据"
    
    # 聚类
    cluster = TopicCluster()
    topics = cluster.cluster_atoms(all_atoms)
    
    # 生成报告
    lines = []
    lines.append("=" * 70)
    lines.append(f"🔥 热点话题报告 - {date}")
    lines.append("=" * 70)
    lines.append(f"\n总计: {len(all_atoms)} 条内容 → {len(topics)} 个话题\n")
    
    # 按分类分组展示
    by_category = defaultdict(list)
    for topic in topics:
        by_category[topic.category].append(topic)
    
    for cat, cat_topics in sorted(by_category.items()):
        lines.append(f"\n{'─' * 70}")
        lines.append(f"📂 {cat.upper()} ({len(cat_topics)}个话题)")
        lines.append('─' * 70)
        
        for i, topic in enumerate(cat_topics[:10], 1):  # 每类最多10个
            lines.append(f"\n{i}. 🔥 {topic.heat_score:.0f} {topic.name}")
            lines.append(f"   内容数: {len(topic.atoms)} | 信源: {', '.join(topic.get_top_sources(3))}")
            
            # 显示各平台分布
            platform_counts = Counter(a.platform for a in topic.atoms)
            platform_str = ' | '.join(f"{p}:{c}" for p, c in platform_counts.most_common())
            lines.append(f"   平台: {platform_str}")
            
            # 显示最高热度内容
            top_atom = max(topic.atoms, key=lambda a: {
                "L1": 3, "L2": 2, "L3": 1
            }.get(a.trust, 1))
            lines.append(f"   💬 {top_atom.summary[:80]}...")
    
    # 未聚类的内容（other分类且没有匹配到话题）
    other_atoms = [a for a in all_atoms if a.category == "other" and a.id not in cluster.atom_to_topic]
    if other_atoms:
        lines.append(f"\n{'─' * 70}")
        lines.append(f"📋 未聚类内容 ({len(other_atoms)}条)")
        lines.append('─' * 70)
        for atom in other_atoms[:5]:
            lines.append(f"  • @{atom.author}: {atom.title[:60]}...")
    
    lines.append(f"\n{'=' * 70}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="话题聚类与热度排序")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--channel", default="all", choices=["x", "weibo", "rss", "all"])
    parser.add_argument("--save", action="store_true", help="保存到文件")
    
    args = parser.parse_args()
    
    report = generate_topic_report(args.date, args.channel)
    
    if args.save:
        report_dir = Path(__file__).parent.parent / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{args.date}_topics.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ 报告已保存: {report_path}")
    else:
        print(report)
