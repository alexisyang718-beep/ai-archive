#!/usr/bin/env python3
"""
增强版 X/Twitter 采集脚本
- 翻页获取 24 小时内全部关注流帖子
- 自动展开转推的原帖内容
- 输出结构化 JSON

用法:
    python x_fetch_enhanced.py
    python x_fetch_enhanced.py --hours 48 --output ./output/twitter_$(date +%Y%m%d).json
    python x_fetch_enhanced.py --hours 48 --format atom    # 输出到 v2/archive/daily/{date}_x.jsonl（Obsidian同步用）
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse

# 自动添加 uv 工具路径
UV_BIN_PATH = Path.home() / ".local" / "bin"
if str(UV_BIN_PATH) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{UV_BIN_PATH}:{os.environ.get('PATH', '')}"

# 默认配置
DEFAULT_HOURS = 24
DEFAULT_BATCH_SIZE = 100
DEFAULT_MAX_BATCHES = 10  # 最多翻页次数，防止无限循环
RATE_LIMIT_DELAY = 2  # 请求间隔秒数

# ============================================================================
# 账号 → 模块映射（与 x-lists-plan.md 保持一致）
# ============================================================================
# 模块常量
MODULE_AI = "🤖AI模型与产品"
MODULE_MOBILE = "📱手机与消费电子"
MODULE_CHIP = "🔧芯片与算力"
MODULE_GAME = "🎮游戏行业"
MODULE_TECH = "🏢科技行业动态"
MODULE_POLICY = "📜政策与监管"

# 账号分类映射：handle (小写) → 模块列表
# 一个账号可以属于多个模块
ACCOUNT_MODULE_MAP: Dict[str, List[str]] = {
    # 🤖 AI
    "_akhaliq": [MODULE_AI], "_xjdr": [MODULE_AI], "addyosmani": [MODULE_AI], "akothari": [MODULE_AI],
    "alexalbert__": [MODULE_AI], "alexandr_wang": [MODULE_AI], "alextamkin": [MODULE_AI], "allen_ai": [MODULE_AI],
    "alliekmiller": [MODULE_AI], "andrewyng": [MODULE_AI], "aravsrinivas": [MODULE_AI], "artificialanlys": [MODULE_AI],
    "barret_china": [MODULE_AI], "browser_use": [MODULE_AI], "chatgptapp": [MODULE_AI], "claudeai": [MODULE_AI],
    "clementdelangue": [MODULE_AI], "coreyganim": [MODULE_AI], "cursor_ai": [MODULE_AI], "darioamodei": [MODULE_AI],
    "davidsholz": [MODULE_AI], "demishassabis": [MODULE_AI], "diffusionpics": [MODULE_AI], "dotey": [MODULE_AI],
    "emollick": [MODULE_AI], "eng_khairallah1": [MODULE_AI], "figma": [MODULE_AI], "firecrawl": [MODULE_AI],
    "geoffreyhinton": [MODULE_AI], "googleai": [MODULE_AI], "googleaidevs": [MODULE_AI], "googledeepmind": [MODULE_AI],
    "grok": [MODULE_AI], "hardmaru": [MODULE_AI], "hbouammar": [MODULE_AI], "heyitsyogesh": [MODULE_AI],
    "heyshrutimishra": [MODULE_AI], "huangyun_122": [MODULE_AI], "huggingface": [MODULE_AI], "hwwaanng": [MODULE_AI],
    "ibusinessai": [MODULE_AI], "ilyasut": [MODULE_AI], "ivanhzhao": [MODULE_AI], "jakevin7": [MODULE_AI],
    "janleike": [MODULE_AI], "jeffdean": [MODULE_AI], "kaifulee": [MODULE_AI], "karpathy": [MODULE_AI],
    "kevinma_dev_zh": [MODULE_AI], "kimi_moonshot": [MODULE_AI], "langchain": [MODULE_AI], "lilianweng": [MODULE_AI],
    "llama_index": [MODULE_AI], "mcaleerstephen": [MODULE_AI], "miramurati": [MODULE_AI], "mistralai": [MODULE_AI],
    "mvansegb": [MODULE_AI], "notionhq": [MODULE_AI], "nousresearch": [MODULE_AI], "npew": [MODULE_AI],
    "initiallogank": [MODULE_AI], "ollama": [MODULE_AI], "openaidevs": [MODULE_AI], "openainewsroom": [MODULE_AI],
    "perplexity_ai": [MODULE_AI], "quocleix": [MODULE_AI], "rasbt": [MODULE_AI], "realpaulsmith": [MODULE_AI],
    "rowancheung": [MODULE_AI], "runes_leo": [MODULE_AI], "rwang07": [MODULE_AI], "saboo_shubham_": [MODULE_AI],
    "sainingxie": [MODULE_AI], "sama": [MODULE_AI], "seele_ai1125": [MODULE_AI], "sha__meng": [MODULE_AI],
    "teknium": [MODULE_AI], "tencentai_news": [MODULE_AI], "therundownai": [MODULE_AI], "thinkymachines": [MODULE_AI],
    "trae_ai": [MODULE_AI], "tukifromkl": [MODULE_AI], "wabi": [MODULE_AI], "woj_zaremba": [MODULE_AI],
    "xai": [MODULE_AI], "xianbao_qian": [MODULE_AI], "xiaohu": [MODULE_AI], "ylecun": [MODULE_AI],
    "youmind_ai": [MODULE_AI], "yuchenj_uw": [MODULE_AI], "zai_org": [MODULE_AI],
    "dontbesilent": [MODULE_AI], "elonmusk": [MODULE_AI], "triform_ai": [MODULE_AI],
    # 🎮 游戏
    "alphaintel": [MODULE_GAME], "appstoregames": [MODULE_GAME], "bytestix": [MODULE_GAME], "dexerto": [MODULE_GAME],
    "epicgames": [MODULE_GAME], "eric_seufert": [MODULE_GAME], "gamespot": [MODULE_GAME], "genki_jpn": [MODULE_GAME],
    "gibiz": [MODULE_GAME], "googleplay": [MODULE_GAME], "idlesloth84_": [MODULE_GAME], "ign": [MODULE_GAME],
    "nextgenplayer": [MODULE_GAME], "pcgamer": [MODULE_GAME], "playstation": [MODULE_GAME], "steam": [MODULE_GAME],
    "twitch": [MODULE_GAME], "zhugeex": [MODULE_GAME],
    # 💾 芯片/算力
    "drjimfan": [MODULE_CHIP], "gpucompute": [MODULE_CHIP], "nvidia": [MODULE_CHIP], "nvidiaaidev": [MODULE_CHIP],
    "nvidianewsroom": [MODULE_CHIP], "nvidiadc": [MODULE_CHIP], "compute_king": [MODULE_CHIP], "mingchikuo": [MODULE_CHIP],
    "semi_daily": [MODULE_CHIP], "yoolimleenews": [MODULE_CHIP], "harryjlu": [MODULE_CHIP], "anystream_ai": [MODULE_CHIP],
    "emallen_tech": [MODULE_CHIP], "chipsandtips": [MODULE_CHIP], "tsmc_trend": [MODULE_CHIP],
    "techinsight_inc": [MODULE_CHIP],
    # 📱 手机/消费电子
    "9to5mac": [MODULE_MOBILE], "appleinsider": [MODULE_MOBILE], "centroleaks": [MODULE_MOBILE], "creativestrat": [MODULE_MOBILE],
    "encoword": [MODULE_MOBILE], "huawei": [MODULE_MOBILE], "huweimobile": [MODULE_MOBILE], "kenhu_huawei": [MODULE_MOBILE],
    "macrumors": [MODULE_MOBILE], "mweinbach": [MODULE_MOBILE], "nakajimegame": [MODULE_MOBILE], "onLeaks": [MODULE_MOBILE],
    "oppo": [MODULE_MOBILE], "oppomobilekl": [MODULE_MOBILE], "shishirshelke1": [MODULE_MOBILE], "tim_cook": [MODULE_MOBILE],
    "universeice": [MODULE_MOBILE], "windowslatest": [MODULE_MOBILE], "yabhishekhd": [MODULE_MOBILE],
    # 🌐 泛科技 → 科技行业动态 + 政策与监管（双重命中，日报生成时二次分类）
    "_reachsumit": [MODULE_TECH], "abmankendrick": [MODULE_TECH], "appstore": [MODULE_TECH], "baicai003": [MODULE_TECH],
    "bbcbreaking": [MODULE_TECH, MODULE_POLICY], "bbcworld": [MODULE_TECH, MODULE_POLICY],
    "btcdayu": [MODULE_TECH], "business": [MODULE_TECH, MODULE_POLICY], "buzzfeed": [MODULE_TECH],
    "cartidise": [MODULE_TECH], "casualeffects": [MODULE_TECH], "ceobriefing": [MODULE_TECH],
    "chinesewsj": [MODULE_TECH, MODULE_POLICY], "cnbctech": [MODULE_TECH], "cnfinancewatch": [MODULE_TECH, MODULE_POLICY],
    "davidsacks": [MODULE_TECH], "defiteddy2020": [MODULE_TECH], "engadget": [MODULE_TECH], "foxshuo": [MODULE_TECH],
    "ftworldnews": [MODULE_TECH, MODULE_POLICY], "fusheng_0306": [MODULE_TECH], "fxtrader": [MODULE_TECH],
    "garrytan": [MODULE_TECH], "gm_t18": [MODULE_TECH], "hanyangwang": [MODULE_TECH], "hooeem": [MODULE_TECH],
    "jasminejaksic": [MODULE_TECH], "jukan05": [MODULE_TECH], "koreatimescokr": [MODULE_TECH], "lennysan": [MODULE_TECH],
    "linmiv": [MODULE_TECH], "love1mothe": [MODULE_TECH], "nake13": [MODULE_TECH], "natfriedman": [MODULE_TECH],
    "newscaixin": [MODULE_TECH, MODULE_POLICY], "nikitabier": [MODULE_TECH], "panda_liyin": [MODULE_TECH],
    "paulg": [MODULE_TECH], "piqsuite": [MODULE_TECH], "poezhao0605": [MODULE_TECH], "polymarket": [MODULE_TECH],
    "qq_timmy": [MODULE_TECH], "reidhoffman": [MODULE_TECH], "reuters": [MODULE_TECH, MODULE_POLICY],
    "reutersbiz": [MODULE_TECH, MODULE_POLICY], "sawyermerritt": [MODULE_TECH], "similarweb": [MODULE_TECH],
    "stocksavvyshay": [MODULE_TECH], "techcrunch": [MODULE_TECH], "techeconomyana": [MODULE_TECH],
    "techmeme": [MODULE_TECH], "thedankoe": [MODULE_TECH], "tweaktown": [MODULE_TECH], "uw": [MODULE_TECH],
    "verge": [MODULE_TECH], "vista8": [MODULE_TECH], "vkhosla": [MODULE_TECH], "wsj": [MODULE_TECH, MODULE_POLICY],
    "ycombinator": [MODULE_TECH], "yiguxia": [MODULE_TECH], "yq_acc": [MODULE_TECH], "yuyy614893671": [MODULE_TECH],
    "wallstsir": [MODULE_TECH], "zaobaosg": [MODULE_TECH, MODULE_POLICY],
}

# ── 已知垃圾广告账号（直接过滤，不收录）───────────────────────────────
# 格式：handle (小写)
KNOWN_SPAM_ACCOUNTS: set = {
    "cloudflare",      # SSL/TLS 域名广告
    "kodiakfi",        # "Get funded" 金融 promo
    "planetofmemes",   # 梗图账号，非科技
    "scalahosting",    # VPS 托管广告
    "tangem",          # 加密钱包 promo
    "tessera_pe",      # 私募 equity promo
    "gjdaniel99",      # affiliate marketing
    "ksorbs",          # 可疑链接
    "scorechain",      # 区块链 AML 广告
    "sip_app",         # color picker 工具 promo
    "travalacom",      # 加密货币 + 机票 promo
    # 以下为新增：发布历史推广帖的账号
    "vloot_io",       # CS皮肤抽奖广告
    "coinbound",       # Web3广告
    "woodmackenzie",   # 能源分析，非科技
    "vortexa",         # 能源海运数据，非科技
    "hashgraphonline", # 加密相关
    "sumsub",          # KYC/加密服务推广
    "cboe",            # 期权交易所，非科技
    "cybrid_xyz",      # 加密银行推广
    "cryptojobslist",  # 加密货币招聘
    "asx_capital",     # 金融投资
    "czapp_portal",    # 商品研究，非科技
    "dsmfirmenichanh", # 食品饮料，非科技
    "supportjimmylai", # 政治相关
    "tcgcornerglobal", # 交易信号
    "peterzaitsev",    # Percona 博客，非直接科技
    "nakajimegame",    # 游戏但非主流
    "igari_tomoka3",   # 个人账号
}

# ── 广告过滤关键词（正文匹配）──────────────────────────────────────────
AD_KEYWORD_PATTERNS: list = [
    "get funded today", "register your custom domain", "free ssl",
    "private equities", "access goes live", "book a demo",
    "manage your cloud vps", "get btc for every", "20% off",
    "crypto options", "600+ airlines", "aml compliance",
    "color picker", "bring ease to color organization",
    "blockchain analytics effortless",
]


def is_advertisement(tweet: Dict) -> bool:
    """
    判断一条推文是否为广告/垃圾内容。
    检查维度：账号黑名单 + 正文关键词 + 互动数据（广告帖通常互动极低）
    """
    author = tweet.get('author', {})
    screen = author.get('screenName', '').lower()
    text = (tweet.get('text', '') + ' ' + author.get('description', '')).lower()
    metrics = tweet.get('metrics', {})
    likes = metrics.get('likeCount', metrics.get('favoritesCount', 0))
    rts = metrics.get('retweetCount', 0)
    views = metrics.get('viewCount', metrics.get('impressionCount', 0))

    # 1. 账号黑名单
    if screen in KNOWN_SPAM_ACCOUNTS:
        return True

    # 2. 正文关键词过滤（广告特征词）
    text_lower = tweet.get('text', '').lower()
    for kw in AD_KEYWORD_PATTERNS:
        if kw in text_lower:
            return True

    # 3. 极低互动 + 短文本 + 外链（非关注账号的低质量 promotional 帖）
    if likes < 3 and rts < 1 and views < 100 and len(text_lower.strip()) < 60:
        # 可能是广告/机器人帖，但不做强制过滤（保留有嵌入链接的）
        pass

    return False


# ── 关键词 → 模块 兜底映射（用于未关注账号的 RT 原帖）─────────────────
TEXT_MODULE_KEYWORDS: Dict[str, List[str]] = {
    MODULE_AI: [
        "gpt", "claude", "gemini", "llm", "ai model", "openai", "anthropic",
        "deepmind", "midjourney", "stable diffusion", "hugging face", "mistral",
        "artificial intelligence", "large language", "chatgpt", "Cursor", "vibe coding",
        "notion", "ollama", "langchain", "perplexity", "kimi", "月之暗面",
        "智谱", "通义", "minimax", "零一", "阶跃星辰", "deepseek",
    ],
    MODULE_CHIP: [
        "nvidia", "gpu", "h100", "h200", "b200", "gb200", "cuda",
        "semiconductor", "芯片", "gpu", "arm", "intel", "amd",
        "台积电", "tsmc", "三星", "中芯", "SMIC", "ASML",
        "算力", "AI chip", "GPU compute",
    ],
    MODULE_GAME: [
        "game", "playstation", "xbox", "nintendo", "steam", "epic games",
        "pokemon", "ign", "gaming", "电竞", "游戏",
    ],
    MODULE_MOBILE: [
        "iphone", "ipad", "android", "samsung", "huawei", "小米", "oppo", "vivo",
        "apple", "pixel", "oneplus", "手机", "移动设备",
    ],
}


def infer_modules_from_text(tweet: Dict) -> List[str]:
    """
    根据推文正文关键词推断模块（兜底策略，用于未收录的账号）。
    返回匹配的模块列表，优先返回单一模块。
    """
    text = tweet.get('text', '').lower()
    matched = []
    for module, keywords in TEXT_MODULE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > 0:
            matched.append((score, module))
    if matched:
        matched.sort(key=lambda x: -x[0])
        return [matched[0][1]]
    # 没有任何关键词匹配，归入泛科技
    return [MODULE_TECH]


def get_account_modules(author_handle: str) -> List[str]:
    """根据账号 handle 返回对应的模块列表，未知账号返回空列表"""
    handle = author_handle.lstrip("@").lower()
    return ACCOUNT_MODULE_MAP.get(handle, [])


def run_twitter_command(args: List[str]) -> Optional[Dict]:
    """执行 twitter-cli 命令并返回 JSON 结果"""
    cmd = ["twitter"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            print(f"⚠️ 命令失败: {' '.join(cmd)}")
            print(f"错误: {result.stderr}")
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print(f"⏱️ 命令超时: {' '.join(cmd)}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        print(f"原始输出: {result.stdout[:500]}")
        return None
    except Exception as e:
        print(f"❌ 执行错误: {e}")
        return None


def parse_tweet_time(time_str: str) -> Optional[datetime]:
    """解析推文时间字符串"""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%a %b %d %H:%M:%S +0000 %Y",  # Twitter API 格式
    ]
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    # 尝试 ISO 格式
    try:
        return datetime.fromisoformat(time_str.replace('Z', '+00:00').replace('+00:00', ''))
    except:
        pass
    return None


def fetch_original_tweet(tweet_id: str) -> Optional[Dict]:
    """
    获取转推的原帖完整内容
    
    注意: twitter-cli 的 feed 命令返回的转推不包含原帖内容
    我们使用 tweet 命令获取原帖详情
    """
    if not tweet_id:
        return None
    
    print(f"    📄 获取原帖: {tweet_id}")
    time.sleep(RATE_LIMIT_DELAY)
    
    # 使用 tweet 命令获取原帖（返回数组，第一个是主帖）
    result = run_twitter_command(["tweet", tweet_id, "--json"])
    if result and 'data' in result and len(result['data']) > 0:
        return result['data'][0]  # 第一个是主帖，后面是回复
    return None


def expand_retweet(tweet: Dict) -> Dict:
    """
    展开转推，确保原帖信息完整。

    twitter-cli 的 RT 结构：
    - author = 原帖作者（已经是原帖，不是RT者）
    - text = 原帖正文
    - urls = 原帖嵌入式链接
    - retweetedBy = 转发者用户名
    - retweetedStatus = 不存在（无需查找）

    我们只需确保 retweetedBy 被正确记录，并补充原帖原始链接。
    """
    is_retweet = tweet.get('isRetweet', False)
    if not is_retweet:
        return tweet

    retweeted_by = tweet.get('retweetedBy')
    if not retweeted_by:
        return tweet

    expanded = tweet.copy()

    # 构建完整的原帖信息（twitter-cli 已内嵌原帖数据）
    original_author = tweet.get('author', {})
    original_text = tweet.get('text', '')
    original_urls = tweet.get('urls', [])

    # 补充：原帖作者的原始帖子链接
    original_author_handle = original_author.get('screenName', '')
    original_tweet_id = tweet.get('id', '')
    if original_author_handle and original_tweet_id:
        original_urls = original_urls.copy()  # 不修改原引用
        original_urls.append(f"https://x.com/{original_author_handle}/status/{original_tweet_id}")

    # 保留转推者的转发行为信息（追加，不是覆盖）
    expanded['_retweetMeta'] = {
        'retweetedBy': retweeted_by,
        'originalAuthor': original_author_handle,
        'originalTweetId': original_tweet_id,
        'originalTweetUrl': f"https://x.com/{original_author_handle}/status/{original_tweet_id}" if original_author_handle and original_tweet_id else None,
        'originalText': original_text[:200] if original_text else None,
    }

    # urls：确保包含原文链接
    expanded['urls'] = original_urls
    expanded['isRetweet'] = True
    expanded['_isRetweetExpanded'] = True  # 已完全展开

    return expanded


def fetch_following_timeline(hours: int = DEFAULT_HOURS, expand_retweets: bool = True) -> List[Dict]:
    """
    获取关注流，支持大批量采集
    
    由于 twitter-cli 的 feed 命令不支持翻页 cursor，我们采用以下策略：
    1. 增大单次请求数量 (--max 200 可获取更多)
    2. 按时间过滤，只保留指定时间范围内的
    3. 对转推自动展开原帖内容
    
    Args:
        hours: 获取多少小时内的帖子
        expand_retweets: 是否展开转推原帖
    
    Returns:
        所有符合条件的推文列表
    """
    # 推文时间是 UTC，所以用 utcnow() 来比较
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    print(f"⏰ 采集时间范围: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')} UTC 至今")
    print(f"📊 单次请求: {DEFAULT_BATCH_SIZE} 条")
    print("-" * 60)
    
    all_tweets = []
    batch_count = 0
    
    # 由于不支持翻页，我们增大单次请求量
    # twitter-cli 实际能返回的数量可能超过 --max，取决于 API
    fetch_size = min(DEFAULT_BATCH_SIZE * 2, 200)  # 最多一次请求 200 条
    
    while batch_count < DEFAULT_MAX_BATCHES:
        batch_count += 1
        print(f"\n🔄 第 {batch_count} 批次采集 (请求 {fetch_size} 条)...")
        
        # 执行请求
        result = run_twitter_command([
            "feed", "-t", "following", 
            "--max", str(fetch_size), 
            "--json"
        ])
        
        if not result:
            print("⚠️ API 请求失败，停止采集")
            break
        
        # 解析结果
        tweets = result.get('data', []) if 'data' in result else []
        
        if not tweets:
            print("⚠️ 没有获取到数据")
            break
        
        print(f"   获取到 {len(tweets)} 条原始推文")
        
        # 处理每条推文
        batch_valid_count = 0
        batch_expanded_count = 0
        batch_out_of_range = 0
        
        for tweet in tweets:
            # 解析时间
            time_str = tweet.get('createdAt') or tweet.get('createdAtLocal')
            tweet_time = parse_tweet_time(time_str) if time_str else None
            
            if not tweet_time:
                # 无法解析时间的，保留但标记
                tweet['_fetchedAt'] = datetime.now().isoformat()
                all_tweets.append(tweet)
                continue
            
            # 检查是否在时间范围内
            if tweet_time < cutoff_time:
                batch_out_of_range += 1
                continue  # 跳过超时的
            
            # 展开转推（如果是转推且需要展开）
            is_retweet = tweet.get('isRetweet', False)
            if is_retweet and expand_retweets:
                retweeted_by = tweet.get('retweetedBy')
                if retweeted_by:
                    print(f"   🔄 展开转推 by @{retweeted_by}: {tweet.get('text', '')[:50]}...")
                    tweet = expand_retweet(tweet)
                    batch_expanded_count += 1
            elif not is_retweet:
                # 非RT：确保 urls 字段存在且包含可点击链接（推文内嵌链接）
                urls = tweet.get('urls', [])
                if urls:
                    # urls 已是原始链接（含短链如 reut.rs/bit.ly 或完整URL）
                    # 标记备用完整URL
                    tweet['_hasEmbeddedLinks'] = True

            # 添加元数据
            tweet['_fetchedAt'] = datetime.now().isoformat()
            tweet['_tweetTime'] = tweet_time.isoformat()

            # ── 广告过滤 ───────────────────────────────────────────
            if is_advertisement(tweet):
                print(f"   🚫 广告过滤: @{tweet.get('author',{}).get('screenName','?')}: {tweet.get('text','')[:40]}...")
                continue

            # ── 账号 → 模块分类 ──────────────────────────────────────
            author_handle = tweet.get('author', {}).get('screenName', '')
            is_rt = tweet.get('isRetweet', False)

            # 从账号映射表获取模块
            modules = get_account_modules(author_handle)

            if not modules:
                # 未知账号（未收录在名单中）→ 用关键词兜底推断
                # 这种情况常见于：RT 的原帖作者不在我们的 Following 名单里
                tweet['_unfollowedOriginalAuthor'] = is_rt  # RT：原帖未关注；非RT：发帖者未关注
                modules = infer_modules_from_text(tweet)
                tweet['_modules'] = modules
                tweet['_modulesInferred'] = True  # 标记为推断，非账号归属
                rt_meta = tweet.get('_retweetMeta', {})
                orig_author = rt_meta.get('originalAuthor', author_handle)
                print(f"   ⚠️ 未知账号 @{author_handle} → 关键词推断模块: {modules[0]}（{('RT原帖@'+orig_author) if is_rt else '发帖者'}）")
            else:
                # 已知账号：正常归属
                tweet['_modules'] = modules
                # RT 原帖作者如果在名单里也有归属，加上（可能和转发者模块不同）
                if is_rt:
                    rt_meta = tweet.get('_retweetMeta', {})
                    orig_author = rt_meta.get('originalAuthor', '')
                    if orig_author and orig_author.lower() in ACCOUNT_MODULE_MAP:
                        orig_modules = get_account_modules(orig_author)
                        if orig_modules and orig_modules != modules:
                            # RT 者模块 + 原帖作者模块都保留（跨模块内容）
                            tweet['_originalAuthorModules'] = orig_modules
            # ── 分类完成 ───────────────────────────────────────────
            
            all_tweets.append(tweet)
            batch_valid_count += 1
        
        print(f"   ✅ 有效: {batch_valid_count} 条 | 🔄 转推: {batch_expanded_count} 条 | ⏰ 超时: {batch_out_of_range} 条")
        
        # 如果这次请求的所有推文都在时间范围内，可能需要更多数据
        # 但由于不支持翻页，我们只能停止
        if batch_out_of_range == 0 and len(tweets) >= fetch_size * 0.9:
            print(f"   ℹ️ 可能还有更多数据，但 twitter-cli 不支持翻页")
        
        # 只执行一次，因为不支持翻页
        break
    
    print(f"\n{'='*60}")
    print(f"✅ 采集完成: 共 {len(all_tweets)} 条推文")
    
    return all_tweets


def deduplicate_tweets(tweets: List[Dict]) -> List[Dict]:
    """去重：基于推文 ID"""
    seen_ids = set()
    unique = []
    
    for tweet in tweets:
        tweet_id = tweet.get('id')
        if tweet_id and tweet_id not in seen_ids:
            seen_ids.add(tweet_id)
            unique.append(tweet)
    
    print(f"🔄 去重: {len(tweets)} → {len(unique)} 条")
    return unique


def save_results(tweets: List[Dict], output_path: str):
    """保存结果到 JSON 文件"""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 添加元数据
    result = {
        'meta': {
            'fetchedAt': datetime.now().isoformat(),
            'tweetCount': len(tweets),
            'hoursWindow': DEFAULT_HOURS,
            'tool': 'twitter-cli',
            'version': '2.0'
        },
        'tweets': tweets
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"💾 已保存到: {output_file}")
    return output_file


def save_atoms(tweets: List[Dict], date_str: str) -> Path:
    """
    将推文转换为 Atom 格式并保存到 v2/archive/daily/{date}_x.jsonl

    Atom 字段映射：
    - id: atom_{date}_{seq:03d}
    - date: YYYY-MM-DD
    - title: 完整文本（前120字）
    - source.platform: "x"
    - source.author: @handle
    - source.url: https://x.com/{handle}/status/{id}
    - source.timestamp: YYYY-MM-DD HH:MM
    - content_type: 推断类型
    - category: 六大模块之一
    - trust_default: L1~L3
    """
    # 推文时间 → YYYY-MM-DD HH:MM
    def tweet_time_to_ts(tweet: Dict) -> str:
        iso = tweet.get('_tweetTime', '')
        if iso:
            return iso[:16].replace('T', ' ')
        return ''

    # 推文 → Atom
    atoms = []
    for i, tweet in enumerate(tweets):
        author = tweet.get('author', {})
        screen = author.get('screenName', '')
        tweet_id = tweet.get('id', '')
        text = tweet.get('text', '')
        if len(text) > 120:
            title = text[:120] + '…'
        else:
            title = text

        # 内容类型推断
        if tweet.get('isRetweet'):
            content_type = 'retweet'
        elif any(k in text for k in ['RT @', 'retweeted']):
            content_type = 'retweet'
        elif tweet.get('urls') or tweet.get('_hasEmbeddedLinks'):
            content_type = 'firsthand_report'
        else:
            content_type = 'commentary'

        # 信任等级
        if screen.lower() in ('sama', 'elonmusk', 'tylerlto', 'kaborosh', '_akhaliq', '_xjdr', 'addyosmani', 'akothari', 'alexalbert__', 'alexandr_wang'):
            trust = 'L1'
        else:
            trust = 'L2'

        # 模块（用已有的 _modules 标注为 tags）
        modules = tweet.get('_modules', [])
        tags = modules if modules else ['other']

        atom = {
            'id': f"atom_{date_str.replace('-','')}_{i+1:03d}",
            'date': date_str,
            'title': title,
            'title_zh': title,
            'summary_zh': text,
            'source': {
                'platform': 'x',
                'author': f'@{screen}',
                'author_type': 'kol',
                'url': f'https://x.com/{screen}/status/{tweet_id}' if tweet_id else '',
                'timestamp': tweet_time_to_ts(tweet),
            },
            'content_type': content_type,
            'trust_default': trust,
            'trust_final': None,
            'trust_reason': None,
            'category': modules[0] if modules else 'other',
            'tags': tags,
            'entities': [],
            'metrics': {
                'likes': tweet.get('likeCount', 0) or tweet.get('likes', 0),
                'retweets': tweet.get('retweetCount', 0) or tweet.get('retweets', 0),
                'replies': tweet.get('replyCount', 0) or tweet.get('replies', 0),
                'views': tweet.get('viewCount', 0) or tweet.get('views', 0),
            },
            'in_daily_brief': False,
            'brief_date': None,
            'related_atoms': [],
            'full_text_fetched': False,
            'full_text_path': None,
            'channel': 'x',
        }
        atoms.append(atom)

    # 保存到 atom store 路径
    base_dir = Path(__file__).parent.parent / 'v2' / 'archive' / 'daily'
    out_path = base_dir / f'{date_str}_x.jsonl'
    base_dir.mkdir(parents=True, exist_ok=True)

    with open(out_path, 'w', encoding='utf-8') as f:
        for a in atoms:
            f.write(json.dumps(a, ensure_ascii=False) + '\n')

    print(f"💾 Atom 已保存: {out_path} ({len(atoms)} 条)")
    return out_path


def print_summary(tweets: List[Dict]):
    """打印采集摘要"""
    print(f"\n{'='*60}")
    print("📋 采集摘要")
    print("="*60)
    
    # 统计
    retweet_count = sum(1 for t in tweets if t.get('isRetweet'))
    original_count = len(tweets) - retweet_count
    
    print(f"总推文数: {len(tweets)}")
    print(f"  - 原创/原帖: {original_count}")
    print(f"  - 转推: {retweet_count}")
    
    # 按作者统计（转推显示原帖作者）
    author_stats = {}
    for t in tweets:
        author = t.get('author', {}).get('screenName', 'unknown')
        author_stats[author] = author_stats.get(author, 0) + 1
    
    print(f"\n👤 活跃作者 Top 10:")
    for author, count in sorted(author_stats.items(), key=lambda x: -x[1])[:10]:
        print(f"  @{author}: {count} 条")
    
    # 转推来源统计
    retweet_sources = {}
    for t in tweets:
        if t.get('isRetweet'):
            source = t.get('retweetedBy') or t.get('_retweetedBy', 'unknown')
            retweet_sources[source] = retweet_sources.get(source, 0) + 1
    
    if retweet_sources:
        print(f"\n🔄 转推来源 Top 5:")
        for source, count in sorted(retweet_sources.items(), key=lambda x: -x[1])[:5]:
            print(f"  @{source}: {count} 条")
    
    # 最新/最早
    if tweets:
        times = [t.get('_tweetTime', '') for t in tweets if '_tweetTime' in t]
        if times:
            print(f"\n⏰ 时间范围:")
            print(f"  最早: {min(times)}")
            print(f"  最新: {max(times)}")


def main():
    global DEFAULT_MAX_BATCHES
    
    parser = argparse.ArgumentParser(description='增强版 X/Twitter 采集脚本')
    parser.add_argument('--hours', type=int, default=DEFAULT_HOURS,
                        help=f'采集多少小时内的帖子 (默认: {DEFAULT_HOURS})')
    parser.add_argument('--output', type=str,
                        default=f"./output/twitter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        help='输出文件路径')
    parser.add_argument('--no-expand', action='store_true',
                        help='不展开转推原帖')
    parser.add_argument('--max-batches', type=int, default=DEFAULT_MAX_BATCHES,
                        help=f'最大翻页次数 (默认: {DEFAULT_MAX_BATCHES})')
    parser.add_argument('--format', type=str, choices=['json', 'atom'], default='atom',
                        help='输出格式: json=原始推文JSON, atom=Atom格式(默认)')

    args = parser.parse_args()
    
    DEFAULT_MAX_BATCHES = args.max_batches
    
    print("🚀 启动 X/Twitter 增强采集")
    print(f"📁 输出文件: {args.output}")
    print("="*60)
    
    # 检查 twitter-cli
    result = subprocess.run(["which", "twitter"], capture_output=True)
    if result.returncode != 0:
        print("❌ 未找到 twitter 命令")
        print("请安装: uv tool install twitter-cli")
        sys.exit(1)
    
    # 采集
    tweets = fetch_following_timeline(args.hours)
    
    if not tweets:
        print("❌ 未获取到任何推文")
        sys.exit(1)
    
    # 去重
    tweets = deduplicate_tweets(tweets)
    
    # 按时间排序
    tweets.sort(key=lambda x: x.get('_tweetTime', ''), reverse=True)
    
    # 保存
    date_str = datetime.now().strftime('%Y-%m-%d')
    if args.format == 'atom':
        save_atoms(tweets, date_str)
    else:
        save_results(tweets, args.output)
    
    # 摘要
    print_summary(tweets)


if __name__ == "__main__":
    main()
