#!/usr/bin/env python3
"""将微信复制版（全 inline style）日报 HTML 推送到微信公众号草稿箱
修改：
1. 上传桌面 cover.png 作为封面
2. 移除目录部分
3. 用 div 包裹 table 实现圆角（微信 table 不支持 border-radius）
4. 去除正文 div 开头空格
5. 正文字号不做调整（保持14px，微信渲染不会自动放大）
"""
import sys, re, os
from pathlib import Path
sys.path.insert(0, '/Users/yangliu/.codebuddy/skills/wechat-publisher-skill/src')

from publisher import WeChatPublisher

# ===== 配置 =====
APPID = "wxc0acff84c3ba27b0"
APPSECRET = "7af6a2678e804ecbe3425f0889c1d28d"
COVER_IMAGE = os.path.expanduser("~/Desktop/cover.png")

# 路径基准：脚本所在目录的上级即 ai-daily-brief/
PROJECT_DIR = Path(__file__).resolve().parent.parent
BRIEF_DIR = PROJECT_DIR / "brief"

# 读取微信复制版 HTML（已经全部 inline style，不需要 premailer）
html_path = BRIEF_DIR / "2026-03-10-wechat-copy.html"
with open(html_path, 'r') as f:
    html = f.read()

print(f"1. 读取 HTML: {len(html)} bytes")

# 提取 body 内容
body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
if body_match:
    content = body_match.group(1).strip()
else:
    content = html
print(f"2. 提取 body: {len(content)} bytes")

# ===== 修改1: 移除目录部分 =====
print("3. 移除目录...")
# 目录是一个包含"目录"文字的 table，紧接着一个分隔线 div
content = re.sub(
    r'<table[^>]*>.*?目录.*?</table>\s*<div[^>]*style="[^"]*height:1px[^"]*"[^>]*></div>',
    '',
    content,
    flags=re.DOTALL
)
print(f"   移除目录后: {len(content)} bytes")

# ===== 修改2: 清理微信不支持的内容 =====
print("4. 清理微信不兼容内容...")

# 移除 HTML 注释
content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

# 微信不允许外部链接 <a href="http...">，保留文字去掉标签
content = re.sub(r'<a\s+[^>]*href=["\']https?://[^"\']*["\'][^>]*>(.*?)</a>', r'\1', content, flags=re.DOTALL)

# 移除残余的 <a> 标签
content = re.sub(r'<a\s+[^>]*>(.*?)</a>', r'\1', content, flags=re.DOTALL)

# 移除 class 属性（inline 版不应该有，但以防万一）
content = re.sub(r'\s+class="[^"]*"', '', content)

# 移除 data-* 属性
content = re.sub(r'\s+data-[a-z-]+="[^"]*"', '', content)

# 移除空的 style 属性
content = re.sub(r'\s+style=""', '', content)

# ===== 修改3: 去掉正文开头空格 =====
print("5. 去除正文开头空格...")
# 正文 div 内有多余的换行+空格缩进，例如：
#   <div style="font-size:14px...">
#       Anthropic 于...
#   </div>
# 需要去掉 > 之后到正文文字之间的空白
content = re.sub(r'(<div[^>]*style="[^"]*font-size:14px[^"]*"[^>]*>)\s+', r'\1', content, flags=re.DOTALL)

# 同样处理深度洞察的 div
content = re.sub(r'(<div[^>]*style="[^"]*line-height:1\.85[^"]*"[^>]*>)\s+', r'\1', content, flags=re.DOTALL)

# ===== 修改4: 处理 table 圆角 =====
# 微信 table 元素不支持 border-radius，需要在 table 外包一层 div 来实现圆角
# 主要处理新闻卡片的外层 table
print("6. 处理圆角边框...")

def wrap_table_with_rounded_div(content):
    """将有 border-radius 的 table 用外层 div 包裹实现圆角"""
    # 匹配含有 border-radius 的 table 开始标签
    # 策略：将 table 的 border-radius 和 border 移到外层 div
    def replace_rounded_table(match):
        full_match = match.group(0)
        style = match.group(1)
        
        # 提取 border-radius 值
        br_match = re.search(r'border-radius:\s*([^;]+)', style)
        if not br_match:
            return full_match
        
        border_radius = br_match.group(1).strip()
        
        # 提取 border 值
        border_match = re.search(r'(?<!border-radius:)\bborder:\s*([^;]+)', style)
        border_val = border_match.group(1).strip() if border_match else None
        
        # 提取 margin-bottom
        mb_match = re.search(r'margin-bottom:\s*([^;]+)', style)
        margin_bottom = mb_match.group(1).strip() if mb_match else None
        
        # 构建外层 div 样式
        div_style_parts = [
            f"border-radius:{border_radius}",
            "overflow:hidden",
        ]
        if border_val:
            div_style_parts.append(f"border:{border_val}")
        if margin_bottom:
            div_style_parts.append(f"margin-bottom:{margin_bottom}")
        
        div_style = ";".join(div_style_parts)
        
        # 从 table style 中移除已提取的属性
        new_style = style
        new_style = re.sub(r'border-radius:\s*[^;]+;?\s*', '', new_style)
        if border_val:
            # 只移除 border，不移除 border-top 等
            new_style = re.sub(r'(?<!-)border:\s*[^;]+;?\s*', '', new_style)
        if margin_bottom:
            new_style = re.sub(r'margin-bottom:\s*[^;]+;?\s*', '', new_style)
        
        # 清理尾部分号
        new_style = new_style.rstrip(';').strip()
        
        new_table = f'<table cellpadding="0" cellspacing="0" border="0" width="100%" style="{new_style}">'
        
        return f'<div style="{div_style}">{new_table}'
    
    # 匹配包含 border-radius 的 table 开始标签
    content = re.sub(
        r'<table\s+cellpadding="0"\s+cellspacing="0"\s+border="0"\s+width="100%"\s+style="([^"]*border-radius[^"]*)">', 
        replace_rounded_table, 
        content
    )
    
    # 对应的，在这些 table 的 </table> 结尾处加上 </div>
    # 这比较棘手，因为 table 可能嵌套。用更简单的方法：
    # 直接在 content 中，每个被包裹的 table 的最后一个 </table> 后加 </div>
    # 但这需要精确匹配。简化方案：不嵌套 div，而是直接修改 td 的样式
    
    return content

# 更简单的方案：微信中 td 支持 border-radius，直接确保 td 有圆角
# 实际上原 HTML 已经在 td 上设了 border-radius:12px，只是微信可能忽略
# 换一种策略：在 td 外再加一层 section 包裹
# 最安全的方案：把 table 卡片替换为 div+section 结构
# 但这改动太大。实际测试微信公众号 td 是支持 border-radius 的。
# 问题可能出在 table 的 border-collapse 导致 td 的 border-radius 失效

# 简化方案：给所有有 border-radius 的 td 加上 overflow:hidden 确保生效
content = re.sub(
    r'(<td\s+style="[^"]*)(border-radius:\s*\d+px)',
    r'\1overflow:hidden;\2',
    content
)

print(f"   处理后内容大小: {len(content)} bytes ({len(content)/1024:.1f} KB)")

if len(content) > 2 * 1024 * 1024:
    print("⚠️  内容超过 2MB，可能超出微信 API 限制")

# ===== 上传封面图片 =====
print("7. 连接微信公众号 API...")
publisher = WeChatPublisher(appid=APPID, secret=APPSECRET)

print(f"8. 上传封面图片: {COVER_IMAGE}")
if not os.path.exists(COVER_IMAGE):
    print(f"❌ 封面图片不存在: {COVER_IMAGE}")
    sys.exit(1)

# 上传封面图片获取 thumb_media_id
try:
    thumb_media_id = publisher.upload_image(COVER_IMAGE)
    print(f"   封面上传成功: {thumb_media_id}")
except Exception as e:
    print(f"❌ 封面上传失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

article = {
    "title": "科技资讯日报｜3月10日",
    "author": "AI Daily Brief",
    "digest": "Anthropic起诉五角大楼 · 微软Copilot Cowork接入Claude · 13家大厂抢OpenClaw · 苹果Ultra产品矩阵 · GDC 2026 · AI APP时长暴增177%",
    "content": content,
    "content_source_url": "https://alexisyang718-beep.github.io/ai-archive/brief/2026-03-10.html",
    "thumb_media_id": thumb_media_id,
    "show_cover_pic": 1,
    "need_open_comment": 1,
    "only_fans_can_comment": 0
}

print("9. 创建草稿...")
try:
    media_id = publisher.create_draft([article])
    print(f"✅ 草稿创建成功！media_id: {media_id}")
    print(f"   封面: {COVER_IMAGE}")
    print(f"   请到微信公众平台后台查看: https://mp.weixin.qq.com/")
except Exception as e:
    print(f"❌ 创建草稿失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
