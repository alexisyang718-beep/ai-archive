#!/usr/bin/env python3
"""
    Collector — v2 统一采集入口

职责：
1. 从各信源（X/微博/RSS）采集原始数据
2. 将原始数据统一转化为 Atom 格式
3. 通过 AtomStore 持久化到 JSONL

本脚本是**框架骨架**，定义了接口和数据流。
具体的采集逻辑（调用 twitter-cli、weibo-cli 等）需要在各 adapter 中实现。

使用方式：
    # 完整采集（按 L0→L0.5→L1 顺序）
    python3 collector.py
    
    # 只采集 X
    python3 collector.py --source x
    
    # 只采集微博
    python3 collector.py --source weibo
    
    # 只采集 RSS
    python3 collector.py --source rss
    
    # 从已有 JSON 文件导入
    python3 collector.py --import-file /path/to/tweets.json --source x
"""

import json
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 添加 v2/scripts 到 path
sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore, create_atom

# 导入作者学习器
try:
    from author_learner import AuthorCategoryLearner, get_learner
    AUTHOR_LEARNER_AVAILABLE = True
except ImportError:
    AUTHOR_LEARNER_AVAILABLE = False
    print("⚠️ author_learner 模块未找到，自动学习功能不可用")


# ====================================================================
# 工具函数：带重试的 subprocess 调用
# ====================================================================

def _retry_subprocess(cmd, max_retries=2, timeout=60, **kwargs):
    """带重试的 subprocess.run 封装"""
    import time
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kwargs)
            return result
        except subprocess.TimeoutExpired as e:
            last_err = e
            if attempt < max_retries:
                wait = 2 ** attempt  # 指数退避：1s, 2s
                print(f"    ⏱️ 超时，{wait}s 后重试 ({attempt+1}/{max_retries})...", flush=True)
                time.sleep(wait)
        except Exception as e:
            last_err = e
            break
    raise last_err

# ============ 配置 ============
PROJECT_ROOT = Path(__file__).parent.parent.parent  # tech-daily-brief/
V2_ROOT = Path(__file__).parent.parent              # tech-daily-brief/v2/
CONFIG_DIR = PROJECT_ROOT / "config"

# 环境变量（可通过 .env 或 export 自定义）
PATH_ENV = os.environ.get(
    "COLLECTOR_PATH",
    os.path.expanduser("~/.local/bin") + ":/Library/Frameworks/Python.framework/Versions/3.13/bin:/usr/local/bin:/usr/bin:/bin"
)

# Obsidian vault 路径（可选，仅同步功能需要）
OBSIDIAN_VAULT = Path(os.environ.get(
    "OBSIDIAN_VAULT",
    "~/Documents/Obsidian/资讯"
)).expanduser()


# ====================================================================
# 第零部分：规则标注器（RuleBasedAnnotator）
# 基于 keyword 匹配自动判断 category/tags/entities
# ====================================================================

class RuleBasedAnnotator:
    """
    基于规则的标注器 —— 不需要 AI，纯关键词匹配 + 正则词边界。
    
    在采集时自动为推文/微博打上 category、tags、entities 标签。
    v2.1: 使用 re 词边界匹配短词，避免 "said" 误匹配 "ai" 等问题。
    """
    
    # 作者→分类提示（当纯文本关键词不够时，作者身份可以辅助判断）
    AUTHOR_CATEGORY_HINTS = {
        # ===== X 官方账号 =====
        "@openai": "ai_models",
        "@anthropic": "ai_models",
        "@google": "ai_models",
        "@googleai": "ai_models",
        "@nvidia": "chips",
        "@deepmind": "ai_models",
        "@metaai": "ai_models",
        "@xai": "ai_models",
        "@mistralai": "ai_models",
        "@deepseek_ai": "ai_models",
        "@huggingface": "ai_models",
        "@stability_ai": "ai_models",
        "@midjourney": "ai_models",
        "@runwayml": "ai_models",
        "@perplexity_ai": "ai_models",
        "@cursor_ai": "software_dev",
        "@github": "software_dev",
        "@vercel": "software_dev",
        "@cloudflare": "internet_tech",
        "@supabase": "software_dev",
        
        # ===== X AI 研究员/专家 (T1) =====
        "@simonwillison": "ai_models",  # Simon Willison - AI 工具分析
        "@karpathy": "ai_models",       # Andrej Karpathy
        "@drjimfan": "ai_models",       # Jim Fan - NVIDIA
        "@ylecun": "ai_models",         # Yann LeCun
        "@demishassabis": "ai_models",  # Demis Hassabis
        "@sama": "ai_models",           # Sam Altman
        "@darioamodei": "ai_models",    # Dario Amodei
        "@alexalbert__": "ai_models",   # Alex Albert - Anthropic
        "@goodside": "ai_models",       # Riley Goodside - Prompt 专家
        "@bindureddy": "ai_models",     # Bindu Reddy
        "@emollick": "ai_models",       # Ethan Mollick - AI 教育
        "@jeremyphoward": "ai_models",  # Jeremy Howard - Fast.ai
        "@gwern": "ai_models",          # Gwern - AI 研究
        "@hardmaru": "ai_models",       # David Ha - AI 研究
        "@lilianweng": "ai_models",     # Lilian Weng - OpenAI
        "@sh_reya": "ai_models",        # Shreya Shankar - AI 工程
        "@swyx": "ai_models",           # Shawn Wang - AI 工程
        "@matthewberman": "ai_models",  # Matthew Berman - AI 评测
        "@theomojica": "ai_models",     # Theo - AI 产品
        "@aidailybrief": "ai_models",   # AI Daily Brief
        "@benparr": "ai_models",        # Ben Parr
        "@mreflow": "ai_models",        # Matt Mireles
        "@itsandrewgao": "ai_models",   # Andrew Gao
        "@rohanpaul_ai": "ai_models",   # Rohan Paul - AI 教程
        "@omarsar0": "ai_models",       # Elvis Saravia - AI 研究
        "@svpino": "ai_models",         # Santiago - AI 工程
        "@jamesbridle": "ai_models",    # James Bridle
        "@kwindla": "ai_models",        # Kwindla Hultman Kramer
        
        # ===== X 科技投资人/创始人 =====
        "@garrytan": "tech_industry",   # Garry Tan - YC
        "@paulg": "tech_industry",      # Paul Graham
        "@jason": "tech_industry",      # Jason Calacanis
        "@eladgil": "tech_industry",    # Elad Gil
        "@suhail": "tech_industry",     # Suhail - Playground
        "@natfriedman": "tech_industry", # Nat Friedman
        "@gdb": "tech_industry",        # Greg Brockman
        "@ilyasut": "ai_models",        # Ilya Sutskever
        "@geoffreyhinton": "ai_models", # Geoffrey Hinton
        "@fchollet": "ai_models",       # François Chollet
        "@jeremyphoward": "ai_models",  # Jeremy Howard
        
        # ===== X 芯片/硬件专家 =====
        "@dylan522p": "chips",          # Dylan Patel - SemiAnalysis
        "@irismchu": "chips",           # Iris Hsu
        "@danielnewmanuv": "chips",     # Daniel Newman
        "@patrickmoorhead": "chips",    # Patrick Moorhead
        "@geoffreyhinton": "ai_models", # Geoffrey Hinton
        "@drjimfan": "ai_models",       # Jim Fan
        
        # ===== X 开发者工具/编程 =====
        "@levelsio": "software_dev",    # Pieter Levels
        "@marc_louvion": "software_dev", # Marc Lou
        "@theo": "software_dev",        # Theo - t3.gg
        "@t3dotgg": "software_dev",     # Theo
        "@leeerob": "software_dev",     # Lee Robinson - Vercel
        "@rauchg": "software_dev",      # Guillermo Rauch - Vercel
        "@shadcn": "software_dev",      # shadcn
        "@midudev": "software_dev",     # Miguel Angel Duran
        "@traversymedia": "software_dev", # Brad Traversy
        "@fireship": "software_dev",    # Fireship
        "@addyosmani": "software_dev",  # Addy Osmani
        "@kentcdodds": "software_dev",  # Kent C. Dodds
        "@dan_abramov": "software_dev", # Dan Abramov
        "@ryanflorence": "software_dev", # Ryan Florence
        "@tannerlinsley": "software_dev", # Tanner Linsley
        
        # ===== X 游戏 =====
        "@kazuma_yamauchi": "gaming",   # 山内一典 - GT赛车
        "@toddhoward": "gaming",        # Todd Howard - Bethesda
        "@tim_sweeney": "gaming",       # Tim Sweeney - Epic
        "@markcerny": "gaming",         # Mark Cerny - PlayStation
        "@shahidkamal": "gaming",       # Shahid Ahmad
        
        # ===== X 媒体/记者 =====
        "@techcrunch": "tech_industry",
        "@theverge": "tech_industry",
        "@wired": "tech_industry",
        "@arstechnica": "tech_industry",
        "@reuters": "policy",
        "@reutersbiz": "policy",
        "@bloomberg": "policy",
        "@business": "policy",
        "@cnbc": "tech_industry",
        "@wsj": "policy",
        "@chinesewsj": "policy",
        "@bbcworld": "policy",
        "@platformer": "tech_industry",  # Casey Newton
        "@martin_casado": "tech_industry", # Martin Casado
        "@stratechery": "tech_industry", # Ben Thompson
        "@zaobaosg": "policy",
        "@koreatimescokr": "policy",
        "@buzzfeed": "tech_industry",
        
        # ===== X 游戏媒体 =====
        "@ign": "gaming",
        "@pcgamer": "gaming",
        "@genki_jpn": "gaming",
        
        # ===== X 金融/市场 =====
        "@polymarket": "policy",
        "@cnfinancewatch": "tech_industry",
        "@fxtrader": "tech_industry",
        "@stocksavvyshay": "tech_industry",
        
        # ===== 微博用户 =====
        "数码闲聊站": "mobile",
        "机器之心pro": "ai_models",
        "机器之心": "ai_models",
        "量子位": "ai_models",
        "新智元": "ai_models",
        "36氪": "tech_industry",
        "虎嗅app": "tech_industry",
        "宝玉xp": "ai_models",
        "歸藏的ai工具箱": "ai_models",
        "karminski-牙医": "ai_models",
        "林亦lyi": "ai_models",
        "阑夕": "tech_industry",
        "互联网怪盗团": "tech_industry",
    }

    # 板块关键词
    # 格式：每个词如果 <= 4 字符且纯 ASCII，自动使用词边界 \b 匹配
    CATEGORY_KEYWORDS = {
        "ai_models": [
            # 公司/品牌
            "openai", "chatgpt", "anthropic", "deepmind", "google ai",
            "meta ai", "mistral", "deepseek", "perplexity", "huggingface",
            "hugging face", "cohere", "stability ai", "together ai",
            # 产品/模型
            "gpt-4", "gpt-4o", "gpt-5", "claude", "gemini", "llama",
            "grok", "midjourney", "copilot", "sora", "dall-e", "dall·e",
            "stable diffusion", "runway", "flux", "whisper",
            # 技术术语
            "llm", "大模型", "大语言模型", "large language model",
            "transformer", "diffusion model", "neural network", "deep learning",
            "machine learning", "reinforcement learning", "rlhf", "rag",
            "fine-tune", "finetune", "微调", "fine tuning",
            "embedding", "vector database", "向量数据库",
            "prompt engineering", "prompt", "token limit",
            "reasoning model", "chain of thought", "思维链",
            "multimodal", "多模态", "vision language", "text to image",
            "text to video", "text to speech", "text to code",
            "ai agent", "ai coding", "ai编程", "agentic",
            "mcp protocol", "function calling", "tool use",
            "aigc", "生成式ai", "generative ai",
            "对齐", "alignment", "safety", "ai安全",
            "开源模型", "open source model", "open weight",
            "benchmark", "评测", "leaderboard",
            "inference", "推理", "训练", "training", "预训练",
            # AI Coding 相关（从 software_dev 移过来的核心词）
            "vibe coding", "coding agent", "code agent", "devin",
            # 中国 AI
            "智谱", "glm", "通义千问", "qwen", "百川", "baichuan", "minimax",
            "月之暗面", "moonshot", "kimi", "零一万物", "阶跃星辰", "stepfun",
            "文心一言", "ernie", "混元", "hunyuan", "豆包", "doubao",
            "天工", "skywork", "讯飞星火", "spark", "abab",
            # 应用场景
            "chatbot", "聊天机器人", "ai assistant", "ai助手",
            "code generation", "代码生成", "ai搜索", "ai search",
            "ai写作", "ai绘画", "ai视频", "ai音乐",
            # 开发工具（从 software_dev 合并过来的核心词）
            "cursor", "windsurf", "devin", "github copilot", "codeium",
            "vscode", "vs code", "visual studio", "jetbrains", "intellij",
            "xcode", "android studio",
            # 语言/框架
            "python", "javascript", "typescript", "rust", "golang",
            "react", "vue", "nextjs", "next.js", "svelte",
            "node.js", "nodejs", "deno", "bun",
            # 云/基础设施
            "kubernetes", "docker", "aws", "azure", "gcp",
            "cloudflare", "vercel", "supabase", "firebase",
            "serverless", "microservice", "微服务",
            # 数据库
            "postgresql", "mysql", "mongodb", "redis", "sqlite",
            # 开源/社区
            "github", "开源", "open source", "apache", "linux",
            "开发者", "developer", "程序员", "programmer",
            "编程", "coding", "代码", "debug", "api",
            "sdk", "框架", "framework", "library",
            "devops", "cicd", "ci/cd",
        ],
        "mobile": [
            "apple", "iphone", "samsung galaxy", "pixel phone", "折叠屏", "foldable",
            "华为手机", "华为mate", "华为p", "小米手机", "红米", "redmi",
            "oppo find", "vivo x", "荣耀magic", "一加", "oneplus",
            "realme", "iqoo",
            "ar眼镜", "ar glasses", "vision pro", "quest",
            "骁龙", "snapdragon", "天玑", "dimensity", "exynos",
            "a17 pro", "a18 pro", "a19 pro", "m4", "m5",
            "手机发布", "手机评测", "新机", "旗舰机",
            "手机壳", "保护壳", "屏幕", "display", "刷新率",
            "续航", "battery life",
            "ios 18", "ios 19", "android 15", "android 16",
            "鸿蒙", "harmonyos", "harmony os",
            "airpods", "apple watch", "galaxy watch",
            "ipad", "平板电脑", "tablet",
            "wearable", "可穿戴",
        ],
        "chips": [
            "nvidia", "英伟达", "黄仁勋", "jensen huang",
            "tsmc", "台积电", "三星晶圆", "samsung foundry",
            "intel", "英特尔", "amd",
            "gpu", "芯片", "semiconductor", "半导体",
            "ai芯片", "ai chip", "ai accelerator",
            "h100", "h200", "b100", "b200", "gb200", "blackwell", "rubin",
            "a100", "cuda", "tensor core", "rocm",
            "昇腾", "ascend", "寒武纪", "cambricon",
            "算力", "compute", "数据中心", "data center",
            "ai服务器", "ai server", "ai基础设施", "ai infrastructure",
            "液冷", "liquid cooling",
            "制程", "nm工艺", "晶圆", "wafer", "foundry",
            "amd epyc", "amd instinct", "intel gaudi",
            "高通", "qualcomm", "联发科", "mediatek",
            "npu", "neural engine", "tpu",
            "asic", "fpga", "risc-v",
            "光刻机", "euv", "asml",
            "shader", "显卡", "graphics card",
            "供应链", "supply chain",
            # 智能汽车/电动车（从 ev_auto 合并）
            "特斯拉", "tesla", "马斯克", "elon musk",
            "比亚迪", "byd", "蔚来", "nio", "小鹏", "xpeng",
            "理想汽车", "li auto", "问界", "aito",
            "电动车", "电动汽车", "新能源车", "ev",
            "自动驾驶", "autonomous driving", "self-driving",
            "智能驾驶", "智驾", "adas", "lidar", "激光雷达",
            "充电桩", "充电站", "电池", "battery", "固态电池",
            "车机", "车载", "carplay", "车联网",
        ],
        "gaming": [
            "playstation", "xbox", "nintendo", "switch 2",
            "steam", "epic games", "game pass",
            "steam deck", "rog ally", "掌机", "handheld",
            "云游戏", "cloud gaming",
            "游戏", "gta", "gaming industry",
            "ps5", "ps6", "gta6", "gta vi",
            "虚幻引擎", "unreal engine", "unity engine",
            "米哈游", "mihoyo", "原神", "genshin",
            "王者荣耀", "英雄联盟", "league of legends",
            "电竞", "esports", "游戏主机", "console",
            "indie game", "独立游戏", "3a游戏", "aaa game",
            "游戏开发", "game dev",
        ],
        "tech_industry": [
            "融资", "acquisition", "收购", "并购", "merger",
            "ipo上市", "ipo", "裁员", "layoff", "layoffs",
            "revenue", "earnings", "营收", "财报", "利润",
            "market cap", "估值", "valuation",
            "投资", "funding", "series a", "series b", "series c",
            "startup", "独角兽", "unicorn", "创业",
            "风投", "venture capital", "angel investor", "天使投资",
            "科技公司", "tech company", "tech industry", "科技行业",
            "tech giant", "big tech", "硅谷", "silicon valley",
        ],
        "policy": [
            "regulation", "监管", "监管政策", "政策法规", "政策",
            "制裁", "sanctions", "export control", "出口管制",
            "关税", "tariff", "贸易战", "trade war", "贸易",
            "国产替代", "信创", "自主可控",
            "antitrust", "反垄断", "反竞争", "垄断",
            "隐私", "privacy", "gdpr", "数据安全", "data protection", "网络安全",
            "欧盟ai法案", "eu ai act", "ai法案", "人工智能法案",
            "工信部", "网信办", "ftc", "sec", "doj", "司法部",
            "地缘政治", "geopolitics", "国际关系", "外交",
            "中美", "中欧", "中俄", "中印", "台海", "南海",
            "政府", "government", "国会", "议会", "congress", "parliament",
            "总统", "president", "特朗普", "trump", "拜登", "biden",
            "选举", "election", "投票", "vote", "大选",
            "军事", "military", "战争", "war", "冲突", "conflict",
            "情报", "intelligence", "cia", "fbi", "nsa",
            "能源", "energy", "石油", "天然气", "opec",
            "气候", "climate", "环保", "碳中和", "碳排放",
            "央行", "利率", "加息", "降息", "通胀", "inflation",
            "银行", "bank", "金融", "finance", "经济", "economy",
            "市场", "market", "股市", "stock market", "华尔街", "wall street",
            "路透社", "reuters", "彭博社", "bloomberg", "华尔街日报", "wsj",
            "bbc", "cnn", "fox", "半岛电视台", "al jazeera",
        ],
    }
    
    # 实体提取规则（关键词 → 标准实体名）
    # 🚫 硬性规则：索引键统一小写，显示时用原始大小写
    ENTITY_MAP = {
        # AI 公司
        "openai": "OpenAI",
        "chatgpt": "ChatGPT",
        "gpt-5": "GPT-5",
        "gpt5": "GPT-5",
        "gpt-4": "GPT-4",
        "gpt4": "GPT-4",
        "gpt-4o": "GPT-4o",
        "gpt4o": "GPT-4o",
        "gpt-5.4": "GPT-5.4",
        "o1": "OpenAI o1",
        "o3": "OpenAI o3",
        "o4": "OpenAI o4",
        "sora": "Sora",
        "anthropic": "Anthropic",
        "claude": "Claude",
        "google": "Google",
        "deepmind": "DeepMind",
        "gemini": "Gemini",
        "nvidia": "NVIDIA",
        "jensen huang": "Jensen Huang",
        "黄仁勋": "Jensen Huang",
        "apple": "Apple",
        "tim cook": "Tim Cook",
        "库克": "Tim Cook",
        "meta": "Meta",
        "mark zuckerberg": "Mark Zuckerberg",
        "扎克伯格": "Mark Zuckerberg",
        "llama": "Llama",
        "microsoft": "Microsoft",
        "copilot": "Copilot",
        "satya nadella": "Satya Nadella",
        "纳德拉": "Satya Nadella",
        "tesla": "Tesla",
        "elon musk": "Elon Musk",
        "马斯克": "Elon Musk",
        "xai": "xAI",
        "grok": "Grok",
        "deepseek": "DeepSeek",
        "深度求索": "DeepSeek",
        "mistral": "Mistral",
        "midjourney": "Midjourney",
        "huggingface": "HuggingFace",
        "perplexity": "Perplexity",
        "cursor": "Cursor",
        "github": "GitHub",
        # 中国公司
        "华为": "Huawei",
        "huawei": "Huawei",
        "小米": "Xiaomi",
        "xiaomi": "Xiaomi",
        "雷军": "Lei Jun",
        "oppo": "OPPO",
        "vivo": "vivo",
        "荣耀": "Honor",
        "honor": "Honor",
        "比亚迪": "BYD",
        "byd": "BYD",
        "大疆": "DJI",
        "dji": "DJI",
        # 中国 AI
        "智谱": "Zhipu AI",
        "zhipu": "Zhipu AI",
        "glm": "GLM",
        "通义千问": "Qwen",
        "qwen": "Qwen",
        "阿里云": "Alibaba Cloud",
        "百川": "Baichuan",
        "baichuan": "Baichuan",
        "minimax": "MiniMax",
        "月之暗面": "Moonshot",
        "moonshot": "Moonshot",
        "kimi": "Kimi",
        "零一万物": "Yi",
        "yi model": "Yi",
        "阶跃星辰": "StepFun",
        "stepfun": "StepFun",
        # 芯片
        "tsmc": "TSMC",
        "台积电": "TSMC",
        "amd": "AMD",
        "苏姿丰": "Lisa Su",
        "lisa su": "Lisa Su",
        "intel": "Intel",
        "高通": "Qualcomm",
        "qualcomm": "Qualcomm",
        "联发科": "MediaTek",
        "mediatek": "MediaTek",
        "寒武纪": "Cambricon",
        "cambricon": "Cambricon",
        "昇腾": "Ascend",
        "ascend": "Ascend",
        # 手机
        "iphone": "iPhone",
        "samsung": "Samsung",
        "三星": "Samsung",
        "pixel": "Google Pixel",
        "fold": "Galaxy Fold",
        # 游戏
        "nintendo": "Nintendo",
        "任天堂": "Nintendo",
        "switch": "Nintendo Switch",
        "索尼": "Sony",
        "sony": "Sony",
        "playstation": "PlayStation",
        "ps5": "PlayStation 5",
        "xbox": "Xbox",
        "valve": "Valve",
        "steam": "Steam",
        "米哈游": "miHoYo",
        "mihoyo": "miHoYo",
        "原神": "Genshin Impact",
        "genshin": "Genshin Impact",
        # 人物
        "sam altman": "Sam Altman",
        "sama": "Sam Altman",
        "dario amodei": "Dario Amodei",
        "demis hassabis": "Demis Hassabis",
        "yann lecun": "Yann LeCun",
        "lecun": "Yann LeCun",
        "karpathy": "Andrej Karpathy",
        "andrej karpathy": "Andrej Karpathy",
        "jim fan": "Jim Fan",
        "drjimfan": "Jim Fan",
        # 产品
        "vision pro": "Vision Pro",
        "visionpro": "Vision Pro",
        "airpods": "AirPods",
        "galaxy": "Samsung Galaxy",
        
        # ===== 新增 AI 公司/产品 =====
        "cohere": "Cohere",
        "stability ai": "Stability AI",
        "stable diffusion": "Stable Diffusion",
        "runway": "Runway",
        "flux": "Flux",
        "whisper": "Whisper",
        "together ai": "Together AI",
        "hugging face": "HuggingFace",
        "manus": "Manus AI",
        "manus ai": "Manus AI",
        "豆包": "Doubao",
        "doubao": "Doubao",
        "文心一言": "ERNIE Bot",
        "ernie": "ERNIE Bot",
        "混元": "Hunyuan",
        "hunyuan": "Hunyuan",
        "天工": "Skywork",
        "skywork": "Skywork",
        "讯飞星火": "iFlytek Spark",
        "spark": "iFlytek Spark",
        "abab": "MiniMax ABAB",
        
        # ===== 新增芯片/硬件 =====
        "h100": "NVIDIA H100",
        "h200": "NVIDIA H200",
        "b100": "NVIDIA B100",
        "b200": "NVIDIA B200",
        "gb200": "NVIDIA GB200",
        "blackwell": "NVIDIA Blackwell",
        "rubin": "NVIDIA Rubin",
        "a100": "NVIDIA A100",
        "hopper": "NVIDIA Hopper",
        "grace": "NVIDIA Grace",
        "骁龙": "Snapdragon",
        "snapdragon": "Snapdragon",
        "天玑": "Dimensity",
        "dimensity": "Dimensity",
        "exynos": "Samsung Exynos",
        "a17 pro": "Apple A17 Pro",
        "a18 pro": "Apple A18 Pro",
        "m4": "Apple M4",
        "m5": "Apple M5",
        
        # ===== 新增手机品牌/产品 =====
        "一加": "OnePlus",
        "oneplus": "OnePlus",
        "realme": "Realme",
        "红米": "Redmi",
        "redmi": "Redmi",
        "小米su7": "Xiaomi SU7",
        "小米汽车": "Xiaomi Auto",
        "ipad": "iPad",
        "macbook": "MacBook",
        "mac pro": "Mac Pro",
        
        # ===== 新增互联网公司 =====
        "腾讯": "Tencent",
        "tencent": "Tencent",
        "阿里巴巴": "Alibaba",
        "alibaba": "Alibaba",
        "字节跳动": "ByteDance",
        "bytedance": "ByteDance",
        "百度": "Baidu",
        "baidu": "Baidu",
        "美团": "Meituan",
        "meituan": "Meituan",
        "京东": "JD.com",
        "拼多多": "PDD",
        "pinduoduo": "PDD",
        "网易": "NetEase",
        "netease": "NetEase",
        "bilibili": "Bilibili",
        "哔哩哔哩": "Bilibili",
        "抖音": "Douyin",
        "tiktok": "TikTok",
        "小红书": "Xiaohongshu",
        "快手": "Kuaishou",
        "kuaishou": "Kuaishou",
        "spotify": "Spotify",
        "netflix": "Netflix",
        "amazon": "Amazon",
        "aws": "AWS",
        
        # ===== 新增汽车 =====
        "蔚来": "NIO",
        "nio": "NIO",
        "小鹏": "XPeng",
        "xpeng": "XPeng",
        "理想汽车": "Li Auto",
        "li auto": "Li Auto",
        "问界": "AITO",
        "aito": "AITO",
        
        # ===== 新增游戏 =====
        "epic games": "Epic Games",
        "epic": "Epic Games",
        "game pass": "Xbox Game Pass",
        "switch 2": "Nintendo Switch 2",
        "unreal engine": "Unreal Engine",
        "虚幻引擎": "Unreal Engine",
        "unity": "Unity",
        
        # ===== 新增人物 =====
        "李彦宏": "Robin Li",
        "robin li": "Robin Li",
        "马化腾": "Pony Ma",
        "pony ma": "Pony Ma",
        "jack dorsey": "Jack Dorsey",
        "sundar pichai": "Sundar Pichai",
        "craig federighi": "Craig Federighi",
        
        # ===== 新增平台/产品 =====
        "windsurf": "Windsurf",
        "devin": "Devin",
        "vercel": "Vercel",
        "supabase": "Supabase",
        "cloudflare": "Cloudflare",
        "product hunt": "Product Hunt",
    }
    
    # 编译正则缓存（类级别，只编译一次）
    _regex_cache = {}
    
    @classmethod
    def _build_regex(cls, keyword: str):
        """为关键词构建匹配正则（带缓存）"""
        import re
        if keyword not in cls._regex_cache:
            # 纯 ASCII 且 <= 4 字符的英文词：使用词边界 \b 匹配
            # 避免 "ai" 匹配到 "said", "ar" 匹配到 "are" 等
            if keyword.isascii() and len(keyword) <= 4 and keyword.isalpha():
                cls._regex_cache[keyword] = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
            else:
                cls._regex_cache[keyword] = None  # 非短词，用简单 in 匹配
        return cls._regex_cache[keyword]
    
    def annotate(self, text: str, author: str = "") -> dict:
        """
        分析文本，返回 category/tags/entities。
        
        v2.1: 短英文词用 \\b 词边界匹配，长词/中文用 in 匹配。
        
        Args:
            text: 要分析的文本内容
            author: 作者名（可选，用于辅助判断）
            
        Returns:
            {
                "category": str,      # 板块分类
                "tags": List[str],    # 标签列表（小写）
                "entities": List[str] # 实体列表（保留原始大小写）
            }
        """
        text_lower = text.lower()
        
        def _kw_in_text(kw: str) -> bool:
            """检查关键词是否在文本中，短英文词用词边界匹配"""
            regex = self._build_regex(kw)
            if regex is not None:
                return bool(regex.search(text_lower))
            return kw in text_lower
        
        # 1. 板块分类：匹配关键词最多的板块
        cat_scores = {}
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if _kw_in_text(kw))
            if score > 0:
                cat_scores[cat] = score
        
        # 作者提示加权：如果作者能映射到分类，+3 分
        author_hint_used = False
        if author:
            author_key = author.lower().strip()
            # 支持带@和不带@两种格式
            if author_key in self.AUTHOR_CATEGORY_HINTS:
                hinted_cat = self.AUTHOR_CATEGORY_HINTS[author_key]
                cat_scores[hinted_cat] = cat_scores.get(hinted_cat, 0) + 3
                author_hint_used = True
            elif f"@{author_key}" in self.AUTHOR_CATEGORY_HINTS:
                hinted_cat = self.AUTHOR_CATEGORY_HINTS[f"@{author_key}"]
                cat_scores[hinted_cat] = cat_scores.get(hinted_cat, 0) + 3
                author_hint_used = True
            
            # 如果硬编码映射表中没有，尝试自动学习的映射
            if not author_hint_used and AUTHOR_LEARNER_AVAILABLE:
                learner = get_learner()
                learned_cat = learner.get_author_category(author)
                if learned_cat:
                    # 自动学习的权重稍低 (+2分)
                    cat_scores[learned_cat] = cat_scores.get(learned_cat, 0) + 2
        
        # 只保留6大板块，没有匹配到任何关键词时归入 tech_industry（而非 other）
        VALID_CATEGORIES = {"ai_models", "mobile", "chips", "gaming", "tech_industry", "policy"}
        filtered_scores = {k: v for k, v in cat_scores.items() if k in VALID_CATEGORIES}
        category = max(filtered_scores, key=filtered_scores.get) if filtered_scores else "tech_industry"
        
        # 2. 实体提取：从文本中匹配已知实体
        entities = []
        for keyword, entity_name in self.ENTITY_MAP.items():
            if _kw_in_text(keyword) and entity_name not in entities:
                entities.append(entity_name)
        
        # 基于 @screen_name 自动映射实体
        if author.startswith("@"):
            author_key = author[1:].lower()
            if author_key in self.ENTITY_MAP:
                entity_name = self.ENTITY_MAP[author_key]
                if entity_name not in entities:
                    entities.append(entity_name)
        
        # 3. 标签：实体名的小写 + 板块名
        tags = []
        for e in entities:
            tag = e.lower().replace(" ", "_").replace("-", "_")
            if tag not in tags:
                tags.append(tag)
        if category not in tags:
            tags.append(category)
        
        return {
            "category": category,
            "tags": tags[:10],  # 最多 10 个标签
            "entities": entities[:8]  # 最多 8 个实体
        }


# ====================================================================
# 第一部分：信源适配器（Adapter）
# 每个适配器负责：调用工具 → 解析输出 → 返回 Atom 列表
# ====================================================================

class XTwitterAdapter:
    """
    X/Twitter 采集适配器
    
    工具：twitter-cli（安装在 ~/.local/bin/twitter）
    输出：YAML/JSON 格式的推文列表
    
    🚫 硬性规则：这是 L0 采集源，失败必须停止整个流程。
    """
    
    def __init__(self):
        self.annotator = RuleBasedAnnotator()
    
    # === 官方账号列表（trust_default = L1） ===
    OFFICIAL_ACCOUNTS = {
        "openai", "anthropicai", "googledeepmind", "googleai", "meta", "metaai",
        "nvidia", "xai", "microsoft", "microsoftai", "apple", "stability_ai",
        "huggingface", "deepseek_ai", "mistralai", "perplexity_ai",
        "midjourney", "runwayml", "cursor_ai", "github", "vercel", "cloudflare",
        "supabase", "google", "amazon", "aws", "azure"
    }
    
    # === CEO/CTO/研究员账号（trust_default = L1） ===
    CEO_CTO_ACCOUNTS = {
        "sama",          # Sam Altman - OpenAI
        "elonmusk",      # Elon Musk - xAI/Tesla
        "demishassabis", # Demis Hassabis - DeepMind
        "ylecun",        # Yann LeCun - Meta
        "karpathy",      # Andrej Karpathy
        "drjimfan",      # Jim Fan - NVIDIA
        "darioamodei",   # Dario Amodei - Anthropic
        "satyanadella",  # Satya Nadella - Microsoft
        "jasonwei20",    # Jason Wei - OpenAI
        "arthurmensch",  # Arthur Mensch - Mistral
        "clementdelangue",# Clément Delangue - HuggingFace
        "gdb",           # Greg Brockman - OpenAI
        "ilyasut",       # Ilya Sutskever
        "geoffreyhinton",# Geoffrey Hinton
        "fchollet",      # François Chollet
    }
    
    # === 权威 KOL/专家（trust_default = L1） ===
    EXPERT_KOL_ACCOUNTS = {
        # AI 研究员/专家
        "simonwillison",   # Simon Willison - AI 工具分析
        "emollick",        # Ethan Mollick - AI 教育
        "jeremyphoward",   # Jeremy Howard - Fast.ai
        "gwern",           # Gwern - AI 研究
        "hardmaru",        # David Ha - AI 研究
        "lilianweng",      # Lilian Weng - OpenAI
        "swyx",            # Shawn Wang - AI 工程
        "matthewberman",   # Matthew Berman - AI 评测
        "svpino",          # Santiago - AI 工程
        "bindureddy",      # Bindu Reddy
        "goodside",        # Riley Goodside - Prompt 专家
        "alexalbert__",    # Alex Albert - Anthropic
        "sh_reya",         # Shreya Shankar - AI 工程
        "rohanpaul_ai",    # Rohan Paul - AI 教程
        "omarsar0",        # Elvis Saravia - AI 研究
        "itsandrewgao",    # Andrew Gao
        "mreflow",         # Matt Mireles
        "benparr",         # Ben Parr
        "aidailybrief",    # AI Daily Brief
        "theomojica",      # Theo - AI 产品
        "kwindla",         # Kwindla Hultman Kramer
        
        # 芯片/硬件专家
        "dylan522p",       # Dylan Patel - SemiAnalysis
        "irismchu",        # Iris Hsu
        "danielnewmanuv",  # Daniel Newman
        "patrickmoorhead", # Patrick Moorhead
        
        # 开发者工具专家
        "levelsio",        # Pieter Levels
        "marc_louvion",    # Marc Lou
        "t3dotgg",         # Theo - t3.gg
        "leeerob",         # Lee Robinson - Vercel
        "rauchg",          # Guillermo Rauch - Vercel
        "addyosmani",      # Addy Osmani
        
        # 游戏行业
        "toddhoward",      # Todd Howard - Bethesda
        "tim_sweeney",     # Tim Sweeney - Epic
        "markcerny",       # Mark Cerny - PlayStation
        
        # 科技媒体/分析师
        "garrytan",        # Garry Tan - YC
        "paulg",           # Paul Graham
        "natfriedman",     # Nat Friedman
        "stratechery",     # Ben Thompson
        "martin_casado",   # Martin Casado
    }
    
    # === 媒体账号（trust_default = L2） ===
    MEDIA_ACCOUNTS = {
        "techcrunch", "theverge", "wired", "arstechnica", 
        "reuters", "bloomberg", "cnbc", "platformer",
    }
    
    def classify_author(self, screen_name: str) -> str:
        """
        根据 screen_name 判断 author_type。
        
        Returns:
            "official" | "ceo_cto" | "expert_kol" | "media" | "kol" | "community"
        """
        name_lower = screen_name.lower().lstrip("@")
        
        if name_lower in self.OFFICIAL_ACCOUNTS:
            return "official"
        elif name_lower in self.CEO_CTO_ACCOUNTS:
            return "ceo_cto"
        elif name_lower in self.EXPERT_KOL_ACCOUNTS:
            return "expert_kol"
        elif name_lower in self.MEDIA_ACCOUNTS:
            return "media"
        else:
            return "community"  # 不在列表中的为普通社区用户
    
    def get_trust_default(self, author_type: str) -> str:
        """
        根据 author_type 返回 trust_default。
        
        L1: 官方/CEO/专家 - 一手信源
        L2: 权威 KOL/媒体 - 专业分析
        L3: 普通用户 - 需要验证
        """
        trust_map = {
            "official": "L1",
            "ceo_cto": "L1", 
            "expert_kol": "L1",
            "media": "L2",
            "kol": "L2",
            "community": "L3"
        }
        return trust_map.get(author_type, "L3")
    
    def fetch_following_timeline(self, max_tweets: int = 200) -> List[Dict]:
        """
        获取 Following 时间线。
        
        命令：twitter feed -t following --max 50 --json
        
        Returns:
            原始推文列表（twitter-cli JSON 格式）
            
        Raises:
            RuntimeError: twitter-cli 失败（Cookie 过期等）→ 必须停止整个流程
        """
        env = os.environ.copy()
        env["PATH"] = PATH_ENV + ":" + env.get("PATH", "")
        
        try:
            result = subprocess.run(
                ["twitter", "feed", "-t", "following", "--max", str(max_tweets), "--json"],
                capture_output=True, text=True, timeout=120, env=env
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                # 只有明确显示 authenticated: false 才认为是认证失败
                # 警告信息中包含"cookie"但认证成功的情况不应阻断
                if "authenticated: false" in error_msg.lower():
                    raise RuntimeError(
                        f"🚫 L0 硬性阻断：twitter-cli 认证失败（Cookie 过期）。\n"
                        f"必须停止整个采集流程。请用户更新 Cookie。\n"
                        f"错误信息：{error_msg}"
                    )
                # 其他错误（包括cookie警告但认证成功的情况）继续尝试解析
                print(f"    ⚠️ twitter-cli 警告: {error_msg}", flush=True)
            
            # 解析 JSON 输出（即使returncode!=0，只要stdout有数据就尝试解析）
            output = result.stdout if result.stdout else "{}"
            tweets = json.loads(output)
            if isinstance(tweets, dict) and "data" in tweets:
                tweets = tweets["data"]
            
            return tweets if isinstance(tweets, list) else []
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("🚫 L0 硬性阻断：twitter-cli 超时。请检查网络连接。")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"twitter-cli 输出解析失败: {e}")
    
    def fetch_search(self, query: str, max_tweets: int = 20) -> List[Dict]:
        """
        搜索 X 推文。
        
        命令：twitter search "query" --max 20 --json
        """
        env = os.environ.copy()
        env["PATH"] = PATH_ENV + ":" + env.get("PATH", "")
        
        try:
            result = _retry_subprocess(
                ["twitter", "search", query, "--max", str(max_tweets), "--json"],
                max_retries=2, timeout=30, env=env
            )
            
            if result.returncode != 0:
                print(f"  ⚠️ X 搜索失败 '{query}': {result.stderr.strip()}")
                return []
            
            tweets = json.loads(result.stdout)
            if isinstance(tweets, dict) and "data" in tweets:
                tweets = tweets["data"]
            return tweets if isinstance(tweets, list) else []
            
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            print(f"  ⚠️ X 搜索异常 '{query}': {e}")
            return []
    
    def tweet_to_atom(self, tweet: Dict, date: str) -> Optional[Dict]:
        """
        将 twitter-cli 返回的推文转化为 Atom。
        
        twitter-cli 数据结构：
        - 纯转发 (RT): isRetweet=True, retweetedBy=转发者 → 跳过（由 extract_quoted_tweet 处理原帖）
        - Quote Tweet: quotedTweet 非空 → 保留引用者的评论文本
        - 普通推文: 正常处理
        
        Args:
            tweet: twitter-cli JSON 格式的单条推文
            date: 采集日期
            
        Returns:
            Atom 字典，或 None（如果推文不值得保存）
        """
        # 提取基本字段
        text = tweet.get("text", "")
        screen_name = tweet.get("author", {}).get("screenName", "unknown")
        tweet_id = tweet.get("id", "")
        created_at = tweet.get("createdAtLocal", "")
        
        # 跳过空内容
        if not text or len(text.strip()) < 10:
            return None
        
        # 纯转发 (RT)：跳过，原帖内容由 extract_quoted_tweet 处理
        # twitter-cli 中 RT 的 author 已经是原帖作者，retweetedBy 是转发者
        is_retweet = tweet.get("isRetweet", False)
        if is_retweet:
            return None
        
        # 判断作者类型
        author_type = self.classify_author(screen_name)
        
        # 构建 URL
        url = f"https://x.com/{screen_name}/status/{tweet_id}"
        
        # 互动数据
        metrics = {}
        if "metrics" in tweet:
            m = tweet["metrics"]
            metrics = {
                "likes": m.get("likes", 0),
                "retweets": m.get("retweets", 0),
                "replies": m.get("replies", 0),
                "views": m.get("views", 0),
            }
        
        # ========================================
        # 使用规则标注器判断 category/tags/entities
        # ========================================
        # 对于 Quote Tweet，将被引用推文的内容也纳入标注
        text_for_annotation = text
        quoted_tweet = tweet.get("quotedTweet")
        if quoted_tweet and isinstance(quoted_tweet, dict):
            qt_text = quoted_tweet.get("text", "")
            if qt_text:
                text_for_annotation = f"{text}\n{qt_text}"
        
        annotation = self.annotator.annotate(text_for_annotation, screen_name)
        
        category = annotation["category"]
        tags = annotation["tags"]
        entities = annotation["entities"]
        
        # 内容类型（粗判）
        content_type = self._guess_content_type(text, author_type)
        
        # 中文摘要
        summary_zh = text[:200]  # TODO: AI 翻译+摘要
        
        atom = create_atom(
            title=text[:100],  # 推文前 100 字符作为标题
            summary_zh=summary_zh,
            platform="x",
            author=f"@{screen_name}",
            author_type=author_type,
            url=url,
            content_type=content_type,
            category=category,
            tags=tags,
            entities=entities,
            date=date,
            title_zh=None,  # TODO: AI 翻译
            timestamp=created_at,
            metrics=metrics,
        )
        
        # 如果是 Quote Tweet，标记引用关系
        if quoted_tweet and isinstance(quoted_tweet, dict):
            qt_screen_name = quoted_tweet.get("author", {}).get("screenName", "unknown")
            qt_id = quoted_tweet.get("id", "")
            atom["quotes_tweet"] = f"https://x.com/{qt_screen_name}/status/{qt_id}" if qt_id else None
        
        # 提取推文内嵌链接（twitter-cli 已展开 t.co 短链）
        urls = tweet.get("urls", [])
        if urls and isinstance(urls, list):
            # 过滤掉 X 站内链接（只保留外部链接）
            external_urls = [u for u in urls if isinstance(u, str) and 
                           not u.startswith("https://x.com/") and 
                           not u.startswith("https://twitter.com/")]
            if external_urls:
                atom["embedded_urls"] = external_urls
                # 将第一个外部链接加入 entities
                if external_urls[0] not in entities:
                    entities.append(external_urls[0])
        
        return atom
    
    def extract_quoted_tweet(self, tweet: Dict, date: str) -> List[Dict]:
        """
        从转发/引用推文中提取原帖内容并转化为 Atom。
        
        twitter-cli 返回的数据结构：
        - 纯转发 (RT): isRetweet=True, retweetedBy=转发者, author=原帖作者, text=原帖内容
        - Quote Tweet: isRetweet=False, quotedTweet={id, text, author}, text=引用者评论
        - 普通推文: isRetweet=False, quotedTweet=None
        
        Args:
            tweet: twitter-cli JSON 格式的单条推文（可能是转发）
            date: 采集日期
            
        Returns:
            原帖的 Atom 列表（通常 0 或 1 条）
        """
        atoms = []
        
        # === 情况1: Quote Tweet — quotedTweet 字段 ===
        # twitter-cli 的字段名是 quotedTweet（不是 quotedStatus）
        quoted_tweet = tweet.get("quotedTweet")
        if quoted_tweet and isinstance(quoted_tweet, dict):
            qt_text = quoted_tweet.get("text", "")
            qt_author = quoted_tweet.get("author", {})
            qt_screen_name = qt_author.get("screenName", "unknown")
            qt_id = quoted_tweet.get("id", "")
            
            if qt_text and len(qt_text.strip()) >= 10:
                author_type = self.classify_author(qt_screen_name)
                annotation = self.annotator.annotate(qt_text, qt_screen_name)
                content_type = self._guess_content_type(qt_text, author_type)
                
                # 引用者信息
                quoter_screen_name = tweet.get("author", {}).get("screenName", "unknown")
                quoter_url = f"https://x.com/{quoter_screen_name}/status/{tweet.get('id', '')}"
                
                entities = annotation["entities"]
                
                atom = create_atom(
                    title=qt_text[:100],
                    summary_zh=qt_text[:200],
                    platform="x",
                    author=f"@{qt_screen_name}",
                    author_type=author_type,
                    url=f"https://x.com/{qt_screen_name}/status/{qt_id}" if qt_id else f"https://x.com/{qt_screen_name}",
                    content_type=content_type,
                    category=annotation["category"],
                    tags=annotation["tags"],
                    entities=entities,
                    date=date,
                )
                atom["is_quoted_tweet"] = True
                atom["quoted_by"] = [quoter_url]
                
                # 提取原帖中的链接（从 quoted_tweet 中获取）
                qt_urls = quoted_tweet.get("urls", [])
                if qt_urls and isinstance(qt_urls, list):
                    external_urls = [u for u in qt_urls if isinstance(u, str) and 
                                   not u.startswith("https://x.com/") and 
                                   not u.startswith("https://twitter.com/")]
                    if external_urls:
                        atom["embedded_urls"] = external_urls
                        if external_urls[0] not in entities:
                            entities.append(external_urls[0])
                
                atoms.append(atom)
            
            return atoms  # quotedTweet 已有完整数据，直接返回
        
        # === 情况2: 纯转发 (RT) — isRetweet + retweetedBy ===
        # twitter-cli 中纯 RT 的 author 已经是原帖作者，text 已经是原帖内容
        # retweetedBy 是转发者的 screenName
        is_retweet = tweet.get("isRetweet", False)
        retweeted_by = tweet.get("retweetedBy")
        
        if is_retweet and retweeted_by:
            # 原帖信息就在 tweet 本身
            text = tweet.get("text", "")
            screen_name = tweet.get("author", {}).get("screenName", "unknown")
            tweet_id = tweet.get("id", "")
            
            if text and len(text.strip()) >= 10:
                author_type = self.classify_author(screen_name)
                annotation = self.annotator.annotate(text, screen_name)
                content_type = self._guess_content_type(text, author_type)
                
                entities = annotation["entities"]
                
                atom = create_atom(
                    title=text[:100],
                    summary_zh=text[:200],
                    platform="x",
                    author=f"@{screen_name}",
                    author_type=author_type,
                    url=f"https://x.com/{screen_name}/status/{tweet_id}",
                    content_type=content_type,
                    category=annotation["category"],
                    tags=annotation["tags"],
                    entities=entities,
                    date=date,
                    timestamp=tweet.get("createdAtLocal", ""),
                    metrics={
                        "likes": tweet.get("metrics", {}).get("likes", 0),
                        "retweets": tweet.get("metrics", {}).get("retweets", 0),
                        "replies": tweet.get("metrics", {}).get("replies", 0),
                        "views": tweet.get("metrics", {}).get("views", 0),
                    },
                )
                atom["is_quoted_tweet"] = True
                atom["retweeted_by"] = f"@{retweeted_by}"
                
                # 提取原帖中的链接
                rt_urls = tweet.get("urls", [])
                if rt_urls and isinstance(rt_urls, list):
                    external_urls = [u for u in rt_urls if isinstance(u, str) and 
                                   not u.startswith("https://x.com/") and 
                                   not u.startswith("https://twitter.com/")]
                    if external_urls:
                        atom["embedded_urls"] = external_urls
                        if external_urls[0] not in entities:
                            entities.append(external_urls[0])
                
                atoms.append(atom)
        
        return atoms
    
    def _guess_content_type(self, text: str, author_type: str) -> str:
        """
        基于文本内容和作者类型粗判 content_type。
        
        优化：更好地识别专家/KOL 的高质量分析内容。
        """
        text_lower = text.lower()
        
        # 官方公告信号词
        if author_type in ["official", "ceo_cto"] and any(kw in text_lower for kw in 
            ["announcing", "introducing", "launching", "releasing", "we're", "today we", "we are", "new product", "available now"]):
            return "official"
        
        # 独家/实测信号词
        if any(kw in text_lower for kw in 
            ["exclusive", "first look", "hands-on", "我测了", "实测", "上手", "独家", "首发", "first impression", "review", "benchmark", "tested"]):
            return "firsthand_test"
        
        # 研究/技术分析信号词（专家/KOL 的高质量内容）
        research_signals = [
            "analysis", "deep dive", "technical", "architecture", "implementation",
            "paper", "research", "study", "benchmark", "evaluation",
            "how i built", "how to", "tutorial", "guide", "walkthrough",
            "lessons learned", "insights", "findings", "observations",
            "thread", "🧵", "1/", "2/", "3/",  # Twitter threads
            "my take", "i think", "in my opinion", "perspective", "viewpoint",
            "explained", "breakdown", "overview", "summary of", "key points",
            "comparison", "vs", "versus", "difference between", "pros and cons"
        ]
        if any(kw in text_lower for kw in research_signals):
            return "original_analysis"
        
        # 数据/报告信号词
        if any(kw in text_lower for kw in 
            ["data shows", "statistics", "survey", "poll", "report", "metrics", "numbers", "growth", "decline"]):
            return "report"
        
        # 转发/转载
        if text.startswith("RT ") or "转发" in text:
            return "repost"
        
        # 专家/KOL 的默认内容类型（不是普通 commentary）
        if author_type in ["expert_kol", "ceo_cto", "official"]:
            return "original_analysis"
        
        # 默认：评论
        return "commentary"


class WeiboAdapter:
    """
    微博采集适配器
    
    工具：weibo-cli（安装在 ~/.local/bin/weibo）+ weibo_fetch.py
    配置：config/weibo_users.yaml
    """
    
    def __init__(self):
        self.annotator = RuleBasedAnnotator()
        self.user_map = self._load_user_config()
    
    def _load_user_config(self) -> Dict[str, Dict]:
        """加载 weibo_users.yaml，构建 username→config 查找表"""
        import yaml
        config_file = CONFIG_DIR / "weibo_users.yaml"
        if not config_file.exists():
            return {}
        
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        user_map = {}
        for user in config.get("weibo_users", []):
            name = user.get("name", "").strip()
            tier = user.get("tier", "")
            category = user.get("category", "")
            
            # 根据 tier + category 推断 author_type
            if tier == "T1" or tier == "T2":
                author_type = "media"
            elif tier == "T3":
                if "爆料" in user.get("description", "") or "手机" in category:
                    author_type = "insider"
                else:
                    author_type = "kol"
            elif tier == "T4":
                author_type = "kol"
            else:
                author_type = "blogger"
            
            user_map[name.lower()] = {
                "author_type": author_type,
                "tier": tier,
                "category": category,
            }
        
        return user_map
    
    def fetch_all(self, max_per_user: int = 10) -> List[Dict]:
        """
        采集配置文件中所有博主的最新微博。
        
        命令：python3 scripts/weibo_fetch.py --max N --json
        
        Returns:
            原始微博列表
        """
        env = os.environ.copy()
        env["PATH"] = PATH_ENV + ":" + env.get("PATH", "")
        
        try:
            result = _retry_subprocess(
                ["python3", str(PROJECT_ROOT / "scripts" / "weibo_fetch.py"),
                 "--max", str(max_per_user), "--json"],
                max_retries=2, timeout=180, env=env,
                cwd=str(PROJECT_ROOT)
            )
            
            if result.returncode != 0:
                print(f"  ⚠️ 微博采集失败: {result.stderr.strip()[:200]}")
                return []
            
            # weibo_fetch.py 的 stdout 前面有进度文本，JSON 从第一个 '{' 开始
            stdout = result.stdout
            json_start = stdout.find('{')
            if json_start < 0:
                print(f"  ⚠️ 微博采集输出中无 JSON")
                return []
            
            data = json.loads(stdout[json_start:])
            
            # 输出格式: {users: [{username, weibos: [...]}, ...]}
            # 需要展开为扁平的微博列表
            all_weibos = []
            if isinstance(data, dict) and "users" in data:
                for user in data["users"]:
                    for weibo in user.get("weibos", []):
                        # 确保每条微博带上用户名信息
                        if "username" not in weibo:
                            weibo["username"] = user.get("username", "unknown")
                        all_weibos.append(weibo)
                return all_weibos
            elif isinstance(data, list):
                return data
            else:
                return []
            
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            print(f"  ⚠️ 微博采集异常: {e}")
            return []
    
    # 微博营销内容过滤关键词
    MARKETING_KEYWORDS = [
        "抽奖", "转发抽奖", "关注抽奖", "点赞抽奖",
        "福利", "免费送", "0元", "限时", "抢购",
        "优惠券", "折扣", "满减", "秒杀", "预售",
        "下单", "购买链接", "购物车", "种草", "安利",
        "品牌", "代言", " sponsor", "推广", "广告",
        "直播间", "直播带货", "下单立减",
    ]
    
    # 手机品牌营销特征词（用于降低优先级）
    PHONE_MARKETING_PATTERNS = [
        "颜值", "好看", "美", "时尚", "潮流", "设计",
        "手感", "轻薄", "配色", "外观", "颜值担当",
        "拍照好看", "自拍", "美颜", "滤镜",
        "明星", "代言人", "同款",
    ]
    
    def is_marketing_content(self, content: str, username: str) -> bool:
        """
        判断微博是否为营销内容。
        
        返回: True 如果是营销内容（应该被过滤）
        """
        content_lower = content.lower()
        
        # 1. 检查明显的营销关键词
        for kw in self.MARKETING_KEYWORDS:
            if kw in content:
                return True
        
        # 2. 检查手机品牌营销特征（结合用户名）
        # 数码闲聊站等爆料账号除外
        if username not in ["数码闲聊站", "熊猫很禿然", "智慧皮卡丘"]:
            marketing_score = sum(1 for p in self.PHONE_MARKETING_PATTERNS if p in content)
            if marketing_score >= 3:  # 命中3个以上营销特征词
                return True
        
        # 3. 检查纯表情/无实质内容
        if len(content.strip()) < 30 and ("http" in content or "【" in content):
            return True
        
        return False
    
    def weibo_to_atom(self, weibo: Dict, date: str) -> Optional[Dict]:
        """
        将微博数据转化为 Atom。
        
        新增：
        - 营销内容过滤
        - 时间过滤（只保留24小时内内容）
        """
        content = weibo.get("content_raw", weibo.get("text", ""))
        username = weibo.get("username", weibo.get("nickname", "unknown"))
        
        if not content or len(content.strip()) < 10:
            return None
        
        # 1. 营销内容过滤
        if self.is_marketing_content(content, username):
            return None  # 跳过营销内容
        
        # 2. 时间过滤 - 只保留24小时内的内容
        created_at = weibo.get("created_at", "")
        if created_at:
            try:
                from datetime import datetime, timedelta
                # 微博时间格式: "Mon Mar 23 08:30:00 +0800 2026"
                weibo_time = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
                now = datetime.now(weibo_time.tzinfo)
                if now - weibo_time > timedelta(hours=24):
                    return None  # 超过24小时，跳过
            except (ValueError, TypeError):
                # 时间解析失败，继续处理
                pass
        
        # 从配置判断作者类型
        user_config = self.user_map.get(username.lower().strip(), {})
        author_type = user_config.get("author_type", "blogger")
        
        # 使用规则标注器
        annotation = self.annotator.annotate(content, username)
        
        # 微博内容类型判断（简化版）
        content_type = "commentary"
        if "独家" in content or "首发" in content or "爆料" in content:
            content_type = "exclusive"
        elif "实测" in content or "上手" in content or "体验" in content:
            content_type = "firsthand_test"
        elif "转" in content[:10] or "转自" in content:
            content_type = "repost"
        
        # 构建微博帖子 URL（确保可回溯到具体帖子）
        weibo_url = weibo.get("url", "")
        if not weibo_url or weibo_url == "https://weibo.com/" or weibo_url.rstrip("/") == "https://weibo.com":
            uid = weibo.get("uid", "")
            # weibo-cli 搜索返回 "mid"，详情接口返回 "mblogid"
            mid = weibo.get("mid", "") or weibo.get("mblogid", "")
            weibo_id = weibo.get("id", "")
            # uid 为 0 时视为无效
            if uid in ("", "0", 0):
                uid = ""
            if uid and mid:
                weibo_url = f"https://weibo.com/{uid}/{mid}"
            elif mid:
                weibo_url = f"https://m.weibo.cn/detail/{mid}"
            elif uid and weibo_id:
                weibo_url = f"https://weibo.com/{uid}/{weibo_id}"
            elif weibo_id:
                weibo_url = f"https://m.weibo.cn/detail/{weibo_id}"
            else:
                weibo_url = "https://weibo.com/"
        
        # 提取微博中的链接（http://t.cn/ 短链）
        import re
        urls_found = re.findall(r'http[s]?://t\.cn/\w+', content)
        
        entities = annotation["entities"]
        
        atom = create_atom(
            title=content[:100],
            summary_zh=content[:200],
            platform="weibo",
            author=username,
            author_type=author_type,
            url=weibo_url,
            content_type=content_type,
            category=annotation["category"],
            tags=annotation["tags"],
            entities=entities,
            date=date,
            metrics={
                "likes": weibo.get("attitudes_count", 0),
                "retweets": weibo.get("reposts_count", 0),
                "replies": weibo.get("comments_count", 0),
            }
        )
        
        # 保存提取的链接
        if urls_found:
            atom["embedded_urls"] = urls_found
            # 将链接加入 entities
            for url in urls_found:
                if url not in entities:
                    entities.append(url)
        
        # 标记转发微博（weibo-cli 没有 retweeted_status 字段，只能通过文本特征判断）
        if "//" in content and "@" in content:
            atom["is_repost"] = True
            # 尝试提取原帖作者
            repost_match = re.search(r'//@(\w+)', content)
            if repost_match:
                atom["reposted_from"] = repost_match.group(1)
        
        return atom


class RSSAdapter:
    """
    RSS 采集适配器
    
    使用 feedparser 抓取 RSS feeds。
    信源列表从 config/sources.json 加载。
    """
    
    # 权威英文媒体（trust_default = L2）
    L2_DOMAINS = {
        "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
        "reuters.com", "bloomberg.com", "cnbc.com", "mit.edu",
        "technologyreview.com", "venturebeat.com", "engadget.com",
    }
    
    # 中文媒体（trust_default = L2）
    L2_CN_DOMAINS = {
        "36kr.com", "huxiu.com", "ifanr.com", "tmtpost.com",
        "jiqizhixin.com", "quantamagazine.org", "syncedreview.com",
    }
    
    def __init__(self):
        self.annotator = RuleBasedAnnotator()
    
    def fetch_feed(self, url: str, max_items: int = 20, timeout: int = 15) -> List[Dict]:
        """
        抓取单个 RSS feed（带线程超时保护）。
        
        Args:
            url: RSS feed URL
            max_items: 每个 feed 最多抓取条数
            timeout: 单个 feed 超时秒数
            
        Returns:
            [{"title": ..., "url": ..., "summary": ..., "published": ...}, ...]
        """
        try:
            import feedparser
            import ssl
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
            
            if hasattr(ssl, '_create_unverified_context'):
                ssl._create_default_https_context = ssl._create_unverified_context
            
        except ImportError:
            print("  ⚠️ feedparser 未安装，跳过 RSS 抓取", flush=True)
            return []
        
        def _do_parse():
            return feedparser.parse(url)
        
        try:
            # 线程超时：feedparser 底层 C 调用不响应 signal，只能用线程
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_do_parse)
                feed = future.result(timeout=timeout)
            
            if feed.bozo and feed.bozo_exception:
                print(f"  ⚠️ RSS 解析警告 {url}: {feed.bozo_exception}", flush=True)
            
            items = []
            for entry in feed.entries[:max_items]:
                item = {
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "summary": entry.get("summary", entry.get("description", ""))[:500],
                    "published": entry.get("published", entry.get("updated", "")),
                    "source_url": url,
                }
                if item["title"] and item["url"]:
                    items.append(item)
            
            return items
            
        except FuturesTimeout:
            print(f"  ⏱️ RSS 超时跳过 ({timeout}s): {url[:60]}", flush=True)
            return []
        except Exception as e:
            print(f"  ⚠️ RSS 抓取失败 {url[:60]}: {e}", flush=True)
            return []
    
    def rss_item_to_atom(self, item: Dict, source_name: str, source_domain: str, date: str) -> Optional[Dict]:
        """
        将 RSS item 转化为 Atom。
        
        Args:
            item: RSS 条目（来自 fetch_feed）
            source_name: 信源名称（如 "TechCrunch"）
            source_domain: 域名（如 "techcrunch.com"）
            date: 采集日期
            
        Returns:
            Atom 字典，或 None
        """
        title = item.get("title", "")
        url = item.get("url", "")
        summary = item.get("summary", "")
        
        if not title or not url:
            return None
        
        # 判断作者类型（媒体 → L2）
        author_type = "media"
        
        # 判断 trust_default
        if source_domain in self.L2_DOMAINS or source_domain in self.L2_CN_DOMAINS:
            trust_default = "L2"
        else:
            trust_default = "L3"
        
        # 使用规则标注器
        text_for_annotation = f"{title} {summary}"
        annotation = self.annotator.annotate(text_for_annotation, source_name)
        
        # 内容类型判断
        content_type = "report"  # RSS 默认为报道
        title_lower = title.lower()
        if any(kw in title_lower for kw in ["exclusive", "独家", "爆料"]):
            content_type = "exclusive"
        elif any(kw in title_lower for kw in ["hands-on", "review", "评测", "上手", "实测"]):
            content_type = "firsthand_test"
        elif any(kw in title_lower for kw in ["opinion", "editorial", "观点", "评论"]):
            content_type = "commentary"
        
        atom = create_atom(
            title=title,
            summary_zh=summary[:200] if summary else title,  # 中文摘要需要 AI 翻译，这里先用原文
            platform="rss",
            author=source_name,
            author_type=author_type,
            url=url,
            content_type=content_type,
            category=annotation["category"],
            tags=annotation["tags"],
            entities=annotation["entities"],
            date=date,
            timestamp=item.get("published"),
        )
        
        # 覆盖 trust_default（RSS 的 trust_default 应该基于信源权威性而非作者类型）
        atom["trust_default"] = trust_default
        
        return atom
    
    def _parse_pub_date(self, pub_date: str, fallback: str) -> str:
        """解析 RSS 发布时间，支持 RFC 2822 和 ISO 8601"""
        if not pub_date:
            return fallback
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub_date)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            try:
                # ISO 8601 fallback
                dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                return fallback

    def fetch_all_feeds(self, feed_urls: List[Dict], max_per_feed: int = 10, collection_date: Optional[str] = None) -> List[Dict]:
        """
        批量抓取多个 RSS feeds（并行，8 线程）。
        
        Args:
            feed_urls: [{"url": "...", "name": "...", "domain": "..."}, ...]
            max_per_feed: 每个 feed 最多条数
            collection_date: 采集日期（用于分渠道存储），默认今天
            
        Returns:
            所有 Atom 列表
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        all_atoms = []
        today = collection_date or datetime.now().strftime("%Y-%m-%d")
        
        def _fetch_one(feed_info):
            url = feed_info.get("url", "")
            name = feed_info.get("name", "Unknown")
            domain = feed_info.get("domain", "")
            
            items = self.fetch_feed(url, max_items=max_per_feed)
            
            atoms = []
            for item in items:
                # 使用采集日期作为 atom date（用于分渠道存储）
                # 原始发布日期会保存在 timestamp 字段
                atom = self.rss_item_to_atom(item, name, domain, today)
                if atom:
                    atoms.append(atom)
            return name, atoms
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(_fetch_one, fi): fi for fi in feed_urls}
            for future in as_completed(futures):
                try:
                    name, atoms = future.result()
                    print(f"  ✅ {name}: {len(atoms)} 条", flush=True)
                    all_atoms.extend(atoms)
                except Exception as e:
                    fi = futures[future]
                    print(f"  ⚠️ {fi.get('name', '?')} 失败: {e}", flush=True)
        
        return all_atoms
    
    # rsshub.app 公共实例经常不可用（SSL 错误/限流），需要跳过
    RSSHUB_DOMAINS = ["rsshub.app", "rsshub.rssforever.com"]
    
    def load_feeds_from_config(self, skip_rsshub: bool = True) -> List[Dict]:
        """
        从 config/sources.json 加载 RSS feed 列表。
        
        只读，不修改原文件。
        
        Args:
            skip_rsshub: 是否跳过 rsshub 代理 feeds（默认 True，因为公共实例不可靠）
            
        Returns:
            [{"url": "...", "name": "...", "domain": "..."}, ...]
        """
        feeds = []
        skipped_rsshub = 0
        sources_file = CONFIG_DIR / "sources.json"
        
        if not sources_file.exists():
            print(f"  ⚠️ sources.json 不存在: {sources_file}")
            return feeds
        
        try:
            with open(sources_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 遍历所有 tier，提取 feeds
            for tier_key, tier_data in data.items():
                if tier_key.startswith("_"):
                    continue  # 跳过元数据字段
                
                if not isinstance(tier_data, dict):
                    continue
                
                sources = tier_data.get("sources", [])
                for source in sources:
                    if not isinstance(source, dict):
                        continue
                    
                    source_name = source.get("name_zh") or source.get("name_en") or source.get("entity", "Unknown")
                    
                    for feed in source.get("feeds", []):
                        if feed.get("type") == "rss" and feed.get("url"):
                            feed_url = feed["url"]
                            
                            # 跳过 rsshub 代理 feeds
                            if skip_rsshub and any(d in feed_url for d in self.RSSHUB_DOMAINS):
                                skipped_rsshub += 1
                                continue
                            
                            domain = self._extract_domain(feed_url)
                            
                            feeds.append({
                                "url": feed_url,
                                "name": feed.get("handle") or source_name,
                                "domain": domain,
                                "source": source_name,
                            })
            
            if skipped_rsshub > 0:
                print(f"  ℹ️ 跳过 {skipped_rsshub} 个 rsshub 代理 feeds（公共实例不可靠）", flush=True)
            
            return feeds
            
        except Exception as e:
            print(f"  ⚠️ 加载 sources.json 失败: {e}")
            return feeds
    
    def _extract_domain(self, url: str) -> str:
        """从 URL 提取域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return ""


class WebAdapter:
    """
    网页采集适配器
    
    工具优先级：Jina Reader → tavily_extract → web_fetch
    用于抓取 36氪/虎嗅/科创板日报等聚合站。
    """
    
    def __init__(self):
        self.annotator = RuleBasedAnnotator()
    
    def fetch_url(self, url: str, timeout: int = 30) -> Optional[str]:
        """
        抓取网页内容。
        
        优先级：
        1. Jina Reader: curl -s "https://r.jina.ai/URL"
        2. 回退到 web_fetch（CodeBuddy 内置工具，但这里是脚本环境）
        
        Args:
            url: 网页 URL
            timeout: 超时秒数
            
        Returns:
            Markdown 格式的网页内容，失败返回 None
        """
        
        # 方案 1: Jina Reader（首选）
        jina_url = f"https://r.jina.ai/{url}"
        try:
            result = _retry_subprocess(
                ["curl", "-s", "-L", "--max-time", str(timeout), jina_url],
                max_retries=2, timeout=timeout + 5
            )
            
            if result.returncode == 0 and len(result.stdout) > 100:
                # Jina Reader 成功返回 Markdown
                return result.stdout
                
        except subprocess.TimeoutExpired:
            print(f"  ⚠️ Jina Reader 超时: {url}")
        except Exception as e:
            print(f"  ⚠️ Jina Reader 失败: {e}")
        
        # 方案 2: 直接 curl 抓取 HTML（简单处理）
        try:
            result = _retry_subprocess(
                ["curl", "-s", "-L", "--max-time", str(timeout), url],
                max_retries=1, timeout=timeout + 5
            )
            
            if result.returncode == 0 and len(result.stdout) > 100:
                # 简单清理 HTML 标签（粗略处理）
                import re
                text = result.stdout
                # 移除 script/style 标签及内容
                text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL|re.IGNORECASE)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL|re.IGNORECASE)
                # 移除 HTML 标签
                text = re.sub(r'<[^>]+>', ' ', text)
                # 清理多余空白
                text = re.sub(r'\s+', ' ', text).strip()
                
                if len(text) > 100:
                    return text
                    
        except subprocess.TimeoutExpired:
            print(f"  ⚠️ curl 超时: {url}")
        except Exception as e:
            print(f"  ⚠️ curl 失败: {e}")
        
        return None
    
    def web_item_to_atom(self, title: str, url: str, content: str, source: str, date: str,
                         source_domain: str = "") -> Optional[Dict]:
        """
        将网页新闻转化为 Atom。
        
        Args:
            title: 文章标题
            url: 文章 URL
            content: 文章内容（Markdown 或纯文本）
            source: 来源名称（如 "36氪"、"虎嗅"）
            date: 采集日期
            source_domain: 来源域名
            
        Returns:
            Atom 字典，或 None
        """
        if not title or not url:
            return None
        
        # 判断作者类型
        author_type = "media"
        
        # 判断 trust_default（基于域名）
        L2_CN_DOMAINS = {"36kr.com", "huxiu.com", "ifanr.com", "tmtpost.com", 
                        "jiqizhixin.com", "geekpark.net", "ithome.com"}
        trust_default = "L2" if source_domain in L2_CN_DOMAINS else "L3"
        
        # 使用规则标注器
        text_for_annotation = f"{title} {content[:500]}"
        annotation = self.annotator.annotate(text_for_annotation, source)
        
        # 内容类型判断
        content_type = "report"
        title_lower = title.lower()
        if any(kw in title_lower for kw in ["独家", "爆料", "首发"]):
            content_type = "exclusive"
        elif any(kw in title_lower for kw in ["评测", "上手", "实测", "体验"]):
            content_type = "firsthand_test"
        elif any(kw in title_lower for kw in ["观点", "评论", "深度"]):
            content_type = "commentary"
        
        # 摘要：取内容前 200 字
        summary = content[:200] if content else title
        
        atom = create_atom(
            title=title,
            summary_zh=summary,
            platform="web",
            author=source,
            author_type=author_type,
            url=url,
            content_type=content_type,
            category=annotation["category"],
            tags=annotation["tags"],
            entities=annotation["entities"],
            date=date,
        )
        
        # 覆盖 trust_default
        atom["trust_default"] = trust_default
        
        return atom
    
    def fetch_from_sources(self, sources: List[Dict], max_per_source: int = 5) -> List[Dict]:
        """
        从多个网站首页抓取新闻链接。
        
        Args:
            sources: [{"url": "...", "name": "..."}, ...]
            max_per_source: 每个来源最多条数
            
        Returns:
            Atom 列表
            
        注意：这个方法比较粗糙，理想情况下应该用 RSS 或 API。
        """
        all_atoms = []
        date = datetime.now().strftime("%Y-%m-%d")
        
        for source in sources[:5]:  # 限制来源数量
            url = source.get("url", "")
            name = source.get("name", "Unknown")
            domain = self._extract_domain(url)
            
            print(f"  抓取网页: {name}")
            content = self.fetch_url(url)
            
            if not content:
                continue
            
            # 尝试从内容中提取新闻标题
            import re
            
            titles_found = []
            
            # Jina Reader 返回的是 Markdown，提取 ## 或 ### 标题
            md_titles = re.findall(r'^#{1,3}\s+(.{10,100})$', content, re.MULTILINE)
            titles_found.extend(md_titles)
            
            # Markdown 链接文本 [标题](url)
            md_links = re.findall(r'\[([^\[\]]{10,100})\]\(https?://[^)]+\)', content)
            titles_found.extend(md_links)
            
            # HTML 格式兜底（如果 Jina 失败走 curl 回退）
            html_titles = re.findall(r'<h[1-3][^>]*>([^<]{10,100})</h[1-3]>', content, re.IGNORECASE)
            titles_found.extend(html_titles)
            
            # 去重并取前 N 个
            seen = set()
            count = 0
            for title in titles_found:
                title = title.strip()
                if len(title) > 10 and title not in seen and count < max_per_source:
                    seen.add(title)
                    count += 1
                    
                    # 构建 Atom（URL 用首页 URL，因为没有具体文章链接）
                    atom = self.web_item_to_atom(
                        title=title,
                        url=url,
                        content=content,
                        source=name,
                        date=date,
                        source_domain=domain
                    )
                    if atom:
                        all_atoms.append(atom)
        
        return all_atoms
    
    def _extract_domain(self, url: str) -> str:
        """从 URL 提取域名"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return ""


# ====================================================================
# 第二部分：采集编排器（Orchestrator）
# 按 L0→L0.5→L1 顺序执行采集，汇总所有 Atoms
# ====================================================================

class CollectorOrchestrator:
    """
    采集编排器 — 按优先级依次调用各适配器。
    
    🚫 硬性规则：
    1. L0 (X/Twitter) 必须最先执行，失败则停止整个流程
    2. 所有采集到的数据都必须转化为 Atom 并存储
    3. 采集后自动触发 Obsidian 同步
    """
    
    def __init__(self):
        self.store = AtomStore()
        self.x_adapter = XTwitterAdapter()
        self.weibo_adapter = WeiboAdapter()
        self.rss_adapter = RSSAdapter()
        self.web_adapter = WebAdapter()
        self.date = datetime.now().strftime("%Y-%m-%d")
        
        # 统计
        self.stats = {
            "x_following": 0,
            "x_search": 0,
            "weibo": 0,
            "rss": 0,
            "total_raw": 0,
            "total_atoms": 0,
        }
    
    def run_full_collection(self) -> List[Dict]:
        """
        执行完整采集流程。
        
        顺序：L0 (X Following) → L0.5 (微博) → L1 (X 关键词搜索 + RSS)
        每个渠道独立存储到各自的 JSONL 文件（如 2026-03-19_x.jsonl）。
        
        Returns:
            所有采集到的 Atom 列表
            
        Raises:
            RuntimeError: L0 失败（必须停止）
        """
        all_atoms = []
        
        # ====== L0: X/Twitter Following（硬性阻断点）======
        print("=" * 60)
        print("🚫 L0: X/Twitter Following 采集（硬性阻断点）")
        print("=" * 60)
        
        x_atoms = []
        try:
            tweets = self.x_adapter.fetch_following_timeline(max_tweets=200)
            print(f"  ✅ 获取 {len(tweets)} 条推文")
            self.stats["x_following"] = len(tweets)
            
            for tweet in tweets:
                # 1. 先尝试提取原帖（如果是转发/引用）
                quoted_atoms = self.x_adapter.extract_quoted_tweet(tweet, self.date)
                if quoted_atoms:
                    x_atoms.extend(quoted_atoms)
                
                # 2. 再处理推文本身
                atom = self.x_adapter.tweet_to_atom(tweet, self.date)
                if atom:
                    x_atoms.append(atom)
                    
        except RuntimeError as e:
            # L0 失败 → 整个流程停止
            print(f"\n{'='*60}")
            print(f"🚫🚫🚫 L0 采集失败，整个流程终止 🚫🚫🚫")
            print(f"{'='*60}")
            print(f"原因：{e}")
            print(f"\n请修复后重新运行。")
            raise
        
        # ====== L0.5: 微博采集 ======
        print(f"\n{'='*60}")
        print("📡 L0.5: 微博采集")
        print("=" * 60)
        
        weibo_atoms = []
        weibos = self.weibo_adapter.fetch_all(max_per_user=10)
        print(f"  获取 {len(weibos)} 条微博")
        self.stats["weibo"] = len(weibos)
        
        for weibo in weibos:
            atom = self.weibo_adapter.weibo_to_atom(weibo, self.date)
            if atom:
                weibo_atoms.append(atom)
        
        # ====== L1: 聚合搜索 ======
        print(f"\n{'='*60}")
        print("🔍 L1: 聚合搜索（X 关键词 + RSS）")
        print("=" * 60)
        
        # L1.1: 关键词搜索（X 搜索）
        keywords = self._load_search_keywords()
        x_search_failed = 0
        x_search_total = 0
        
        for section, kw_list in keywords.items():
            for kw in kw_list[:2]:  # 每板块最多搜 2 个关键词
                x_search_total += 1
                print(f"  搜索 X: '{kw}' ({section})")
                tweets = self.x_adapter.fetch_search(kw, max_tweets=10)
                
                if tweets:
                    self.stats["x_search"] += len(tweets)
                    for tweet in tweets:
                        # 先提取 RT/Quote Tweet 原帖
                        quoted_atoms = self.x_adapter.extract_quoted_tweet(tweet, self.date)
                        if quoted_atoms:
                            x_atoms.extend(quoted_atoms)
                        # 再处理推文本身
                        atom = self.x_adapter.tweet_to_atom(tweet, self.date)
                        if atom:
                            x_atoms.append(atom)
                else:
                    x_search_failed += 1
        
        # L1.2: RSS 采集
        print(f"\n  {'─'*50}")
        print("  📰 L1.2: RSS 采集")
        print(f"  {'─'*50}")
        
        rss_atoms = []
        rss_feeds = self.rss_adapter.load_feeds_from_config()
        if rss_feeds:
            feeds_to_fetch = rss_feeds[:50]  # 最多 50 个直连 feeds
            print(f"  加载 {len(feeds_to_fetch)} 个直连 RSS feeds（共 {len(rss_feeds)} 个配置）")
            
            rss_atoms = self.rss_adapter.fetch_all_feeds(feeds_to_fetch, max_per_feed=5, collection_date=self.date)
            print(f"  获取 {len(rss_atoms)} 条 RSS 条目")
            self.stats["rss"] = len(rss_atoms)
        else:
            print("  ⚠️ 未找到 RSS feed 配置")
        
        # ====== 按渠道分别存储 ======
        print(f"\n{'='*60}")
        print("💾 按渠道存储 Atoms")
        print("=" * 60)
        
        self.stats["total_raw"] = (self.stats["x_following"] + self.stats["x_search"] +
                                    self.stats["weibo"] + self.stats["rss"])
        
        # X 渠道（following + search 合并）
        if x_atoms:
            x_ids = self.store.save_atoms_batch(x_atoms, channel="x")
            print(f"  📱 X:      {len(x_ids):4d} 条 → {self.date}/x.jsonl")
        else:
            print(f"  📱 X:         0 条")
        
        # 微博渠道
        if weibo_atoms:
            weibo_ids = self.store.save_atoms_batch(weibo_atoms, channel="weibo")
            print(f"  📡 微博:   {len(weibo_ids):4d} 条 → {self.date}/weibo.jsonl")
        else:
            print(f"  📡 微博:      0 条")
        
        # RSS 渠道
        if rss_atoms:
            rss_ids = self.store.save_atoms_batch(rss_atoms, channel="rss")
            print(f"  📰 RSS:    {len(rss_ids):4d} 条 → {self.date}/rss.jsonl")
        else:
            print(f"  📰 RSS:       0 条")
        
        # 汇总
        all_atoms = x_atoms + weibo_atoms + rss_atoms
        self.stats["total_atoms"] = len(all_atoms)
        
        print(f"\n  原始数据: {self.stats['total_raw']} 条")
        print(f"  转化 Atoms: {self.stats['total_atoms']} 条")
        
        # ====== 渠道状态总览 ======
        channel_status = self.store.get_daily_stats(self.date)
        print(f"\n📊 今日渠道状态:")
        for ch, info in channel_status["channels"].items():
            icon = "✅" if info["exists"] and info["count"] > 0 else "❌"
            cats = ", ".join(f"{k}:{v}" for k, v in sorted(info["categories"].items(), key=lambda x: -x[1])[:3])
            print(f"  {icon} {ch:8s} │ {info['count']:4d} 条 │ {cats}")
        print(f"  {'─'*50}")
        print(f"  合计: {channel_status['total']} 条")
        
        # ====== 生成渠道 Markdown 选题 ======
        print(f"\n{'='*60}")
        print("📝 生成渠道 Markdown 选题")
        print("=" * 60)
        self._generate_channel_markdowns()
        
        return all_atoms
    
    def _generate_channel_markdowns(self):
        """为每个渠道生成 Markdown 选题文件"""
        from datetime import datetime
        
        CATEGORY_NAMES = {
            "ai_models": "🤖 AI 模型与产品",
            "mobile": "📱 手机与消费电子", 
            "chips": "🔧 芯片与算力",
            "gaming": "🎮 游戏行业",
            "tech_industry": "🏢 科技行业动态",
            "policy": "📜 政策与监管",
            "other": "📋 其他",
        }
        
        TRUST_ICONS = {"L1": "🟢", "L2": "🟡", "L3": "🟠"}
        CONTENT_TYPE_LABELS = {
            "official": "官方", "exclusive": "独家", "firsthand_test": "实测",
            "original_analysis": "原创分析", "report": "报道", "commentary": "评论",
        }
        
        docs_dir = V2_ROOT / "docs" / self.date
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        for channel in ["x", "weibo", "rss"]:
            atoms = self.store.query_by_date_channel(self.date, channel)
            if not atoms:
                continue
            
            # 按分类分组
            by_category = {}
            for atom in atoms:
                cat = atom.get("category", "other")
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(atom)
            
            # 生成 Markdown
            lines = [
                f"# {channel.upper()} 渠道选题 - {self.date}",
                "",
                f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"总条目: {len(atoms)} 条",
                "",
                "---",
                "",
            ]
            
            # 按6大模块顺序输出
            for cat_key in ["ai_models", "mobile", "chips", "gaming", "tech_industry", "policy", "other"]:
                if cat_key not in by_category:
                    continue
                
                cat_name = CATEGORY_NAMES.get(cat_key, cat_key)
                lines.append(f"## {cat_name}")
                lines.append("")
                
                # 按 trust 排序（L1优先）
                cat_atoms = sorted(by_category[cat_key], 
                                   key=lambda a: {"L1": 0, "L2": 1, "L3": 2}.get(a.get("trust_default", "L3"), 2))
                
                for atom in cat_atoms:
                    trust = atom.get("trust_default", "L3")
                    trust_icon = TRUST_ICONS.get(trust, "⚪")
                    author = atom.get("source", {}).get("author", "未知")
                    author_type = atom.get("source", {}).get("author_type", "")
                    content_type = atom.get("content_type", "")
                    ct_label = CONTENT_TYPE_LABELS.get(content_type, content_type)
                    title = atom.get("title_zh") or atom.get("title", "")
                    url = atom.get("source", {}).get("url", "")
                    summary = atom.get("summary_zh", "")[:100]
                    
                    lines.append(f"### {trust_icon} {title}")
                    lines.append(f"- **作者**: {author} (`{author_type}`)")
                    lines.append(f"- **类型**: {ct_label} | **置信度**: {trust}")
                    lines.append(f"- **链接**: {url}")
                    if summary:
                        lines.append(f"- **摘要**: {summary}...")
                    lines.append("")
            
            # 写入文件
            md_path = docs_dir / f"{channel}.md"
            md_path.write_text("\n".join(lines), encoding="utf-8")
            print(f"  ✅ {channel}.md: {len(atoms)} 条")
        
        print(f"\n  📁 选题文件位置: v2/docs/{self.date}/")
    
    def _load_search_keywords(self) -> Dict[str, List[str]]:
        """
        加载搜索关键词（从 config/search_keywords.yaml）。
        
        只加载英文关键词用于 X 搜索。
        """
        import yaml
        
        keywords_file = CONFIG_DIR / "search_keywords.yaml"
        if not keywords_file.exists():
            print(f"  ⚠️ 关键词配置不存在: {keywords_file}")
            return {}
        
        with open(keywords_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        # 提取英文关键词
        result = {}
        for section, data in config.items():
            if isinstance(data, dict) and "en" in data:
                result[section] = data["en"]
        
        return result
    
    def _tavily_search_fallback(self, keywords: Dict[str, List[str]]) -> List[Dict]:
        """
        Tavily 搜索 fallback —— 当 X 搜索全部失败时使用。
        
        通过 tavily-mcp 工具搜索科技新闻，转化为 Atom。
        """
        TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
        if not TAVILY_API_KEY:
            print("  ⚠️ TAVILY_API_KEY 未设置，跳过 Tavily 搜索")
            return []
        
        all_atoms = []
        env = os.environ.copy()
        env["TAVILY_API_KEY"] = TAVILY_API_KEY
        env["PATH"] = PATH_ENV + ":" + env.get("PATH", "")
        
        # 只搜核心关键词，避免太多请求
        search_queries = []
        for section, kw_list in keywords.items():
            if kw_list:
                search_queries.append({
                    "query": f"{kw_list[0]} latest news today",
                    "section": section,
                })
        
        # 最多 5 次搜索
        for sq in search_queries[:5]:
            query = sq["query"]
            section = sq["section"]
            print(f"  🔍 Tavily 搜索: '{query}' ({section})", flush=True)
            
            try:
                # 构建 JSON-RPC 请求
                jsonrpc_init = json.dumps({
                    "jsonrpc": "2.0", "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "collector", "version": "1.0"}
                    }
                })
                jsonrpc_search = json.dumps({
                    "jsonrpc": "2.0", "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "tavily_search",
                        "arguments": {
                            "query": query,
                            "max_results": 5,
                            "search_depth": "basic",
                            "topic": "news",
                        }
                    }
                })
                
                payload = jsonrpc_init + "\n" + jsonrpc_search + "\n"
                
                result = subprocess.run(
                    ["npx", "-y", "tavily-mcp@latest"],
                    input=payload, capture_output=True, text=True,
                    timeout=30, env=env
                )
                
                if result.returncode != 0:
                    print(f"    ⚠️ Tavily 搜索失败: {result.stderr[:100]}", flush=True)
                    continue
                
                # 解析 JSON-RPC 响应
                atoms_from_query = self._parse_tavily_response(result.stdout, section)
                all_atoms.extend(atoms_from_query)
                print(f"    → {len(atoms_from_query)} 条结果", flush=True)
                
            except subprocess.TimeoutExpired:
                print(f"    ⏱️ Tavily 搜索超时", flush=True)
            except Exception as e:
                print(f"    ⚠️ Tavily 异常: {e}", flush=True)
        
        return all_atoms
    
    def _parse_tavily_response(self, stdout: str, section: str) -> List[Dict]:
        """
        解析 Tavily MCP 的 JSON-RPC 响应。
        
        Tavily 返回两种格式：
        1. 纯文本格式："Detailed Results:\n\nTitle: ...\nURL: ...\nContent: ..."
        2. JSON 格式：[{"title": ..., "url": ..., "content": ...}]
        """
        import re
        atoms = []
        annotator = RuleBasedAnnotator()
        
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                resp = json.loads(line)
                content = resp.get("result", {}).get("content", [])
                if not content:
                    continue
                
                for item in content:
                    text = item.get("text", "")
                    if not text:
                        continue
                    
                    search_results = []
                    
                    # 尝试 JSON 解析
                    try:
                        parsed = json.loads(text)
                        if isinstance(parsed, list):
                            search_results = parsed
                        elif isinstance(parsed, dict):
                            search_results = parsed.get("results", [])
                    except json.JSONDecodeError:
                        pass
                    
                    # 如果 JSON 解析失败，用文本正则解析
                    # 格式：Title: ...\nURL: ...\nContent: ...
                    if not search_results and "Title:" in text:
                        # 按 "Title:" 分割各条结果
                        blocks = re.split(r'\n\s*Title:\s*', text)
                        for block in blocks:
                            block = block.strip()
                            if not block:
                                continue
                            # 如果首块包含前缀文字（如 "Detailed Results:"），跳过
                            if not re.search(r'URL:', block):
                                continue
                            
                            # 提取字段
                            title_match = re.match(r'^(.+?)(?:\nURL:)', block)
                            url_match = re.search(r'URL:\s*(\S+)', block)
                            content_match = re.search(r'Content:\s*(.+?)(?:\n\n|$)', block, re.DOTALL)
                            
                            if title_match and url_match:
                                search_results.append({
                                    "title": title_match.group(1).strip(),
                                    "url": url_match.group(1).strip(),
                                    "content": content_match.group(1).strip() if content_match else "",
                                })
                    
                    # 转化为 Atoms
                    for r in search_results:
                        title = r.get("title", "")
                        url = r.get("url", "")
                        snippet = r.get("content", r.get("snippet", ""))
                        
                        if not title or not url:
                            continue
                        
                        annotation = annotator.annotate(f"{title} {snippet}")
                        
                        atom = create_atom(
                            title=title,
                            summary_zh=snippet[:200] if snippet else title,
                            platform="web",
                            author="Tavily Search",
                            author_type="media",
                            url=url,
                            content_type="report",
                            category=annotation["category"],
                            tags=annotation["tags"],
                            entities=annotation["entities"],
                            date=self.date,
                        )
                        atoms.append(atom)
                        
            except json.JSONDecodeError:
                continue
        
        return atoms


# ====================================================================
# 第三部分：CLI 入口
# ====================================================================

def main():
    import argparse
    import functools
    
    # 全局禁用 stdout 缓冲（确保 print 立即输出，避免 IDE 终端 idle timeout）
    sys.stdout.reconfigure(line_buffering=True)
    
    parser = argparse.ArgumentParser(description="Tech Daily Brief v2 — 统一采集入口")
    parser.add_argument("--source", choices=["x", "weibo", "rss", "all"],
                        default="all", help="采集源（默认全部）")
    parser.add_argument("--import-file", type=str, help="从已有 JSON 文件导入")
    parser.add_argument("--date", type=str, default=None,
                        help="指定日期（默认今天，格式 YYYY-MM-DD）")
    parser.add_argument("--dry-run", action="store_true",
                        help="试运行，不写入存储")
    parser.add_argument("--learn", action="store_true",
                        help="从已有数据批量学习作者分类")
    parser.add_argument("--learn-min-samples", type=int, default=2,
                        help="学习时最小样本数（默认2）")
    parser.add_argument("--learn-min-confidence", type=float, default=0.4,
                        help="学习时最小置信度（默认0.4）")
    
    args = parser.parse_args()
    
    # 批量学习模式
    if args.learn:
        if not AUTHOR_LEARNER_AVAILABLE:
            print("❌ author_learner 模块不可用")
            sys.exit(1)
        
        print("📚 批量学习作者分类...")
        learner = AuthorCategoryLearner()
        
        date = args.date or datetime.now().strftime("%Y-%m-%d")
        channels = ["x", "weibo", "rss"] if args.source == "all" else [args.source]
        
        total_learned = 0
        for channel in channels:
            jsonl_path = Path(__file__).parent.parent / "archive" / "daily" / date / f"{channel}.jsonl"
            if jsonl_path.exists():
                print(f"\n  学习 {channel} 渠道...")
                new_learned = learner.batch_learn_from_jsonl(
                    jsonl_path, 
                    min_confidence=args.learn_min_confidence,
                    min_samples=args.learn_min_samples
                )
                print(f"  新学习 {len(new_learned)} 个作者")
                total_learned += len(new_learned)
        
        print(f"\n✅ 总计新学习 {total_learned} 个作者")
        print(f"📊 累计已学习: {len(learner.learned_authors)} 个作者")
        
        # 显示学习报告
        print("\n" + learner.generate_report())
        return
    
    orchestrator = CollectorOrchestrator()
    if args.date:
        orchestrator.date = args.date
    
    if args.import_file:
        # 从文件导入模式
        print(f"从文件导入: {args.import_file}")
        with open(args.import_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        items = data if isinstance(data, list) else data.get("data", [])
        atoms = []
        
        for item in items:
            if args.source == "x":
                atom = orchestrator.x_adapter.tweet_to_atom(item, orchestrator.date)
            elif args.source == "weibo":
                atom = orchestrator.weibo_adapter.weibo_to_atom(item, orchestrator.date)
            else:
                print(f"  导入模式需要指定 --source (x 或 weibo)")
                sys.exit(1)
            
            if atom:
                atoms.append(atom)
        
        if not args.dry_run:
            ids = orchestrator.store.save_atoms_batch(atoms)
            print(f"导入 {len(ids)} 条 Atoms")
        else:
            print(f"[DRY RUN] 将导入 {len(atoms)} 条 Atoms")
            for a in atoms[:5]:
                print(f"  [{a['source']['author']}] {a['title'][:60]}")
    
    elif args.source == "all":
        # 完整采集
        try:
            atoms = orchestrator.run_full_collection()
        except RuntimeError as e:
            print(f"\n❌ 采集中断: {e}")
            sys.exit(1)
    
    elif args.source == "x":
        # 只采集 X → 写入 _x.jsonl
        try:
            tweets = orchestrator.x_adapter.fetch_following_timeline(200)
            atoms = []
            for t in tweets:
                # 先提取 RT/Quote Tweet 原帖
                quoted_atoms = orchestrator.x_adapter.extract_quoted_tweet(t, orchestrator.date)
                atoms.extend(quoted_atoms)
                # 再处理推文本身
                atom = orchestrator.x_adapter.tweet_to_atom(t, orchestrator.date)
                if atom:
                    atoms.append(atom)
            
            if not args.dry_run:
                ids = orchestrator.store.save_atoms_batch(atoms, channel="x")
                print(f"存储 {len(ids)} 条 X Atoms → {orchestrator.date}/x.jsonl")
        except RuntimeError as e:
            print(f"\n❌ X 采集失败: {e}")
            sys.exit(1)
    
    elif args.source == "weibo":
        # 只采集微博 → 写入 _weibo.jsonl
        weibos = orchestrator.weibo_adapter.fetch_all()
        atoms = [orchestrator.weibo_adapter.weibo_to_atom(w, orchestrator.date) for w in weibos]
        atoms = [a for a in atoms if a]
        
        if not args.dry_run:
            ids = orchestrator.store.save_atoms_batch(atoms, channel="weibo")
            print(f"存储 {len(ids)} 条微博 Atoms → {orchestrator.date}/weibo.jsonl")
    
    elif args.source == "rss":
        # 只采集 RSS → 写入 _rss.jsonl
        feeds = orchestrator.rss_adapter.load_feeds_from_config()
        if feeds:
            atoms = orchestrator.rss_adapter.fetch_all_feeds(feeds[:20], max_per_feed=10, collection_date=orchestrator.date)
            print(f"获取 {len(atoms)} 条 RSS Atoms")
            
            if not args.dry_run:
                ids = orchestrator.store.save_atoms_batch(atoms, channel="rss")
                print(f"存储 {len(ids)} 条 RSS Atoms → {orchestrator.date}/rss.jsonl")
        else:
            print("⚠️ 未找到 RSS feed 配置")
    
    print("\n✅ 采集完成")


if __name__ == "__main__":
    main()
