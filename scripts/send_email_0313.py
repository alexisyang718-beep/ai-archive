#!/usr/bin/env python3
"""
发送 3月13日 科技资讯日报 — 通过 QQ 邮箱 SMTP
邮件适配：缩减左右边距、CSS变量→硬编码、去JS/暗黑/外部字体/SVG、premailer内联
"""
import re
import smtplib
import subprocess
import warnings
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from premailer import transform

warnings.filterwarnings('ignore')

# === 路径基准：脚本所在目录的上级即 tech-daily-brief/ ===
PROJECT_DIR = Path(__file__).resolve().parent.parent
BRIEF_DIR = PROJECT_DIR / "brief"

# === 配置 ===
INPUT_HTML = BRIEF_DIR / '2026-03-13.html'
SUBJECT = '科技资讯日报｜3月13日'
ONLINE_URL = 'https://alexisyang718-beep.github.io/ai-archive/brief/2026-03-13.html'

SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
QQ_EMAIL = "422548579@qq.com"

# 完整收件人列表
TO_LIST = [
    "fabzeng@tencent.com",
    "ryanpang@tencent.com",
    "yuxiachen@tencent.com",
    "winstonchen@tencent.com",
    "cicipei@tencent.com",
    "laviahuo@tencent.com",
    "allenzqwei@tencent.com",
    "alexisyang@tencent.com",
]

# 从钥匙串获取授权码
def get_auth_code():
    result = subprocess.run(
        ["security", "find-generic-password", "-a", QQ_EMAIL, "-s", "qq-smtp-auth", "-w"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    raise RuntimeError("无法从钥匙串读取授权码")

# === Step 1: 读取并做邮件适配 ===
print("1. 读取 HTML 并做邮件适配...")
with open(INPUT_HTML, 'r', encoding='utf-8') as f:
    html = f.read()

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

# 1i) 去掉固定定位元素
html = re.sub(r'<a[^>]*class="back-to-top"[^>]*>.*?</a>', '', html, flags=re.DOTALL)
html = re.sub(r'<a[^>]*class="back-home"[^>]*>.*?</a>', '', html, flags=re.DOTALL)
html = re.sub(r'<div[^>]*class="theme-toggle"[^>]*>.*?</div>', '', html, flags=re.DOTALL)

# 1j) 去掉 <script> 标签
html = re.sub(r'<script[\s\S]*?</script>', '', html)

# 1k) 所有 "AI Daily Brief" → "科技资讯日报"
html = html.replace('AI Daily Brief', '科技资讯日报')
html = html.replace(
    '</footer>',
    f'<p style="margin-top:12px;"><a href="{ONLINE_URL}" style="color:#C96442;">📱 在手机/电脑浏览器中查看完整版（含暗色模式）</a></p>\n</footer>'
)

# 1l) 去掉 .back-to-top / .back-home / .theme-toggle 的 CSS 规则
html = re.sub(r'\.back-to-top\s*\{[^}]*\}', '', html)
html = re.sub(r'\.back-to-top\.visible\s*\{[^}]*\}', '', html)
html = re.sub(r'\.back-home\s*\{[^}]*\}', '', html)
html = re.sub(r'\.theme-toggle\s*\{[^}]*\}', '', html)

# 1m) 去掉 grid（邮件兼容性差）→ 改为 block
html = html.replace('display: grid;', 'display: block;')
html = html.replace('grid-template-columns: repeat(2, 1fr);', '')
html = html.replace('grid-template-columns: 1fr 1fr;', '')
html = html.replace('grid-template-columns: 1fr;', '')

print(f"   适配后 HTML: {len(html)} bytes")

# === Step 2: premailer 内联 CSS ===
print("2. premailer 内联 CSS...")
inlined = transform(
    html,
    remove_classes=True,
    strip_important=True,
    keep_style_tags=False,
    cssutils_logging_level='CRITICAL'
)
print(f"   内联后 HTML: {len(inlined)} bytes")

# === Step 3: 构建 MIME 邮件 ===
print("3. 构建邮件...")
msg = MIMEMultipart('alternative')
msg['Subject'] = SUBJECT
msg['From'] = QQ_EMAIL
msg['To'] = ', '.join(TO_LIST)

text_part = MIMEText(
    f'科技资讯日报｜3月13日\n\n'
    f'请使用支持 HTML 的邮件客户端查看。\n'
    f'在线版：{ONLINE_URL}',
    'plain', 'utf-8'
)
html_part = MIMEText(inlined, 'html', 'utf-8')
msg.attach(text_part)
msg.attach(html_part)

# === Step 4: QQ SMTP SSL 发送 ===
print("4. 连接 QQ SMTP...")
QQ_AUTH_CODE = get_auth_code()
try:
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(QQ_EMAIL, QQ_AUTH_CODE)
        print("   登录成功!")
        server.sendmail(QQ_EMAIL, TO_LIST, msg.as_string())
        print(f"✅ 邮件发送成功！ → {len(TO_LIST)} 位收件人")
        for addr in TO_LIST:
            print(f"   📧 {addr}")
except Exception as e:
    print(f"❌ 发送失败: {e}")
