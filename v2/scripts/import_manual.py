#!/usr/bin/env python3
"""
手动导入新闻条目到 Atom 系统
用法：python3 import_manual.py
"""

import sys, json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from atom_store import AtomStore, create_atom
from obsidian_sync import ObsidianSyncer

DATE = "2026-03-19"

# ============ 待导入的新闻条目 ============

NEWS_ITEMS = [
    # === 🎮 游戏行业 ===
    {
        "title": "Clair Obscur: Expedition 33 获 GDCA 2026 年度游戏大奖",
        "title_zh": "Clair Obscur: Expedition 33 获 GDCA 2026 年度游戏大奖",
        "summary_zh": "法国工作室 Sandfall Interactive 开发的回合制 RPG《光与影：33号远征队》在 2026 年 GDC 游戏开发者选择奖中斩获年度游戏等五项大奖。游戏已售出超过 200 万份。BAFTA 游戏奖也提名该作 12 个奖项。",
        "platform": "web",
        "author": "GamesIndustry.biz",
        "author_type": "media",
        "url": "https://www.gamesindustry.biz/clair-obscur-expedition-33-wins-game-of-the-year-at-gdca-2026",
        "content_type": "report",
        "category": "gaming",
        "tags": ["gaming", "gdca", "awards", "indie_game", "rpg"],
        "entities": ["Clair Obscur", "Sandfall Interactive", "BAFTA"],
        "trust_default": "L2",
    },
    {
        "title": "GDC 2026 参展人数骤降 30% 至 2 万人",
        "title_zh": "GDC 2026 参展人数骤降 30% 至 2 万人",
        "summary_zh": "旧金山游戏开发者大会 2026 年参展人数从去年超 3 万跌至 2 万（-30%），主因是大规模裁员潮和签证政策收紧。GDC 主旨演讲者直接呼吁行业高管停止裁员。一项调查显示三分之一游戏从业者在过去两年被裁。",
        "platform": "web",
        "author": "SF Chronicle / Polygon",
        "author_type": "media",
        "url": "https://www.sfchronicle.com/bayarea/article/tech-conference-attendance-plunged-22079584.php",
        "content_type": "report",
        "category": "gaming",
        "tags": ["gaming", "gdc", "layoffs", "conference"],
        "entities": ["GDC", "San Francisco"],
        "trust_default": "L2",
    },
    {
        "title": "Warner Bros. 蒙特利尔工作室裁员",
        "title_zh": "Warner Bros. 蒙特利尔工作室裁员",
        "summary_zh": "Warner Bros. 蒙特利尔游戏工作室遭遇新一轮裁员。该工作室曾开发《蝙蝠侠：哥谭骑士》。游戏行业裁员潮持续蔓延。",
        "platform": "web",
        "author": "GamesIndustry.biz",
        "author_type": "media",
        "url": "https://www.gamesindustry.biz/warner-bros-montreal-reportedly-hit-with-staff-cuts",
        "content_type": "report",
        "category": "gaming",
        "tags": ["gaming", "layoffs", "warner_bros"],
        "entities": ["Warner Bros."],
        "trust_default": "L2",
    },
    {
        "title": "Newzoo 报告：PC 游戏收入将在 2028 年超过主机",
        "title_zh": "Newzoo 报告：PC 游戏收入将在 2028 年超过主机",
        "summary_zh": "Newzoo 年度 PC 与游戏报告显示，Steam 主导的 PC 市场增长将推动 PC 游戏收入在 2028 年超过 Switch 2+PS5+Xbox 的总和。低价（$30 以下）游戏在 PC 平台占比飙升 156%（2022-2025），占 Steam 收入的 32%。$70 3A 游戏风险越来越高。",
        "platform": "web",
        "author": "Kotaku",
        "author_type": "media",
        "url": "https://kotaku.com/steam-game-prices-clair-obscur-data-sales-2000678987",
        "content_type": "report",
        "category": "gaming",
        "tags": ["gaming", "steam", "pc", "newzoo", "market_data"],
        "entities": ["Steam", "Newzoo", "Nintendo Switch", "PlayStation", "Xbox"],
        "trust_default": "L2",
    },
    {
        "title": "Xbox Gaming Copilot 将登陆现世代主机",
        "title_zh": "Xbox Gaming Copilot 将于 2026 年登陆现世代主机",
        "summary_zh": "微软宣布 Gaming Copilot（AI 游戏助手）将于 2026 年登陆 Xbox Series X/S。此举将 AI 助手引入游戏主机，是 AI 在游戏领域落地的重要信号。",
        "platform": "web",
        "author": "GamesIndustry.biz",
        "author_type": "media",
        "url": "https://www.gamesindustry.biz/gaming-copilot-coming-to-current-gen-xbox-consoles-in-2026",
        "content_type": "report",
        "category": "gaming",
        "tags": ["gaming", "xbox", "ai", "copilot", "microsoft"],
        "entities": ["Xbox", "Microsoft", "Copilot"],
        "trust_default": "L2",
    },
    {
        "title": "Starfield 登陆 PS5 并公布新 DLC",
        "title_zh": "Starfield 确定 PS5 发售日期，附带新剧情 DLC",
        "summary_zh": "Bethesda 宣布《星空》PS5 版发售日期，同时推出新故事 DLC 和 Free Lanes 更新。Bethesda 暗示对该游戏有「长期计划」。",
        "platform": "web",
        "author": "Eurogamer",
        "author_type": "media",
        "url": "https://www.eurogamer.net/starfield-ps5-release-date",
        "content_type": "report",
        "category": "gaming",
        "tags": ["gaming", "starfield", "bethesda", "ps5"],
        "entities": ["Bethesda", "PlayStation 5", "Starfield"],
        "trust_default": "L2",
    },
    {
        "title": "Take-Two CEO：AI 无法创造 GTA 6 量级的作品",
        "title_zh": "Take-Two CEO：AI 无法创造 GTA 6 量级的作品",
        "summary_zh": "Take-Two Interactive CEO Strauss Zelnick 再次否定 AI 能独立制作 GTA 6 级别的大型游戏，强调「创造这种量级的作品需要人类的参与和创造力」。",
        "platform": "web",
        "author": "Eurogamer",
        "author_type": "media",
        "url": "https://www.eurogamer.net/take-two-ceo-ai-gta6",
        "content_type": "commentary",
        "category": "gaming",
        "tags": ["gaming", "ai", "gta6", "take_two"],
        "entities": ["Take-Two", "GTA 6"],
        "trust_default": "L2",
    },

    # === 🏛️ 科技行业动态 ===
    {
        "title": "SpaceX/OpenAI/Anthropic 2026 超级 IPO 年：三巨头合计估值超 2.4 万亿美元",
        "title_zh": "SpaceX/OpenAI/Anthropic 2026 超级 IPO 年：三巨头合计估值超 2.4 万亿美元",
        "summary_zh": "PitchBook 分析师报告：SpaceX（1.5万亿）、OpenAI（8400亿）、Anthropic（3300亿）可能在 2026 年 IPO，合计估值 2.4 万亿美元，将打破 VC-backed IPO 纪录。三家若同时上市可能挤压其他 IPO 的资金。OpenAI 2026年2月单笔融资 1100 亿美元。",
        "platform": "web",
        "author": "PitchBook",
        "author_type": "analyst",
        "url": "https://pitchbook.com/news/reports/q1-2026-analyst-note-mega-ipos-could-threaten-2026-ipo-class",
        "content_type": "original_analysis",
        "category": "tech_industry",
        "tags": ["ipo", "spacex", "openai", "anthropic", "venture_capital"],
        "entities": ["SpaceX", "OpenAI", "Anthropic", "Elon Musk"],
        "trust_default": "L2",
    },
    {
        "title": "Block/Atlassian/Dell CEO 宣布用 AI 替代员工",
        "title_zh": "Block、Atlassian、Dell CEO 宣布用 AI 替代员工",
        "summary_zh": "Block（Square 母公司）和 Atlassian CEO 明确表示将用 AI 替代部分员工岗位。Dell 同样在推进 AI 驱动的现代化转型。科技公司正从「裁员以削减成本」转向「AI 替代以提升效率」的新阶段。",
        "platform": "web",
        "author": "Business Insider / The Next Web",
        "author_type": "media",
        "url": "https://thenextweb.com/news/block-atlassian-dell-ai-replace-workers",
        "content_type": "report",
        "category": "tech_industry",
        "tags": ["ai", "layoffs", "automation", "block", "atlassian", "dell"],
        "entities": ["Block", "Atlassian", "Dell"],
        "trust_default": "L2",
    },
    {
        "title": "Meta 公布自研 AI 芯片路线图：24 个月内出 4 代 MTIA",
        "title_zh": "Meta 公布自研 AI 芯片路线图：24 个月内推出 4 代 MTIA 芯片",
        "summary_zh": "Meta 公布 MTIA（Meta Training and Inference Accelerator）芯片路线图，计划 24 个月内推出 MTIA 300/400/450/500 四代芯片，开发周期仅 6 个月（行业标准 1-2 年）。MTIA 300 已大规模部署于 Meta 旗下 App 的排序和推荐系统。此举信号大厂开始摆脱对 NVIDIA GPU 的依赖。",
        "platform": "web",
        "author": "Telecoms.com",
        "author_type": "media",
        "url": "https://www.telecoms.com/ai/meta-details-its-in-house-ai-chip-roadmap",
        "content_type": "report",
        "category": "tech_industry",
        "tags": ["meta", "ai_chip", "mtia", "nvidia", "custom_silicon"],
        "entities": ["Meta", "NVIDIA", "AMD", "MTIA"],
        "trust_default": "L2",
    },
    {
        "title": "欧洲 AI 基础设施融资爆发：Nscale 估值 146 亿美元，AMI Labs 种子轮 10.3 亿美元",
        "title_zh": "欧洲 AI 基础设施融资爆发：Nscale 估值 146 亿美元",
        "summary_zh": "本周欧洲十大融资轮中，AI 基础设施公司 Nscale 以 $14.6B 估值完成 C 轮（4个月估值翻 4 倍），法国 AMI Labs 完成 $1.03B 种子轮（史上最大种子轮之一）。AI 计算基础设施成为欧洲 VC 最热赛道。",
        "platform": "web",
        "author": "The Next Web",
        "author_type": "media",
        "url": "https://thenextweb.com/news/europe-startup-funding-rounds-march",
        "content_type": "report",
        "category": "tech_industry",
        "tags": ["funding", "ai_infrastructure", "europe", "nscale", "ami_labs"],
        "entities": ["Nscale", "AMI Labs"],
        "trust_default": "L2",
    },

    # === 📜 政策与监管 ===
    {
        "title": "美国白宫与共和党准备阻止各州 AI 立法",
        "title_zh": "美国白宫与共和党准备阻止各州 AI 立法",
        "summary_zh": "美国白宫 AI 主管和众议院共和党正在推动一项提案，可能禁止各州和地方政府在最多 10 年内对 AI 进行监管，以实现联邦层面统一的 AI 政策框架。这引发了关于 AI 安全与创新平衡的激烈争论。",
        "platform": "web",
        "author": "Washington Post",
        "author_type": "media",
        "url": "https://www.washingtonpost.com/wp-intelligence/ai-tech-brief/2026/03/16/white-house-house-gop-prepare-block-state-ai-laws/",
        "content_type": "report",
        "category": "policy",
        "tags": ["policy", "ai_regulation", "us", "preemption"],
        "entities": ["White House"],
        "trust_default": "L2",
    },
    {
        "title": "华盛顿邮报：国会正在输掉 AI 监管竞赛",
        "title_zh": "华盛顿邮报：国会正在输掉 AI 监管竞赛",
        "summary_zh": "华盛顿邮报专访硅谷众议员 Sam Liccardo，他认为美国国会无力监管 AI，分享了弥合监管差距的方案。报道分析了 AI 监管滞后于技术发展的深层原因。",
        "platform": "web",
        "author": "Washington Post",
        "author_type": "media",
        "url": "https://www.washingtonpost.com/wp-intelligence/ai-tech-brief/2026/03/17/congress-is-losing-race-regulate-ai/",
        "content_type": "original_analysis",
        "category": "policy",
        "tags": ["policy", "ai_regulation", "us_congress"],
        "entities": [],
        "trust_default": "L2",
    },
    {
        "title": "德州 AI 治理法案生效：平衡安全与创新的新模型",
        "title_zh": "德州 AI 治理法案 1 月生效，成为美国 AI 监管新模型",
        "summary_zh": "Bloomberg Law 分析：德州《负责任 AI 治理法案》(TRAIGA) 已于 2026 年 1 月 1 日生效，对有害 AI 使用施加限制但保留创新空间，被视为美国 AI 监管的参考模型。",
        "platform": "web",
        "author": "Bloomberg Law",
        "author_type": "media",
        "url": "https://news.bloomberglaw.com/bloomberg-law-analysis/analysis-new-texas-ai-law-seeks-to-balance-safety-innovation",
        "content_type": "original_analysis",
        "category": "policy",
        "tags": ["policy", "ai_regulation", "texas", "traiga"],
        "entities": [],
        "trust_default": "L2",
    },
    {
        "title": "美国商务部推 AI 出口套餐计划",
        "title_zh": "美国商务部推出「全栈 AI 出口套餐」计划",
        "summary_zh": "美国商务部正在征集「全栈 AI 出口套餐」提案，包括 AI 优化硬件、数据中心存储、模型、网络安全措施和应用方案，旨在将美国 AI 技术包捆绑出口到更多国家。",
        "platform": "web",
        "author": "Washington Post / Commerce Dept",
        "author_type": "media",
        "url": "https://www.washingtonpost.com/wp-intelligence/ai-tech-brief/2026/03/17/commerce-ai-export-packages/",
        "content_type": "report",
        "category": "policy",
        "tags": ["policy", "ai_export", "us_commerce", "export_control"],
        "entities": [],
        "trust_default": "L2",
    },

    # === 📱 手机与消费电子 ===
    {
        "title": "OPPO/OnePlus/vivo 官宣中国市场手机涨价",
        "title_zh": "OPPO、OnePlus、vivo 官宣中国市场手机涨价",
        "summary_zh": "OPPO、OnePlus 和 vivo 正式宣布在中国市场提高智能手机价格。涨价原因包括零部件成本上升和供应链压力。",
        "platform": "web",
        "author": "Notebookcheck",
        "author_type": "media",
        "url": "https://www.notebookcheck.net/Oppo-OnePlus-and-Vivo-officially-announce-smartphone-price-increase-in-China.1251229.0.html",
        "content_type": "report",
        "category": "mobile",
        "tags": ["mobile", "oppo", "vivo", "oneplus", "price_increase", "china"],
        "entities": ["OPPO", "vivo", "OnePlus"],
        "trust_default": "L2",
    },
    {
        "title": "vivo X300 Ultra/X300s 发布日期和配置泄露",
        "title_zh": "vivo X300 Ultra/X300s 发布日期和配置泄露",
        "summary_zh": "vivo X300 Ultra 和 X300s 即将在未来几周发布，泄露信息显示 X300 Ultra 配备 35mm 主摄，定位影像旗舰。与小米 17 Ultra、OPPO Find X9 Ultra 形成三强对决。",
        "platform": "web",
        "author": "GSMArena",
        "author_type": "media",
        "url": "https://www.gsmarena.com/vivo_x300_ultra_x300s_launch_date_configurations_and_colors_leaked-news-71970.php",
        "content_type": "exclusive",
        "category": "mobile",
        "tags": ["mobile", "vivo", "x300_ultra", "camera", "flagship"],
        "entities": ["vivo"],
        "trust_default": "L2",
    },
    {
        "title": "iPhone Fold 产能大幅提升，苹果加码折叠屏",
        "title_zh": "iPhone Fold 产能大幅提升，苹果正式加码折叠屏市场",
        "summary_zh": "Forbes 报道苹果 iPhone Fold 获得大幅产能提升，价格匹配三星 Galaxy Fold 同价位，苹果对折叠屏期望很高。同期 iPhone 18 Pro 也在筹备中。",
        "platform": "web",
        "author": "Forbes",
        "author_type": "media",
        "url": "https://www.forbes.com/sites/jaymcgregor/2026/03/16/apple-iphone-fold-iphone-18-production-number-leak/",
        "content_type": "exclusive",
        "category": "mobile",
        "tags": ["mobile", "apple", "iphone_fold", "foldable"],
        "entities": ["Apple", "iPhone", "Samsung"],
        "trust_default": "L2",
    },
    {
        "title": "Samsung 推出 Galaxy Forever 购机计划",
        "title_zh": "Samsung 推出 Galaxy Forever 以旧换新购机计划",
        "summary_zh": "三星在印度推出 Galaxy Forever 计划，用户只需支付手机 50% 价格即可使用一年，之后可选择保留、退还或升级到下一代。旨在降低 Galaxy S26 系列高昂售价的门槛。",
        "platform": "web",
        "author": "SamMobile",
        "author_type": "media",
        "url": "https://www.sammobile.com/news/samsung-galaxy-forever-lets-you-use-galaxy-s26-for-year-at-half-price/",
        "content_type": "report",
        "category": "mobile",
        "tags": ["mobile", "samsung", "galaxy_s26", "subscription"],
        "entities": ["Samsung", "Samsung Galaxy"],
        "trust_default": "L2",
    },

    # === 🔧 芯片与算力 ===
    {
        "title": "Micron HBM4 量产，专为 NVIDIA Vera Rubin 设计",
        "title_zh": "美光 HBM4 开始量产，专为 NVIDIA Vera Rubin 设计",
        "summary_zh": "美光科技在 GTC 2026 宣布 HBM4 36GB 12H 内存已开始量产（Q1 2026），专为 NVIDIA Vera Rubin 平台设计。带宽超 2.8 TB/s（比 HBM3E 提升 2.3 倍），能效提升 20%+。同时展示 HBM4 48GB 16H 样品和 PCIe Gen6 SSD。",
        "platform": "web",
        "author": "Stock Titan / Micron",
        "author_type": "official",
        "url": "https://www.stocktitan.net/news/MU/micron-in-high-volume-production-of-hbm4-designed-for-nvidia-vera-7usvjaf0l6il.html",
        "content_type": "official",
        "category": "chips",
        "tags": ["chips", "micron", "hbm4", "nvidia", "vera_rubin", "memory"],
        "entities": ["Micron", "NVIDIA", "HBM4", "Vera Rubin"],
        "trust_default": "L1",
    },
    {
        "title": "NVIDIA 重启 H200 芯片对华出口",
        "title_zh": "NVIDIA 重启 H200 芯片对华出口，黄仁勋称供应链正在启动",
        "summary_zh": "黄仁勋在 GTC 2026 确认 NVIDIA 正在重启 H200 芯片对中国的生产，已收到多家客户订单。美国政府从中获取 25% 销售额分成。Blackwell 和 Rubin 系列仍禁止对华销售。",
        "platform": "web",
        "author": "Manila Times / Reuters",
        "author_type": "media",
        "url": "https://www.manilatimes.net/2026/03/18/business/sunday-business-it/nvidia-says-restarting-production-of-china-bound-chips/2302346",
        "content_type": "report",
        "category": "chips",
        "tags": ["chips", "nvidia", "h200", "china", "export_control"],
        "entities": ["NVIDIA", "Jensen Huang"],
        "trust_default": "L2",
    },
    {
        "title": "SK 海力士董事长：晶圆代工市场主导权战已开始",
        "title_zh": "SK 海力士董事长：晶圆代工市场主导权之战已经开始",
        "summary_zh": "SK 集团董事长表示晶圆代工市场的主导权争夺已经开始，暗示 SK 海力士将进一步加强在先进制程和存储领域的投入。",
        "platform": "web",
        "author": "Industry sources",
        "author_type": "media",
        "url": "https://www.koreaherald.com/article/10474856",
        "content_type": "report",
        "category": "chips",
        "tags": ["chips", "sk_hynix", "foundry", "semiconductor"],
        "entities": ["SK Hynix"],
        "trust_default": "L2",
    },
    {
        "title": "Intel PC 市场下滑预警：预计跌幅 10%-20%",
        "title_zh": "Intel 预警 PC 市场将下滑 10%-20%",
        "summary_zh": "Intel 将芯片供应过剩预期从 20% 调整后，预计 PC 市场将下滑 10%-20%，比部分研究机构预测的更为悲观。同时 Intel 自身面临约 20% 的供应过剩问题。",
        "platform": "web",
        "author": "Industry sources",
        "author_type": "media",
        "url": "https://www.tomshardware.com/news/intel-pc-market-decline",
        "content_type": "report",
        "category": "chips",
        "tags": ["chips", "intel", "pc_market", "decline"],
        "entities": ["Intel"],
        "trust_default": "L2",
    },
]


def main():
    store = AtomStore()
    atoms_to_save = []

    for item in NEWS_ITEMS:
        atom = create_atom(
            title=item.get("title", ""),
            summary_zh=item.get("summary_zh", ""),
            platform=item.get("platform", "web"),
            author=item.get("author", ""),
            author_type=item.get("author_type", "media"),
            url=item.get("url", ""),
            content_type=item.get("content_type", "report"),
            category=item.get("category", "other"),
            tags=item.get("tags", []),
            entities=item.get("entities", []),
            date=DATE,
            title_zh=item.get("title_zh"),
        )
        # 覆盖 trust_default
        if "trust_default" in item:
            atom["trust_default"] = item["trust_default"]
        atoms_to_save.append(atom)

    # 批量保存
    ids = store.save_atoms_batch(atoms_to_save)
    print(f"✅ 导入 {len(ids)} 条 Atoms 到 {DATE}")

    # 打印统计
    from collections import Counter
    cats = Counter(a.get("category") for a in atoms_to_save)
    print(f"📊 板块分布: {dict(cats)}")

    # 同步到 Obsidian
    print("\n📝 同步到 Obsidian...")
    syncer = ObsidianSyncer()
    syncer.sync_date(DATE)
    print("✅ Obsidian 同步完成")


if __name__ == "__main__":
    main()
