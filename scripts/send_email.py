#!/usr/bin/env python3
"""
发送科技资讯日报邮件 — 通过 QQ 邮箱 SMTP

用法:
    # 发送给全部收件人（会先显示预览，需确认后才发送）
    python send_email.py brief/2026-03-21.html

    # 只发送给指定邮箱（测试用）
    python send_email.py brief/2026-03-21.html --to alexisyang@tencent.com

    # 跳过确认直接发送（脚本/CI 调用时使用）
    python send_email.py brief/2026-03-21.html -y

    # 发送给新增的一批收件人
    python send_email.py --new-only brief/2026-03-21.html

邮件适配：缩减左右边距、CSS变量→硬编码、去JS/暗黑/外部字体/SVG、premailer内联
"""
import re
import sys
import smtplib
import subprocess
import warnings
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from premailer import transform

warnings.filterwarnings('ignore')

# === 路径基准：脚本所在目录的上级即 tech-daily-brief/ ===
PROJECT_DIR = Path(__file__).resolve().parent.parent
BRIEF_DIR = PROJECT_DIR / "brief"

# === 邮件配置 ===
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
QQ_EMAIL = "422548579@qq.com"

# 原始收件人（8人）
ORIGINAL_LIST = [
    "fabzeng@tencent.com",
    "ryanpang@tencent.com",
    "yuxiachen@tencent.com",
    "winstonchen@tencent.com",
    "cicipei@tencent.com",
    "laviahuo@tencent.com",
    "allenzqwei@tencent.com",
    "alexisyang@tencent.com",
]

# 新增收件人（15人）
NEW_LIST = [
    "alexyigong@tencent.com",
    "camiwei@tencent.com",
    "coraljzhang@tencent.com",
    "cynthiarong@tencent.com",
    "zhenhuaran@tencent.com",
    "aubreyhjli@tencent.com",
    "ceciyazhang@tencent.com",
    "miaruan@tencent.com",
    "michaellhao@tencent.com",
    "summersheng@tencent.com",
    "veranma@tencent.com",
    "bowenyfeng@tencent.com",
    "allenrlu@tencent.com",
    "jakobzhou@tencent.com",
    "jimhanzhang@tencent.com",
]

# 全部收件人（默认使用）
TO_LIST = ORIGINAL_LIST + NEW_LIST

ONLINE_BASE_URL = "https://alexisyang718-beep.github.io/ai-archive/brief"


def get_auth_code():
    """从 macOS 钥匙串获取 QQ 邮箱授权码"""
    result = subprocess.run(
        ["security", "find-generic-password", "-a", QQ_EMAIL, "-s", "qq-smtp-auth", "-w"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    raise RuntimeError("无法从钥匙串读取授权码")


def find_latest_brief():
    """自动检测 brief/ 下最新的日报 HTML（排除 -wechat.html）"""
    html_files = sorted(
        [f for f in BRIEF_DIR.glob("*.html") if not f.name.endswith("-wechat.html")],
        reverse=True
    )
    if not html_files:
        raise FileNotFoundError(f"brief/ 目录下没有找到日报 HTML 文件: {BRIEF_DIR}")
    return html_files[0]


def extract_date_from_html(html_content):
    """从 HTML 内容中提取日期，返回 (年, 月, 日) 或 None"""
    match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', html_content)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return None


def adapt_for_email(html):
    """将网页版 HTML 适配为邮件兼容格式"""

    # 1a) 去掉外部字体 @import（邮件客户端不支持）
    html = re.sub(r"@import\s+url\([^)]+\);?\s*", "", html)

    # 1b) CSS变量 → 硬编码值
    css_vars = {
        'var(--bg)': '#FAF9F5',
        'var(--bg-warm)': '#F5F0E8',
        'var(--card)': '#FFFFFF',
        'var(--border)': '#E8E2D9',
        'var(--border-light)': '#F0EBE3',
        'var(--accent)': '#C96442',
        'var(--accent-hover)': '#B5573A',
        'var(--accent-soft)': 'rgba(201, 100, 66, 0.08)',
        'var(--accent-border)': 'rgba(201, 100, 66, 0.2)',
        'var(--text)': '#1A1A1A',
        'var(--text-secondary)': '#6B6560',
        'var(--text-tertiary)': '#9B9590',
        'var(--tag-red)': '#C96442',
        'var(--tag-red-bg)': 'rgba(201, 100, 66, 0.08)',
        'var(--tag-green)': '#5A8F6B',
        'var(--tag-green-bg)': 'rgba(90, 143, 107, 0.08)',
        'var(--tag-blue)': '#4A7B9D',
        'var(--tag-blue-bg)': 'rgba(74, 123, 157, 0.08)',
        'var(--tag-purple)': '#7B6B9D',
        'var(--tag-purple-bg)': 'rgba(123, 107, 157, 0.08)',
        'var(--tag-orange)': '#B8863B',
        'var(--tag-orange-bg)': 'rgba(184, 134, 59, 0.08)',
        'var(--tag-teal)': '#4A8F8F',
        'var(--tag-teal-bg)': 'rgba(74, 143, 143, 0.08)',
        'var(--shadow-sm)': '0 1px 3px rgba(0,0,0,0.04)',
        'var(--shadow-md)': '0 4px 12px rgba(0,0,0,0.06)',
        'var(--shadow-hover)': '0 6px 20px rgba(0,0,0,0.08)',
        'var(--radius)': '16px',
        'var(--radius-sm)': '10px',
    }
    for var, val in css_vars.items():
        html = html.replace(var, val)

    # 1c) 去掉 :root 块
    html = re.sub(r':root\s*\{[^}]+\}', '', html)

    # 1d) 去掉 [data-theme="dark"] 块
    html = re.sub(r'\[data-theme="dark"\]\s*\{[^}]+\}', '', html)

    # 1e) 去掉所有 :hover 规则（邮件不支持）
    html = re.sub(r'[^{}]*:hover\s*\{[^}]*\}', '', html)

    # 1f) 去掉 transition 属性
    html = re.sub(r'transition:[^;]+;', '', html)

    # 1g) 缩减边距优化移动端
    html = html.replace('max-width: 780px', 'max-width: 680px')
    html = html.replace('padding: 0 24px;', 'padding: 0 12px;', 1)
    html = html.replace('.container { padding: 0 16px; }', '.container { padding: 0 8px; }')
    html = html.replace('padding: 20px 24px;', 'padding: 16px 14px;')
    html = html.replace('padding: 24px 28px;', 'padding: 20px 16px;')
    html = html.replace('padding: 60px 0 40px;', 'padding: 32px 0 20px;')
    html = html.replace('.item { padding: 16px 18px; }', '.item { padding: 12px 10px; }')
    html = html.replace('.summary-card { padding: 18px 20px; }', '.summary-card { padding: 14px 12px; }')
    html = html.replace('margin-bottom: 48px;', 'margin-bottom: 32px;')

    # 1h) 去掉 header-logo（机器人图标）
    html = re.sub(r'<div class="header-logo">.*?</div>', '', html, flags=re.DOTALL)

    # 1i) 去掉固定定位元素（back-to-top, back-home, theme-toggle）
    html = re.sub(r'<a[^>]*class="back-to-top"[^>]*>.*?</a>', '', html, flags=re.DOTALL)
    html = re.sub(r'<a[^>]*class="back-home"[^>]*>.*?</a>', '', html, flags=re.DOTALL)
    html = re.sub(r'<button[^>]*class="theme-toggle"[^>]*>.*?</button>', '', html, flags=re.DOTALL)

    # 1j) 去掉 <script> 标签
    html = re.sub(r'<script[\s\S]*?</script>', '', html)

    # 1k) 去掉 .back-to-top / .back-home / .theme-toggle 的 CSS 规则
    html = re.sub(r'\.back-to-top\s*\{[^}]*\}', '', html)
    html = re.sub(r'\.back-to-top\.visible\s*\{[^}]*\}', '', html)
    html = re.sub(r'\.back-home\s*\{[^}]*\}', '', html)
    html = re.sub(r'\.theme-toggle\s*\{[^}]*\}', '', html)

    # 1l) 去掉 grid（邮件兼容性差）→ 改为 block
    html = html.replace('display: grid;', 'display: block;')
    html = html.replace('grid-template-columns: repeat(2, 1fr);', '')
    html = html.replace('grid-template-columns: 1fr 1fr;', '')
    html = html.replace('grid-template-columns: 1fr;', '')

    return html


def parse_args():
    """解析命令行参数"""
    import argparse
    parser = argparse.ArgumentParser(description='发送科技资讯日报邮件')
    parser.add_argument('file', nargs='?', help='日报 HTML 文件路径（默认自动检测最新）')
    parser.add_argument('--to', help='指定收件人邮箱，多个用逗号分隔')
    parser.add_argument('--new-only', action='store_true', help='只发送给新增的收件人')
    parser.add_argument('-y', '--yes', action='store_true', help='跳过确认直接发送')
    return parser.parse_args()


def main():
    args = parse_args()
    
    # 确定收件人列表
    if args.to:
        to_list = [e.strip() for e in args.to.split(',')]
    elif args.new_only:
        to_list = NEW_LIST
    else:
        to_list = TO_LIST
    
    # 确定输入文件
    if args.file:
        input_html = Path(args.file)
        if not input_html.is_absolute():
            input_html = PROJECT_DIR / input_html
    else:
        input_html = find_latest_brief()

    if not input_html.exists():
        print(f"❌ 文件不存在: {input_html}")
        sys.exit(1)

    print(f"1. 读取 HTML: {input_html.name}")
    html = input_html.read_text(encoding='utf-8')

    # 提取日期
    date_info = extract_date_from_html(html)
    if date_info:
        year, month, day = date_info
        subject = f'科技资讯日报｜{month}月{day}日'
        online_url = f'{ONLINE_BASE_URL}/{input_html.name}'
    else:
        subject = f'科技资讯日报｜{input_html.stem}'
        online_url = f'{ONLINE_BASE_URL}/{input_html.name}'

    print(f"   标题: {subject}")
    print(f"   在线版: {online_url}")

    # 邮件适配
    print("2. 邮件适配...")
    html = adapt_for_email(html)

    # 添加在线版链接
    html = html.replace(
        '</footer>',
        f'<p style="margin-top:12px;"><a href="{online_url}" style="color:#C96442;">📱 在手机/电脑浏览器中查看完整版（含暗色模式）</a></p>\n</footer>'
    )

    print(f"   适配后: {len(html)} bytes")

    # premailer 内联 CSS
    print("3. premailer 内联 CSS...")
    inlined = transform(
        html,
        remove_classes=True,
        strip_important=True,
        keep_style_tags=False,
        cssutils_logging_level='CRITICAL'
    )
    print(f"   内联后: {len(inlined)} bytes")

    # 构建 MIME 邮件
    print("4. 构建邮件...")
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = formataddr((str(Header('科技资讯日报', 'utf-8')), QQ_EMAIL))
    msg['To'] = ', '.join(to_list)

    text_part = MIMEText(
        f'{subject}\n\n'
        f'请使用支持 HTML 的邮件客户端查看。\n'
        f'在线版：{online_url}',
        'plain', 'utf-8'
    )
    html_part = MIMEText(inlined, 'html', 'utf-8')
    msg.attach(text_part)
    msg.attach(html_part)

    # 发送前确认
    print("\n" + "=" * 50)
    print("📋 发送预览")
    print("=" * 50)
    print(f"   标题:  {subject}")
    print(f"   文件:  {input_html.name}")
    print(f"   大小:  {len(inlined)} bytes")
    print(f"   收件人: {len(to_list)} 人")
    for addr in to_list:
        print(f"     → {addr}")
    print("=" * 50)

    if not args.yes:
        try:
            confirm = input("\n⚠️  确认发送？(y/N) ").strip().lower()
            if confirm not in ('y', 'yes'):
                print("❌ 已取消发送。")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            # 非交互环境（如 AI 调用）自动跳过确认
            pass

    # QQ SMTP SSL 发送
    print("\n5. 连接 QQ SMTP...")
    auth_code = get_auth_code()
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(QQ_EMAIL, auth_code)
            print("   登录成功!")
            server.sendmail(QQ_EMAIL, to_list, msg.as_string())
            print(f"\n✅ 邮件发送成功！ → {len(to_list)} 位收件人")
            for addr in to_list:
                print(f"   📧 {addr}")
    except Exception as e:
        print(f"\n❌ 发送失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
